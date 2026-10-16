#!/usr/bin/env python3
"""Compare original per-viewport sprite, mask and text clipping, including plane edges."""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={item.identifier:item for item in archive.entries}
records=json.loads((args.research/'analysis/cockpits/hud-layout.json').read_text())
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x10000);video=VgaCapture(im,aperture=0xa0000)
rng=random.Random(0xc0634);cases=[];expected=[]
def capture(command,file,bounds,stack=(),registers=None,raw=False):
    left,top,right,bottom=bounds
    im.call(0xc0634,stack=(bottom,top,right,left))
    if raw:
        for field,value in ((0x4fb80,left),(0x4fb84,right),(0x4fb88,top),(0x4fb8c,bottom)):
            im.cpu.mem_write(im.native(0x70aa4+field),struct.pack('<I',value))
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(file,stack=tuple(v&0xffffffff for v in stack),**(registers or {}),limit=2000000)
    cases.append(command);expected.append(bytes(video.pixels())+bytes(video.coverage()))
rectangles=[(0,0,319,199),(100,20,156,100),(101,20,157,100),(102,20,158,100),(103,20,159,100),(55,132,111,169),(213,133,264,167),(0,190,319,199)]
for name in sorted({bank['name'] for case in records['cases'] for bank in case['loaded_banks']}):
    bank=archive.unpack(entries[archive.hash_name(name)]);im.cpu.mem_write(0x300000,bank)
    for index in range(32):
        bounds=rectangles[index%len(rectangles)];left,top,right,bottom=bounds
        frame=index%bank[0];x=[left-1,left,left+1,right-1][index//8];y=top+3
        capture(f'C {name} {frame} {x} {y} '+' '.join(map(str,bounds)),0xc0ef8,bounds,(y,x,frame,0x300000))
bitmaps={int(draw['native_pointer'],16)-0xa0000 for case in records['cases'] for draw in case['draws'] if draw['kind']=='monochrome'}
for field in sorted(bitmaps):
    for index,bounds in enumerate(rectangles):
        x=bounds[0]-2;y=bounds[1]-2;colour=0 if index%2 else 127
        capture(f'D {973476+field} {x} {y} {colour} '+' '.join(map(str,bounds)),0xcda48,bounds,(im.data+field,y,x,colour))
for character in range(256):
    text=bytes([character,65,66]);im.cpu.mem_write(0x300000,text+bytes(1));bounds=rectangles[character%len(rectangles)]
    x=bounds[2]-2;y=bounds[1]-2
    capture(f'T {x} {y} 1 {text.hex()} '+' '.join(map(str,bounds)),0x87154,bounds,registers=dict(eax=1,edx=x&0xffffffff,ebx=y&0xffffffff,ecx=0x300000))
for index in range(512):
    width=rng.choice((4,8,16,32,56,200,272,320,508));height=4;left=rng.randrange(-width,321);centre=left+width//2
    bounds=(rng.choice((0,4,100)),0,rng.choice((155,156,159,160,319,320)),200)
    pixels=bytes((x%254)+1 for y in range(height) for x in range(width));raw=bytes([1,3,0,width//2,height])+b''.join(pixels[n::4] for n in range(4));im.cpu.mem_write(0x300000,raw)
    capture(f'P {width} {height} {centre} 22 '+' '.join(map(str,bounds))+' 1',0xc0ef8,bounds,(22,centre,0,0x300000),raw=True)
# A directed case reaches the next stored plane after clipping both horizontal edges.
width=320;height=4;left=-162;bounds=(4,0,159,200);pixels=bytes((x%254)+1 for y in range(height) for x in range(width))
im.cpu.mem_write(0x300000,bytes([1,3,0,width//2,height])+b''.join(pixels[n::4] for n in range(4)))
capture('P 320 4 -2 22 4 0 159 200 1',0xc0ef8,bounds,(22,-2,0,0x300000),raw=True)
output=subprocess.check_output([str((args.build/'sprite_probe').resolve()),str(directory)],input=('\n'.join(cases)+'\n').encode())
assert len(output)==len(cases)*128000
for index,(case,want) in enumerate(zip(cases,expected)):
    got=output[index*128000:(index+1)*128000]
    assert got==want,(case,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Viewport clipping agrees in {len(cases)} complete native pixel/coverage frames, including all byte codes and planar edge reads')
