#!/usr/bin/env python3
"""Compare corrected viewport records and original cockpit composition.

The original compiled overlay executes. The VGA-to-VGA footer transfer is
supplied at its hardware boundary from independently deplaned source bytes;
its native source/destination rectangle is checked and applied verbatim.
"""
import argparse
from pathlib import Path
import shlex
import struct
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';probe=str((args.build/'cockpit_frame_probe').resolve())
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={e.identifier:e for e in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x20000);video=VgaCapture(im,aperture=0xa0000)
def text(address):
    if not address:return ''
    data=bytes(im.cpu.mem_read(address,128));return data[:data.index(0)].decode('latin1').replace('\\','/').lstrip('/')
layouts=[]
for index in range(29):
    at=0x5da4+index*20
    centre,panel,handle,overlay,overlay_handle,bottom,callback=im.read(at,'<HIHIHHI')
    if centre>=32768:centre-=65536
    layouts.append([centre,bottom,callback-im.layout['objects'][0]['preferred_base']+im.layout['objects'][0]['file'] if callback else 0,text(panel),text(overlay)])
output=subprocess.check_output([probe,str(directory),'layouts']).decode().splitlines()
assert len(output)==29
for index,(line,want) in enumerate(zip(output,layouts)):
    fields=shlex.split(line);got=[*map(int,fields[:3]),*fields[3:]];assert got==want,(index,got,want)
# Resource resolution returns only the selected original compiled overlay.
current_overlay=0x300000
im.intercept(0xc85a0,'Supply the selected compiled cockpit artwork at its resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,current_overlay),im.return_from()))
projection=[]
for address in (0xb9238,0xc84b1):im.intercept(address,'Exclude 3D viewport-driver setup; this capture compares the static frame.',lambda im:im.return_from())
def project(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);projection[:]=struct.unpack('<4i',im.cpu.mem_read(stack+4,16))[:2];im.return_from()
im.intercept(0xb94da,'Record the original viewport projection origin without a world scene.',project)
current_panel=b'';copies=[]
def copy_panel(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);dy,dx,segment,height,width,sy,sx,source=struct.unpack('<8I',im.cpu.mem_read(stack+4,32))
    assert segment==0xa000 and source==0x1234,(segment,source)
    assert width>0 and height>0 and sx+width<=320 and sy+height<=len(current_panel)//320,(dy,dx,height,width,sy,sx)
    assert dx+width<=320 and dy+height<=200,(dy,dx,height,width)
    copies.append((dy,dx,height,width,sy,sx))
    for row in range(height):
        for column in range(width):
            x=dx+column;y=dy+row;plane=x%4;offset=y*80+x//4
            video.planes[plane][offset]=current_panel[(sy+row)*320+sx+column];video.written[plane][offset]=255
    im.return_from(32)
im.intercept(0xc87c4,'Supply the original VGA-to-VGA footer transfer at the hardware-copy boundary; preserve its complete native rectangle.',copy_panel)
cases=[(view,x,y) for view in (0,1,3,7,19,28) for x in (-8,0,8) for y in (-100,-1,0,1,14,28,50,54,55,200,32767)]
output=subprocess.check_output([probe,str(directory),'frame'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
stride=128016;assert len(output)==len(cases)*stride
for index,(view,x,y) in enumerate(cases):
    centre,bottom,callback,panel,overlay=layouts[view];at=0x5da4+view*20
    if overlay:
        raw=archive.unpack(entries[archive.hash_name(overlay)]);current_overlay=0x300000 if view==0 else 0x310000;im.cpu.mem_write(current_overlay,raw);im.write(at+12,'<H',1)
    current_panel=b''
    if panel and bottom<199:
        raw=archive.unpack(entries[archive.hash_name(panel)]);size=len(raw)//4;decoded=bytearray(len(raw))
        for plane in range(4):decoded[plane::4]=raw[plane*size:(plane+1)*size]
        current_panel=bytes(decoded)
    im.write(at+6,'<H',0x1234 if panel else 0)
    im.write(0x87b6,'<H',view);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y);im.write(0x10bed,'<B',3)
    video.reset();copies.clear();projection.clear()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x74498,limit=2000000)
    # Isolate the projection helper using the clamped frame coordinates; this is
    # not a claim about the whole game's pre-render camera/update ordering.
    im.call(0x73cd0,limit=100000)
    want=struct.pack('<4i',im.read(0x10be8,'<h')[0],im.read(0x10be6,'<h')[0],*projection)+bytes(video.pixels())+bytes(video.coverage())
    got=output[index*stride:(index+1)*stride]
    assert got==want,((view,x,y),copies,[(i,(i-16)%64000%320,(i-16)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'All 29 native viewport records agree; cockpit composition agrees in {len(cases)} complete pixel/coverage/offset/origin frames with the declared VGA-copy boundary')
