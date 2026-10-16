#!/usr/bin/env python3
"""Compare original aerodynamic NED-to-world/view conversion (0x95aa0).

The full routine, Q15 normalisation, double word conversion, float stores,
integer conversion, renderer-basis copy and angle helpers execute unmodified.
No dependencies are intercepted. This bridge is not the aerodynamic integrator.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
rng=random.Random(0x95aa0);bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if index%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    position=[rng.uniform(-1000000,1000000),rng.uniform(-1000000,1000000),rng.uniform(-30000,100)]
    if index%17==0:position=[0.0,-0.0,0.0]
    if index%31==0:position=[1e12,-1e12,1e12]
    forward=rng.choice([0,2.3,-2.3,rng.uniform(-100,100)])
    upward=rng.choice([0,-.35,.35,rng.uniform(-100,100)])
    cases.append([1+index%3,*map(bits,position),*basis,bits(forward),bits(upward)])
output=subprocess.check_output([str((a.build/'aerodynamic_pose_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    craft=row[0];position=row[1:4];basis=row[4:13];forward,upward=row[13:]
    im.write(0x11b2a,'<H',craft-1);im.write(0x14758,'<3Q',*position);im.write(0x1493e,'<9h',*basis);im.write(0x8d28,'<2Q',forward,upward)
    im.call(0x95aa0,limit=1000000)
    expected=[v&0xffffffff for v in im.read(0x1493e,'<9h')]+[v&0xffffffff for v in im.read(0x1345e,'<9h')]+[v&0xffffffff for v in struct.unpack('<9h',im.cpu.mem_read(im.native(0x70aa4+0x47c38),18))]
    expected += [im.read(p,'<I')[0] for p in (0x1341c,0x13428,0x13434)]+[im.read(p,'<i')[0]&0xffffffff for p in (0x13424,0x13430,0x1343c)]+list(im.read(0x86c8,'<3H'))
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Aerodynamic world/view bridge agrees in {len(cases)} original normalised-frame, basis, float-bit, integer and angle updates without intercepted dependencies')
