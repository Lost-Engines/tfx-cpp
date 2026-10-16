#!/usr/bin/env python3
"""Compare original Escape/seat requests and pilot/abandoned-aircraft handoff.

The complete key handler and 0x70ec8 frame boundary execute. Player physics,
SSD seat-release timing and handle identities are supplied boundaries; model,
camera-queue and audio requests are observed without their separate consumers.
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
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
events=[]
for address,kind,register in [(0xb52d4,0,r.UC_X86_REG_EDX),(0x8fd84,1,r.UC_X86_REG_EAX),(0xa5a9c,2,r.UC_X86_REG_EAX),(0xa4e18,3,r.UC_X86_REG_EAX)]:
    def callback(image,kind=kind,register=register):events.extend([kind,image.cpu.reg_read(register)&65535]);image.return_from()
    im.intercept(address,'Observe typed ejection model/camera/voice/sample requests at their separately verified boundaries',callback)
rng=random.Random(0x70ec8);identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
for index in range(4096):
    basis=list(identity)
    if index%4:
        im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
        basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    position=[rng.randrange(-1000000,1000000),rng.randrange(-10000,100),rng.randrange(-1000000,1000000)]
    floating=[bits(value+.375) for value in position]
    cases.append([[0,1,254,255][index%4],index%3,[0,1,2,3,4,5,10,255][index%8],rng.randrange(-2000000000,2000000000),rng.randrange(-2000000,0),rng.randrange(-2000000000,2000000000),*basis,*position,*floating,*basis,*[rng.randrange(65536) for _ in range(3)],rng.choice([-100000,0,20,300,65535]),rng.choice([0,1,4,108,65535]),index%5,index%7==0])
output=subprocess.check_output([str((a.build/'ejection_sequence_probe').resolve())],input=('\n'.join(' '.join(str(int(value)) for value in row) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for index,(row,line) in enumerate(zip(cases,output)):
    presses,stage,phase=row[:3];old=row[3:6];old_basis=row[6:15];position=row[15:18];floating=row[18:21];basis=row[21:30];angles=row[30:33];speed,ticks,calls,mark=row[33:]
    im.write(0x7786,'<B',presses);im.write(0xabe9,'<B',stage);im.write(0xe784,'<B',phase);im.write(0xe6f0,'<3i',*old);im.write(0xe730,'<9h',*old_basis)
    for field,value in zip((0x13424,0x13430,0x1343c),position):im.write(field,'<i',value)
    for field,value in zip((0x1341c,0x13428,0x13434),floating):im.write(field,'<I',value)
    im.write(0x1345e,'<9h',*basis);im.write(0x86c8,'<3H',*angles);im.write(0x13444,'<i',speed);im.write(0x13476,'<H',ticks);im.write(0x13520,'<3i',7,8,9);im.write(0x7785,'<B',1);im.write(0x593a,'<H',0);im.write(0xe76c,'<H',7);im.write(0xe754,'<H',9);im.write(0xac58,'<i',-16384);im.write(0xac5c,'<i',0);events.clear()
    for call in range(calls):im.call(0x84e60)
    if mark:im.write(0xabe9,'<B',1)
    im.call(0x70ec8)
    expected=[*im.read(0x7786,'<B'),*im.read(0xabe9,'<B'),*im.read(0xe784,'<B'),int(im.read(0xe76c,'<H')[0]==9),*im.read(0x593a,'<H'),*im.read(0x7785,'<B'),*im.read(0x13520,'<3i'),*im.read(0xe6f0,'<3i'),*im.read(0xe730,'<9h'),len(events)//2,*events]
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],actual,expected)
print(f'Escape and pilot/aircraft handoff agree in {len(cases)} complete native key/frame-boundary states and ordered requests')
