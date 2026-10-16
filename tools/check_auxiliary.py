#!/usr/bin/env python3
"""Compare original engine, approach, ground and ammunition indicators."""
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
archive=Archive.read(directory/'DID.DAT');entries={item.identifier:item for item in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x20000)
for handle,(name,field) in enumerate((('englite',0x12c28),('aoasprs',0x12c1e),('nwsg',0x12c20)),1):
    raw=archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]);im.cpu.mem_write(0x300000+(handle-1)*0x8000,raw);im.write(field,'<H',handle)
im.intercept(0xc8568,'Supply original auxiliary lamp sprite banks at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x8000),im.return_from()))
video=VgaCapture(im,aperture=0xa0000);im.write(0x6c38,'<B',3)
rng=random.Random(0x8046c);cases=[]
for index in range(512):
    left,right=[rng.choice((0,1,2,11,14)) for _ in range(2)] if index%12<6 else (0,0)
    x,y=[(0,0),(1,0),(2,0),(3,0),(-75,0),(71,0),(0,-78),(0,3),(0,4),(0,35),(0,100),(-15,0),(-16,0),(-17,0),(288,0),(289,0),(300,0)][index%17]
    cases.append([left,right,index%4,index%5,(index%6)-1,int(bool(index&1)),int(bool(index&2)),int(bool(index&4)),x,y])
output=subprocess.check_output([str((args.build/'auxiliary_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
assert len(output)==len(cases)*128002
for index,row in enumerate(cases):
    left,right,redraw,pips,cue,suppressed,ground,landed,x,y=row
    im.write(0x7d72,'<B',left);im.write(0x7d75,'<B',right);im.write(0x10bed,'<B',redraw);im.write(0x1496d,'<B',pips)
    im.write(0x8f82,'<B',cue>=0);im.write(0x8f8a,'<B',max(0,cue));im.write(0x8f8c,'<B',suppressed)
    im.write(0x8d38,'<H',ground);im.write(0x8d3a,'<H',landed);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
    im.cpu.emu_start(im.native(0x8046c),im.native(0x806b3),count=2000000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x806b3)
    want=bytes([im.read(0x7158,'<B')[0],im.read(0x6c38,'<B')[0]])+bytes(video.pixels())+bytes(video.coverage())
    got=output[index*128002:(index+1)*128002]
    assert got==want,(row,[(i,(i-2)%64000%320,(i-2)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Auxiliary indicators agree in {len(cases)} complete native pixel/coverage/refresh-state frames')
