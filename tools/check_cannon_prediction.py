#!/usr/bin/env python3
"""Compare the original HUD-only cannon trajectory before screen projection.

The transformed launch anchor is supplied at its existing native boundary.
Original constructor, timed callbacks, sample spacing and ground/lifetime
stops execute. Screen projection is observed and supplied no drawing result.
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
im.write(0x809c+16,'<2H',10,11)
im.intercept(0xb52d4,'Exclude SSD visual events from the temporary HUD-only trajectory.',lambda im:im.return_from())
im.intercept(0x8b984,'Supply a stable mounted-store descriptor; its transformed anchor is independently supplied below.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x301000),im.return_from()))
def place(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+4,4))[0]
    im.cpu.mem_write(destination,struct.pack('<3i',*anchor));im.return_from()
im.intercept(0xb81de,'Supply the transformed Q8 cannon anchor, already checked separately from prediction.',place)
def project(im):
    points.extend(im.read(0x14ec8,'<3i'))
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+16,4))[0]
    im.cpu.mem_write(destination,bytes(4));im.return_from(16)
im.intercept(0xc5759,'Observe each predicted Q8 point before external screen projection.',project)
rng=random.Random(0xa2878);cases=[]
for index in range(512):
    x=rng.randrange(-100000000,100000000);z=rng.randrange(-100000000,100000000)
    y=[0,1,-1,-256,-10000,-100000,-1000000,-2000000][index%8]
    pitch=[0,16384,32768,49152,65535][index%5] if index<160 else rng.randrange(65536)
    cases.append([x,y,z,pitch,rng.randrange(65536),rng.randrange(65536),rng.randrange(-500,2000),*[(-8192,-32),(-16384,0),(-4096,-100)][index%3]])
cases.append([32243583,-1,12289568,0,0,0,0,-16384,0]) # Landed F-117 empty-pylon sight; first update reaches ground.
output=subprocess.check_output([str((args.build/'cannon_prediction_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).splitlines()
assert len(output)==len(cases)
for index,row in enumerate(cases):
    anchor=tuple(row[:3]);pitch,heading,roll,speed,minimum,maximum=row[3:]
    im.write(0xac58,'<i',minimum);im.write(0xac5c,'<i',maximum)
    im.write(0x86c8,'<3H',pitch,heading,roll);im.write(0x13444,'<i',speed);im.write(0x13476,'<H',index%55);points.clear()
    im.call(0xa2878,eax=0,edx=0x300000,limit=1000000)
    got=list(map(int,output[index].split()));assert got==points,(row,got,points)
    assert im.read(0x13476,'<H')[0]==index%55 and im.read(0x16e92,'<H')[0]==0
print(f'HUD-only cannon prediction agrees for {len(cases)} native trajectories and {len(cases)*5} sampled points, with native timer restoration')

mount_image=NativeReference(directory/'TFX.DAT');expected=[]
for aircraft in range(3):
    mount_image.write(0x11b2a,'<H',aircraft)
    for pylon in range(-1,11):
        address=mount_image.call(0x8b984,eax=pylon&0xffffffff)
        expected.append(list(struct.unpack('<3h',mount_image.cpu.mem_read(address,6))))
output=subprocess.check_output([str((args.build/'cannon_prediction_probe').resolve()),str(directory),'mounts']).splitlines()
assert [list(map(int,line.split())) for line in output]==expected
print('All 36 native sight-mount lookups agree, including empty/cannon sentinels and their adjoining stored records')
