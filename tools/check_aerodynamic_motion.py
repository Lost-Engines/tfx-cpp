#!/usr/bin/env python3
"""Compare both complete native physical motion callbacks (0x9f9d4/0x9fbec).

Original Q15 rotations, double remainders, x87 arithmetic, crash fallback and
integer conversion helpers execute without interception. Forces, already
updated velocity, commands and timestep are declared stage inputs.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0x9f9d4)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
vector_fields=[0x14758,0x14820,0x147f0,0x14508];pair_fields=[0x13fe0,0x8c88]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    frame=im.cpu.mem_read(0x300000,18)
    values=[rng.uniform(-1e6,1e6),rng.uniform(-1e6,1e6),rng.choice([-5000,0,2,2.00000000000001,rng.uniform(-100,100)])]
    values += [rng.uniform(-1000,1000) for _ in range(3)]+[rng.uniform(-100,100) for _ in range(3)]+[rng.uniform(-8,8) for _ in range(3)]
    values += [rng.uniform(-10,10) for _ in range(2)]+[rng.uniform(-63,63) for _ in range(2)]+[rng.uniform(-.1,.1)]
    context=[rng.choice([.02,.04,.1,.3]),rng.uniform(-4,4),rng.uniform(-.6,.6),rng.uniform(-.6,.6)]
    cases.append([index%2,(index//2)%2,(index//4)%2,(index//8)%2,(index//16)%2,rng.choice([0,1,-1]),rng.choice([-100,-5,-2,0,100]),*map(bits,values),*struct.unpack('<9h',frame),*map(bits,context)])
output=subprocess.check_output([str((a.build/'aerodynamic_motion_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    simple,warp,landed,crashing,inhibited,collision,y=row[:7];values=row[7:24];frame=row[24:33];dt,roll,target,alpha=row[33:]
    for offset,value in zip((0xe780,0x8e22,0x13b04),(warp,crashing,inhibited)):im.write(offset,'<B',value)
    im.write(0x8d3a,'<H',landed);im.write(0x12c04,'<h',collision);im.write(0x13430,'<i',y)
    at=0
    for offset in vector_fields:im.write(offset,'<3Q',*values[at:at+3]);at+=3
    for offset in pair_fields:im.write(offset,'<2Q',*values[at:at+2]);at+=2
    im.write(0x143d0,'<Q',values[16]);im.write(0x1493e,'<9h',*frame)
    for offset,value in zip((0x142c0,0x14458,0x14460,0x14418),(dt,roll,target,alpha)):im.write(offset,'<Q',value)
    im.call(0x9fbec if simple else 0x9f9d4)
    expected=[v for offset in vector_fields for v in im.read(offset,'<3Q')]+[v for offset in pair_fields for v in im.read(offset,'<2Q')]
    expected += [v&0xffffffff for v in im.read(0x1493e,'<9h')]+[im.read(0x12c04,'<H')[0],im.read(0x13430,'<i')[0]&0xffffffff]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Aerodynamic motion agrees in {len(cases)} complete original position, velocity, collision, angular-rate, remainder and frame cases without intercepted dependencies')
