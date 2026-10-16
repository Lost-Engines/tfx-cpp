#!/usr/bin/env python3
"""Compare HUD sprite banks and embedded monochrome masks with original VGA blits."""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture
from native_planner import NativePlanner

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
records=json.loads((args.research/'analysis/cockpits/hud-layout.json').read_text())
resources=NativePlanner(directory,args.research)
im=NativeReference(directory/'TFX.DAT',data_base=0x100000)
im.cpu.mem_map(0x300000,0x10000)
video=VgaCapture(im,aperture=0xa0000)
rng=random.Random(0xc0ef8);cases=[];expected=[]
def capture(command,file,stack):
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(file,stack=tuple(value&0xffffffff for value in stack),limit=2000000)
    cases.append(command);expected.append(bytes(video.pixels())+bytes(video.coverage()))
for name in sorted({bank['name'] for case in records['cases'] for bank in case['loaded_banks']}):
    raw=resources.read(name);im.cpu.mem_write(0x300000,raw)
    for frame in range(raw[0]):
        x,y=160+frame%4,100
        capture(f'S {name} {frame} {x} {y}',0xc0ef8,(y,x,frame,0x300000))
    # All plane phases plus the four clipped corners, including large map/ladder banks.
    for x,y in [(0,0),(319,0),(0,199),(319,199),(-3,100),(320,100),(160,-3),(160,200)]:
        frame=raw[0]-1
        capture(f'S {name} {frame} {x} {y}',0xc0ef8,(y,x,frame,0x300000))
bitmaps={draw['native_pointer'] for case in records['cases'] for draw in case['draws'] if draw['kind']=='monochrome'}
for pointer in sorted(bitmaps):
    address=int(pointer,16)-0xa0000
    for x,y in [(20,20),(0,0),(317,20),(20,197),(-3,20)]:
        for colour in (0,127):capture(f'B {973476+address} {x} {y} {colour}',0xcda48,(im.data+address,y,x,colour))
output=subprocess.check_output([str((args.build/'sprite_probe').resolve()),str(directory)],input=('\n'.join(cases)+'\n').encode())
assert len(output)==len(expected)*128000
for index,(case,want) in enumerate(zip(cases,expected)):
    got=output[index*128000:(index+1)*128000]
    assert got==want,(case,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'HUD image blits agree in {len(cases)} complete pixel/coverage frames across 18 original banks and {len(bitmaps)} embedded masks')
