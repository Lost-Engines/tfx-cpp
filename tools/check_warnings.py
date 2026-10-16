#!/usr/bin/env python3
"""Compare original cockpit warning lamps, phase state and one-shot threat sound."""
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
for handle,name in enumerate(('warlites','warlite2'),1):
    raw=archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]);im.cpu.mem_write(0x300000+(handle-1)*0x8000,raw)
    im.write(0x12c38 if handle==1 else 0x12c36,'<H',handle)
im.intercept(0xc8568,'Supply the original warning sprite banks at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x8000),im.return_from()))
sounds=[]
im.intercept(0xa4dfc,'Record the original sound request without playing it.',lambda im:(sounds.append(im.cpu.reg_read(r.UC_X86_REG_EAX)),im.return_from()))
video=VgaCapture(im,aperture=0xa0000)
rng=random.Random(0x81a48);cases=[]
for index in range(1024):
    systems=[rng.choice((0,1,2,11,14)) for _ in range(12)] if index>=32 else [2]*12
    if index<12:systems[index]=11
    if 12<=index<24:systems[index-12]=14
    x,y=[(0,0),(1,0),(2,0),(3,0),(-69,0),(68,0),(0,-104),(0,80),(0,100)][index%9]
    cases.append([*systems,int(bool(index&1)),int(bool(index&2)),int(bool(index&4)),(index%17)-1,int(bool(index&8)),int(index>=24 and index%3!=0),x,y])
output=subprocess.check_output([str((args.build/'warning_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
assert len(output)==len(cases)*128005
for index,row in enumerate(cases):
    systems=row[:12];autopilot,hook,permission,category,stall,threat,x,y=row[12:]
    im.write(0x7d70,'<12B',*systems);im.write(0x14958,'<H',autopilot);im.write(0x8d12,'<H',hook)
    im.write(0x763c,'<H',permission);im.write(0x7638,'<I',0x310000 if category>=0 else 0)
    im.cpu.mem_write(0x310006,bytes([0]));im.write(0x80b9,'<B',max(0,category))
    im.write(0x13474,'<H',stall);im.write(0x763e,'<H',threat);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    video.reset();sounds.clear()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x81a48,limit=2000000)
    assert sounds in ([],[43]),sounds
    want=struct.pack('<HHB',im.read(0x7622,'<H')[0],im.read(0x7624,'<H')[0],bool(sounds))+bytes(video.pixels())+bytes(video.coverage())
    got=output[index*128005:(index+1)*128005]
    assert got==want,(row,[(i,(i-5)%64000%320,(i-5)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Warning lamps agree in {len(cases)} complete native pixel/coverage/phase/sound frames')
