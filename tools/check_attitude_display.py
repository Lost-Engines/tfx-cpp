#!/usr/bin/env python3
"""Compare original heading-strip and projected pitch-ladder VGA pixels.

Original angle setup, projection, clipping, solid/patterned lines and sprites
execute. Only external resource resolution is supplied with original bytes.
"""
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
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x400000,0x20000)
for handle,(name,field) in enumerate((('dat/fwshdg.dat',0x12c3c),('spr/ladnums.spr',0x12c40)),1):
    raw=archive.unpack(entries[archive.hash_name(name)]);im.cpu.mem_write(0x400000+(handle-1)*0x10000,raw);im.write(field,'<H',handle)
im.intercept(0xc8568,'Supply original heading/ladder sprite banks at the external resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x400000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x10000),im.return_from()))
im.call(0x809e4)
rng=random.Random(0x80ab8);cases=[]
for mode in range(2):
    for index in range(512):
        pitch=[0,1,63,64,1819,1820,1821,16384,32768,49152,65535][index%11] if index<176 else rng.randrange(65536)
        heading=[0,1,182,183,184,32767,32768,65534,65535][index%9] if index<176 else rng.randrange(65536)
        roll=[0,16384,32768,49152,65535][index%5] if index<176 else rng.randrange(65536)
        dx,dy=[(0,0),(1,0),(2,0),(3,0),(-4,0),(4,0),(0,-10),(0,28),(0,50),(0,100)][index%10]
        projection_pitch,projection_roll=(pitch,roll) if index%3 else (rng.randrange(65536),rng.randrange(65536))
        cases.append([mode,pitch,heading,roll,projection_pitch,projection_roll,159,56+int(dy/2),dx,dy])
output=subprocess.check_output([str((args.build/'attitude_display_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
stride=128000;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    mode,pitch,heading,roll,projection_pitch,projection_roll,cx,cy,dx,dy=row
    im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    im.call(0xb9238,stack=(0,319,0,199));im.call(0xc84b1,stack=(0,319,0,199,cy));im.call(0xc82b9,stack=(projection_pitch,projection_roll))
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    if mode==0:im.call(0x80ffc,eax=0,edx=-9,ebx=(-heading)&0xffffffff,ecx=115,stack=(214,21,86,128,200,10,95),limit=1000000)
    else:im.call(0x80ab8,eax=6,edx=(-pitch)&0xffffffff,ebx=(-roll)&0xffffffff,ecx=100,stack=(15,220,120),limit=2000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Heading strip and pitch ladder agree in {len(cases)} complete native pixel/coverage frames, including projection, clipping and patterned lines')
