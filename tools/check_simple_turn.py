#!/usr/bin/env python3
"""Compare complete original Simple bank/turn, speed and G-load updates.

The full original 0x8d3cc and its matrix, angle and residual helpers execute
without interception. Prior attitude/rates, Mach and elapsed ticks are supplied;
this is one stage of the Simple flight model, not a complete flight session.
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
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096)
rng=random.Random(0x8d3cc);bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    angles=[rng.randrange(65536),rng.randrange(65536),[0,8191,8192,8193,16384,24575,24576,24577,32768,40959,40960,40961,49152,57343,57344,57345][index%16]]
    for function,angle in zip((0xccf4c,0xcd058,0xcd15c),angles):im.call(function,eax=0x300000,edx=angle)
    basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    mach=[0,.01,.099999,.1,.100001,.7,.85,1.2,2.5][index%9];pitch=bits(rng.uniform(-1000,1000));ticks=[0,1,2,4,18,108,65535][index%7];remainder=bits(rng.uniform(-2048,2048));correction=rng.randrange(-32768,32768)
    cases.append([bits(mach),pitch,ticks,*basis,remainder,correction])
output=subprocess.check_output([str((a.build/'simple_turn_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    mach,pitch,ticks=row[:3];basis=row[3:12];remainder,correction=row[12:]
    im.write(0x86f4,'<I',mach);im.write(0x86dc,'<I',pitch);im.write(0x13476,'<H',ticks);im.write(0x1345e,'<9h',*basis);im.write(0x13484,'<I',remainder);im.write(0x878e,'<h',correction)
    im.call(0x8d3cc,limit=1000000)
    expected=[value&0xffffffff for value in im.read(0x1345e,'<9h')]+[im.read(0x13484,'<I')[0],im.read(0x878e,'<h')[0]&0xffffffff]+[im.read(field,'<I')[0] for field in (0x133a0,0x133c0,0x133c8,0x1339c,0x133f4,0x133c4)]
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Simple coordinated turning agrees in {len(cases)} original basis/residual/bank/speed/G updates with no intercepted dependencies')
