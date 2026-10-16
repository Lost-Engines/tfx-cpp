#!/usr/bin/env python3
"""Compare original ejected-pilot trajectories, model events and termination.

The complete 0x8f198 controller, phase helpers, x87/vector math and pose handoff
execute. Ground height/type, world-water flag and ticks are explicit inputs.
SSD model requests are observed without evaluating those separate animations.
"""
import argparse
from collections import Counter
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--record',type=Path,help='write compact original pilot-motion fixtures')
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
terrain_type=-1;events=[]
im.intercept(0xb0d80,'Supply the current pilot terrain handle; cell selection arithmetic executes',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,65535 if terrain_type==-1 else 2),image.return_from()))
im.intercept(0xb7a3c,'Supply the separately checked SSD terrain type',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,terrain_type&0xffffffff),image.return_from()))
im.intercept(0xb52d4,'Observe pilot model-entry changes without executing animation callbacks',lambda image:(events.append(image.cpu.reg_read(r.UC_X86_REG_EDX)&65535),image.return_from()))
def variable(image):
    name=image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data
    assert name in (0x23b8,0x23c0),hex(name)
    image.cpu.reg_write(r.UC_X86_REG_EAX,0x300800+(4 if name==0x23c0 else 0));image.return_from()
im.intercept(0xb1334,'Supply outcome/status variables and observe the pilot fatal-impact writes',variable)
im.write(0xe76c,'<H',7)
rng=random.Random(0x8f198);identity=[32767,0,0,0,32767,0,0,0,32767]
bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
cases=[]
for variant in range(8):
    phase=[1,1,1,1,5,5,3,10][variant]
    position=[10000,[-10,-500,-1500,-6000,-30,-1000,-1000,-1][variant],20000]
    basis=list(identity)
    if variant%3:
        im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
        for function,angle in zip((0xccf4c,0xcd058,0xcd15c),(1024,8192,2048)):im.call(function,eax=0x300000,edx=angle)
        basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    for step in range(1024):
        cases.append([int(step==0),phase,*map(bits,position),*map(bits,(.5,.1,.7)),*basis,300,0,int(phase in (5,10)),0,0,0,0,[1,4,10,16][step%4],-200 if variant==7 else 0,1 if variant==3 else 0,int(variant==5)])
for index in range(4096):
    phase=[0,1,2,3,4,5,6,9,10,11,255][index%11]
    position=[rng.uniform(-100000,100000),rng.choice([-10000,-1000,-20,-19,-1,0,1000]),rng.uniform(-100000,100000)]
    velocity=[rng.uniform(-20,20) for _ in range(3)]
    cases.append([1,phase,*map(bits,position),*map(bits,velocity),*identity,rng.choice([0,300,65535,-65536]),rng.choice([-2147483648,-1,0,24,25,26,149,150,249,250,2147483647]),index%2,123,index%3,index%5==0,index%7==0,rng.choice([0,1,4,25,150,65535]),rng.choice([-2000,-1,0,200]),[-1,0,1,50][index%4],index%5==0])
output=subprocess.check_output([str((a.build/'ejection_probe').resolve())],input=('\n'.join(' '.join(str(int(value)) for value in row) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
counts=Counter();fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    reset,phase=row[:2];positions=row[2:5];velocities=row[5:8];basis=row[8:17];speed,counter,chute,auxiliary,collision,ended,fatal,ticks,ground,terrain_type,water=row[17:]
    if reset:
        im.write(0xe784,'<B',phase)
        for field,value in zip((0x1341c,0x13428,0x13434),positions):im.write(field,'<I',value)
        for field,value in zip((0x13448,0x13414,0x13418),velocities):im.write(field,'<I',value)
        im.write(0x1345e,'<9h',*basis);im.write(0x13444,'<i',speed);im.write(0x13390,'<i',counter);im.write(0x13394,'<i',chute);im.write(0x13398,'<i',auxiliary);im.write(0x12c04,'<h',collision);im.write(0x593a,'<H',ended);im.write(0x13479,'<B',fatal)
        im.cpu.mem_write(0x300800,struct.pack('<2i',1 if fatal else 0,4 if fatal else 0))
    im.write(0x13476,'<H',ticks);im.write(0xabf2,'<h',ground);im.write(0xe774,'<B',64 if water else 0);events.clear()
    try:im.call(0x8f198,limit=1000000)
    except RuntimeError as error:raise RuntimeError((index,row,str(error))) from error
    expected=[im.read(0xe784,'<B')[0],*[im.read(field,'<I')[0] for field in (0x1341c,0x13428,0x13434,0x13448,0x13414,0x13418)],*im.read(0x1345e,'<9h'),*im.read(0x13444,'<i'),*im.read(0x13390,'<i'),*im.read(0x13394,'<i'),*im.read(0x13398,'<i'),*im.read(0x12c04,'<h'),*im.read(0x593a,'<H'),*im.read(0x13479,'<B'),*[im.read(field,'<i')[0] for field in (0x13424,0x13430,0x1343c)],*im.read(0x86c8,'<3H'),len(events),*events]
    actual=list(map(int,line.split()))
    assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],actual,expected)
    if events and 6 in events:assert struct.unpack('<2i',im.cpu.mem_read(0x300800,8))==(1,4)
    counts['phase_'+str(expected[0])]+=1
    if (index<8192 and index%1024==0) or (index>=8192 and (index-8192)%31==0):
        digest=14695981039346656037
        for value in expected:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixtures.append(' '.join(str(int(value)) for value in row+[digest]))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Ejected-pilot motion agrees in {len(cases)} complete native pose/float-bit/state/model-event updates: {dict(counts)}')
