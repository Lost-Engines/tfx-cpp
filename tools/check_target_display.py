#!/usr/bin/env python3
"""Compare original target telemetry, off-sight cues, clamped and plain reticles."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x20000);im.call(0xde547)
names=['MiG-29 Fulcrum','F-117','Efa Eurofighter','AIR AEW','C-130 tanker','SAM site','E3D']
im.intercept(0x7889c,'Supply the selected aircraft profile name; original first-word/uppercase handling executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
projected=[0,0]
def ground_projection(im):
    destination=struct.unpack('<I',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+16,4))[0]
    im.cpu.mem_write(destination,struct.pack('<2h',*projected));im.cpu.reg_write(r.UC_X86_REG_EAX,1);im.return_from(stack_bytes=16)
im.intercept(0xc5759,'Supply the separately verified projected ground point; native distance admission and all marker drawing execute.',ground_projection)
rng=random.Random(0x7f59c);cases=[]
for mode in range(6):
    for index in range(320):
        player=[rng.randrange(-1000000,1000000) for _ in range(3)];position=[rng.randrange(-100000000,100000000) for _ in range(3)]
        heading=rng.randrange(65536);speed=rng.randrange(-2147483648,2147483648)
        x,y=[(160,56),(116,18),(193,94),(0,0),(-32000,32000),(319,199),(10,25),(200,100)][index%8]
        tracking=[rng.randrange(-32000*256,32000*256) for _ in range(2)]
        dx,dy=[(0,0),(1,0),(2,0),(3,0),(-100,0),(12,0),(0,-100),(0,28)][index%8]
        basis=[32767,0,0,0,32767,0,0,0,32767] if index<32 else [rng.randrange(-32768,32768) for _ in range(9)]
        bounds=[(0,0,319,199),(80,2,241,144),(91,4,231,97),(100,50,220,170)][(index//8)%4]
        cases.append([mode,index%2,index%len(names),*player,*position,heading,speed,x,y,*tracking,dx,dy,*basis,*bounds])
output=subprocess.check_output([str((args.build/'target_display_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
stride=128000;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    mode,sight,name=row[:3];player=row[3:6];position=row[6:9];heading,speed,x,y,tx,ty,dx,dy=row[9:17];basis=row[17:26];xmin,ymin,xmax,ymax=row[26:]
    im.cpu.mem_write(0x300000,names[name].encode()+b'\0');im.cpu.mem_write(0x310000,struct.pack('<3i3Hi',*position,0,heading,0,speed))
    for field,value in zip((0x13424,0x13430,0x1343c),player):im.write(field,'<i',value)
    im.write(0x1345e,'<9h',*basis);im.write(0x135cc,'<2h',x,y);im.write(0x135c0,'<2i',tx,ty);im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    primary,secondary=(0x6da6,0x6dba) if sight else (0x6e13,0x6dd2)
    im.write(0x12c10,'<I',im.data+primary);im.write(0x12c14,'<I',im.data+secondary);im.write(0x12c1a,'<h',4 if sight else 8);im.write(0x12c18,'<h',5 if sight else 10)
    im.call(0xb9238,stack=(xmin,xmax,ymin,ymax));im.call(0xc0634,stack=(ymax,ymin,xmax,xmin));video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    if mode==5:
        projected[:]=[x,y]
        im.call(0x7f2a4,eax=position[0]&0xffffffff,edx=position[1]&0xffffffff,ebx=position[2]&0xffffffff,limit=2000000)
    elif mode<3:im.call((0x7f59c,0x7f000,0x7ee9c)[mode],eax=0x310000,limit=2000000)
    else:
        half=(5 if sight else 10) if mode==4 else (4 if sight else 8)
        im.call(0xcda48,stack=(im.data+(secondary if mode==4 else primary),(y-half)&65535,(x-half)&65535,6),limit=1000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Target telemetry, ground/directional cues and both sizes of primary/lock/edge markers agree in {len(cases)} complete native pixel/coverage frames')
