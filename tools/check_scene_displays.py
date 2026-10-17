#!/usr/bin/env python3
"""Compare original MFD camera requests and pixel overlays at the 3D-renderer boundary."""
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
parser.add_argument('--world-bounds',action='store_true',help='use the initialized TFX mission movement limits')
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
rng=random.Random(0x88378);total=0
for step in (0,512,-1024):
    im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000)
    im.cpu.mem_map(0x300000,4096);im.write(0x7dcc,'<h',step)
    if args.world_bounds:im.write(0xac58,'<2i',-16384,0)
    request=[];projection=[0,0]
    def scene(im):
        side=im.cpu.reg_read(r.UC_X86_REG_EAX)&65535;assert side in (0,2)
        stack=im.cpu.reg_read(r.UC_X86_REG_ESP)
        angles=list(struct.unpack('<3i',im.cpu.mem_read(stack+4,12)))
        position=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]
        x,y,width,height=im.read(0x7c98+side*8,'<4h');dx=im.read(0x10be8,'<h')[0];dy=im.read(0x10be6,'<h')[0]
        word=lambda n:struct.unpack('<h',struct.pack('<H',n&65535))[0]
        request[:]=[*position,*angles,word(x+dx),word(y+dy),word(x+dx+width),word(y+dy+height)]
        im.return_from(12)
    im.intercept(0x880e4,'Record the original camera request; full world rendering and viewport installation are a separate consumer.',scene)
    def project(im):
        stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+16,4))[0]
        im.cpu.mem_write(destination,struct.pack('<2h',*projection));im.return_from(16)
    im.intercept(0xc5759,'Supply a controlled projected target point; the original reticle and range painters execute.',project)
    cases=[]
    for index in range(768):
        page=6 if index%3 else 7;side=index%2;aircraft=(index//2)%3
        position=[rng.randrange(-100000,400000),rng.randrange(-9000,-32),rng.randrange(-100000,400000)]
        angles=[rng.randrange(65536) for _ in range(3)];free=[rng.randrange(65536) for _ in range(2)]
        tracking=(index//3)%2;target=[rng.randrange(-20000000,100000000) for _ in range(3)]
        ground=[rng.randrange(-100000,400000),0,rng.randrange(-100000,400000)]
        dx,dy=[(0,0),(1,0),(2,0),(3,0),(-10,-100),(12,8)][index%6]
        x,y=[(83,150),(238,150),(2,2),(318,198),(-10,20)][index%5]
        cases.append([page,side,aircraft,*position,*angles,*free,tracking,(index*53)&65535,*target,*ground,dx,dy,x,y])
    output=subprocess.check_output([str((args.build/'scene_display_probe').resolve()),str(directory),str(step),*(['--world-bounds']if args.world_bounds else [])],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
    stride=128068;assert len(output)==len(cases)*stride
    for index,row in enumerate(cases):
        page,side,aircraft=row[:3];px,py,pz=row[3:6];pitch,heading,roll=row[6:9];free_pitch,free_heading=row[9:11];tracking=row[11];tracking_roll=row[12];target=row[13:16];ground=row[16:19];dx,dy,x,y=row[19:]
        im.write(0x11b2a,'<H',aircraft)
        for field,value in zip((0x13424,0x13430,0x1343c),(px,py,pz)):im.write(field,'<i',value)
        im.write(0x86c8,'<3H',pitch,heading,roll);im.write(0x8828,'<2H',free_pitch,free_heading)
        im.write(0x8840,'<I',1 if tracking else 0);im.write(0x135a0,'<3i',*target)
        im.write(0x5d44,'<h',0);im.write(0x5c40,'<3i',*ground)
        im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy);projection[:]=[x,y]
        video.reset();request.clear()
        for plane in video.planes:plane[:]=bytes([99])*16000
        # 0xc9714 writes pitch/heading only; 0x88378 also reads the following
        # caller-local roll word. Supply that otherwise uninitialised input explicitly.
        im.cpu.mem_write(im.STACK-28,struct.pack('<H',tracking_roll))
        im.call(0x88378 if page==6 else 0x88530,eax=side*2,limit=1000000)
        header=[*request,im.read(0x7dc4,'<h')[0],*im.read(0x7dc6,'<3H'),im.read(0x7dcc,'<h')[0],*im.read(0x8828,'<2H')]
        want=struct.pack('<17i',*header)+bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
        assert got==want,(step,index,row,[(i,(i-68)%64000%320,(i-68)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
    total+=len(cases)
print(f'MFD camera requests, gimbal/orbit/reticle state and pixel overlays agree in {total} native cases; full world rendering is separate')
