#!/usr/bin/env python3
"""Compare complete original post-ejection outcomes and recovery map decisions.

The actual launcher prefix and recovery routine execute. Parser variable lookup,
resource upload and VGA pixel reads are supplied boundaries; the native start-cell
pixel marker executes. Only valid image coordinates are compared.
"""
import argparse
from collections import Counter
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
a=parser.parse_args();directory=a.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(a.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,4096);video=VgaCapture(im,aperture=0xa0000)
screens={}
variables={0x208:0x300000,0x210:0x300004,0x310:0x300008};loaded=[]
def variable(image):
    address=image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data
    image.cpu.reg_write(r.UC_X86_REG_EAX,variables[address]);image.return_from()
im.intercept(0xb1334,'Resolve supplied outcome/status/safe variables; original assignments execute',variable)
im.intercept(0xc6348,'Exclude host VGA mode setup; supplied indexed framebuffer retains native pixel writes',lambda image:image.return_from())
def upload(image):
    address=image.cpu.reg_read(r.UC_X86_REG_EAX);name=bytes(image.cpu.mem_read(address,40)).split(b'\0')[0].decode();loaded.append(name)
    if name not in screens:screens[name]=archive.unpack(entries[archive.hash_name('iff/raw/'+name)])
    raw=screens[name]
    assert raw[:4]==b'war ' and len(raw)==64772
    for plane in range(4):video.planes[plane][:]=raw[772+plane::4]
    image.cpu.reg_write(r.UC_X86_REG_EAX,1);image.return_from()
im.intercept(0xc6f64,'Upload the original named recovery image at the separately verified screen resource boundary',upload)
def read_pixel(image):
    stack=image.cpu.reg_read(r.UC_X86_REG_ESP);y,x=struct.unpack('<2I',image.cpu.mem_read(stack+4,8))
    assert x<320 and y<200,(x,y)
    image.cpu.reg_write(r.UC_X86_REG_EAX,video.planes[x%4][y*80+x//4]);image.return_from(8)
im.intercept(0xc707c,'Supply VGA indexed reads after executing the original start-cell marker',read_pixel)
rng=random.Random(0x72424);cases=[]
for index in range(3072):
    region=index%5;ejected=int(index%13!=0);fatal=int(index%17==0);damaged=index%2;violations=1 if index%11==0 else 0
    start=[rng.randrange(200)*2048+rng.randrange(2048) for _ in range(2)]
    position=start if index%7==0 else [rng.randrange(200)*2048+rng.randrange(2048) for _ in range(2)]
    cases.append([region,ejected,fatal,damaged,violations,*start,*position,index%5,index%5,index%2])
output=subprocess.check_output([str((a.build/'recovery_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
counts=Counter()
for index,(row,line) in enumerate(zip(cases,output)):
    region,ejected,fatal,damaged,violations,sx,sz,x,z,outcome,status,safe=row
    im.write(0xabe9,'<B',2 if ejected else 0);im.write(0x13479,'<B',fatal);im.write(0xe75c,'<h',violations);im.write(0x8e18,'<d',10.0 if damaged else 0.0);im.write(0x11b3b,'<B',region)
    im.write(0x11958,'<2i',sx,sz);im.write(0x13424,'<i',x);im.write(0x1343c,'<i',z);im.cpu.mem_write(0x300000,struct.pack('<3i',outcome,status,safe));loaded.clear();video.reset()
    im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202);im.cpu.emu_start(im.native(0x72a21),im.native(0x72a91),count=200000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x72a91)
    expected=list(struct.unpack('<3i',im.cpu.mem_read(0x300000,12)));actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected,loaded)
    counts[tuple(expected)]+=1
print(f'Post-ejection outcome/status/safe agree in {len(cases)} complete original launcher/map cases across all five retail recovery maps; {len(counts)} resulting states')
