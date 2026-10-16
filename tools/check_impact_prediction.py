#!/usr/bin/env python3
"""Compare original category-9 bomb impact prediction before screen projection.

The transformed mount anchor is supplied; original construction and complete
motion callbacks run until the native stop condition. SSD visual notifications
are excluded, and the projected sample is observed at the graphics boundary.
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
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
im=NativeReference(directory/'TFX.DAT');im.cpu.mem_map(0x300000,0x2000)
anchor=(0,0,0);points=[]
im.intercept(0x8b984,'Supply a stable mount descriptor; the transformed anchor follows separately.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x301000),im.return_from()))
def place(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+4,4))[0]
    im.cpu.mem_write(destination,struct.pack('<3i',*anchor));im.return_from()
im.intercept(0xb81de,'Supply the independently verified transformed Q8 launch anchor.',place)
im.intercept(0xb52d4,'Exclude visual events from the temporary, non-firing prediction.',lambda im:im.return_from())
def project(im):
    points.extend(im.read(0x14ec8,'<3i'))
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+16,4))[0]
    im.cpu.mem_write(destination,bytes(4));im.return_from(16)
im.intercept(0xc5759,'Observe the resulting Q8 impact point before external screen projection.',project)
weapons=[weapon for weapon in range(27) if im.read(0x80b9+weapon*48,'<B')[0]==9]
for weapon in weapons:im.write(0x809c+weapon*48+16,'<2H',10,11)
rng=random.Random(0xa29dc);cases=[]
for index in range(256):
    weapon=weapons[index%len(weapons)];x=rng.randrange(-100000000,100000000);z=rng.randrange(-100000000,100000000)
    y=[0,1,-1,-256,-10000,-100000,-1000000,-2000000][index%8]
    pitch=[0,16384,32768,49152,65535][index%5] if index<80 else rng.randrange(65536)
    cases.append([weapon,x,y,z,pitch,rng.randrange(65536),rng.randrange(65536),rng.randrange(-500,2000),*[(-8192,-32),(-16384,0),(-4096,-100)][index%3]])
output=subprocess.check_output([str((args.build/'cannon_prediction_probe').resolve()),str(directory),'impact'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).splitlines()
assert len(output)==len(cases)
for index,row in enumerate(cases):
    weapon,*rest=row;anchor=tuple(rest[:3]);pitch,heading,roll,speed,minimum,maximum=rest[3:]
    im.write(0xac58,'<i',minimum);im.write(0xac5c,'<i',maximum);im.write(0x86c8,'<3H',pitch,heading,roll);im.write(0x13444,'<i',speed);im.write(0x13476,'<H',index%55);points.clear()
    im.call(0xa29dc,eax=weapon,edx=0x300000,limit=10000000)
    got=list(map(int,output[index].split()));assert got==points,(row,got,points)
    assert im.read(0x13476,'<H')[0]==index%55 and im.read(0x16e92,'<H')[0]==0
print(f'Bomb impact prediction agrees in {len(cases)} native trajectories across all {len(weapons)} category-9 weapons, with native timer restoration')
