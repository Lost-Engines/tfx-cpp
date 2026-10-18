#!/usr/bin/env python3
"""Compare original MFD pages using synthetic inventory, flight and damage telemetry."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'))
from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT')
entry=next(item for item in archive.entries if item.identifier==archive.hash_name('spr/disp12.spr'))
im=NativeReference(directory/'TFX.DAT',data_base=0x100000)
im.cpu.mem_map(0x300000,0x10000);im.cpu.mem_write(0x300000,archive.unpack(entry))
for address in (0xc85a0,0xc8568):im.intercept(address,'Supply the original decoded disp12 sprite bank at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
im.write(0x12c3a,'<H',1)
video=VgaCapture(im,aperture=0xa0000)
im.call(0xde547)
# Execute both native dispatchers, intercepting only their selected page boundary.
selected=[]
page_handlers={0x8723c:0,0x87854:1,0x874dc:2,0x87b3c:3,0x876e8:4,0x87eac:5,0x88378:6,0x88530:7,0x88778:8,0x823d0:9,0x88664:10,0x87960:11}
dispatch=NativeReference(directory/'TFX.DAT')
for handler,page in page_handlers.items():
    dispatch.intercept(handler,'Record the selected MFD page; individual painters are compared separately.',lambda im,page=page:(selected.append(page),im.return_from()))
for side in range(2):
    for mode in range(9):
        dispatch.write(0x713a if side==0 else 0x713e,'<H',mode)
        dispatch.call(0x88e38 if side==0 else 0x8905c)
actual_pages=subprocess.check_output([str((args.build/'mfd_probe').resolve()),str(directory),'--pages'])
assert list(map(int,actual_pages.split()))==selected
rng=random.Random(0x88e38);cases=[]
for page in (*range(6),11):
    for side in range(2):
        for aircraft in range(3):
            for variant in range(14):
                speed=rng.randrange(-1000,2000);height=-rng.random()*2000;heading=rng.randrange(65536)
                fuel=[0,999.5,1000,2499.5,2500,9999,12000][variant%7]
                gauge=[0,1,311,312,2495,2496,2499,2500,5000,7500,9999,10000,12000,-32768][variant]
                burn=[0,2,9,10,100][variant%5];throttle=[0,.09999999,.5,.9999999,1,1.2][variant%6]
                x,y=[(0,0),(1,0),(2,0),(3,0),(-3,0),(12,0),(0,-100),(0,8),(0,20),(0,28),(0,36),(0,60),(0,70),(0,0)][variant]
                systems=[rng.choice((0,1,2,11,14)) for _ in range(12)]
                stores=[(rng.randrange(23),rng.choice((0,1,4))) for _ in range(11)]
                selected=rng.randrange(10);guns=variant%2;locked=(variant//2)%2
                row=[page,side,aircraft,speed,height,heading,fuel,gauge,burn,throttle,x,y,rng.random()*1.5,rng.random()*1.5,*systems,selected,guns,locked,*[v for pair in stores for v in pair]]
                cases.append(row)
# Ground-impact frames reach exact zero height. Watcom omits the sign of
# decimal zero, including a negative nonzero value that rounds to zero.
for page in (2,3,11):
    for side in range(2):
        for aircraft in range(3):
            base=next(row for row in cases if row[:3]==[page,side,aircraft])
            for value in (0.0,-0.0,0.0001,-0.0001,0.005,-0.005,0.5,-0.5):
                row=list(base);row[4]=value;row[6]=value;row[12:14]=[value,value]
                cases.append(row)
output=subprocess.check_output([str((args.build/'mfd_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
assert len(output)==len(cases)*128000
for index,row in enumerate(cases):
    page,side,aircraft,speed,height,heading,fuel,gauge,burn,throttle,x,y=row[:12]
    systems=row[14:26];selected,guns,locked=row[26:29];stores=row[29:]
    im.write(0x14880,'<2d',*row[12:14])
    im.write(0x11b2a,'<H',aircraft);im.write(0x13444,'<i',speed);im.write(0x13428,'<f',height);im.write(0x86ca,'<H',heading)
    im.write(0x14858,'<d',fuel);im.write(0x6c3c,'<h',gauge);im.write(0x6c3a,'<h',burn);im.write(0x133f8,'<f',throttle)
    im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y);im.write(0x7d70,'<12B',*systems)
    im.write(0x93ae,'<h',(9,3,7)[aircraft]);im.write(0x93b0,'<h',selected);im.write(0x7140,'<B',not guns);im.write(0x135d0,'<I',locked)
    im.write(0x13374,'<22B',*stores)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call({0:0x8723c,1:0x87854,2:0x874dc,3:0x87b3c,4:0x876e8,5:0x87eac,11:0x87960}[page],eax=side*2,limit=2000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*128000:(index+1)*128000]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Seven MFD pages agree in {len(cases)} complete native pixel/coverage frames across both display positions and all three aircraft; all 18 native page selections also agree')
