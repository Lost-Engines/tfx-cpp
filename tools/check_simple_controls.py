#!/usr/bin/env python3
"""Compare the original complete Simple G-limited control response (0x8cfa0).

The original joystick direction helper, x87 normalisation and power routine
execute. Alt-key state, prior turn coupling, aircraft limits and
speed are supplied inputs; this is not the complete Simple flight model.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);im.write(0x1b23c,'<I',0x300000)
rng=random.Random(0x8cfa0);bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    basis=list(identity)
    if index%3:
        im.cpu.mem_write(0x300100,struct.pack('<9h',*identity))
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300100,edx=rng.randrange(65536))
        basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300100,18)))
    speed=[0,1,2,399,400,401,1000,-1][index%8]
    metres=[.01,64.375,92.7,67.98,149.99,150,150.01,340,600][index%9]
    maximum,minimum,stall=[(9,-3,64.375),(6,-1,92.7),(9,-3,67.98)][index%3]
    turn=bits(rng.uniform(-2,2));ticks=[0,1,2,4,18,108,65535][index%7];source=(index//8)%4;joystick=[rng.choice([-513,-512,-41,-40,0,40,41,512,513]) for _ in range(2)]
    keys=[int(index&(1<<bit)!=0) for bit in range(4)];flags=[int(index&(1<<bit)!=0) for bit in range(4,8)]
    initial=[bits(rng.uniform(-1000,1000)) for _ in range(6)]
    cases.append([speed,bits(metres),maximum,minimum,stall,turn,*basis,ticks,source,*joystick,*keys,*flags,*initial])
output=subprocess.check_output([str((a.build/'simple_controls_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    speed,metres,maximum,minimum,stall,turn=row[:6];basis=row[6:15];ticks,source,x,y=row[15:19];keys=row[19:23];landed,ground,pitch_inhibited,rudder=row[23:27];initial=row[27:]
    im.write(0x13444,'<i',speed);im.write(0x133e8,'<I',metres);im.write(0x14488,'<d',maximum);im.write(0x14500,'<d',minimum);im.write(0x14540,'<d',stall);im.write(0x133c8,'<I',turn);im.write(0x1345e,'<9h',*basis);im.write(0x13476,'<H',ticks);im.write(0x13478,'<B',source);im.write(0xac60,'<2h',x,y);im.write(0x8d3a,'<H',landed);im.write(0x8d38,'<H',ground);im.write(0x13474,'<H',pitch_inhibited);im.cpu.mem_write(0x300038,bytes([rudder]))
    for field,value in zip((0x13256,0x13258,0x1325c,0x1325e),keys):im.write(field,'<H',value)
    for field,value in zip((0x86dc,0x86e0,0x86e4,0x133d0,0x133d4,0x133a4),initial):im.write(field,'<I',value)
    im.call(0x8cfa0,limit=1000000)
    expected=[im.read(field,'<I')[0] for field in (0x86dc,0x86e0,0x86e4,0x133d0,0x133d4,0x133a4)]+[im.read(field,'<H')[0] for field in (0x13256,0x13258,0x1325c,0x1325e)]
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Simple control response agrees in {len(cases)} original float-bit/rate/limit/key updates across keyboard, joystick, mouse, G limits and rudder branches')
