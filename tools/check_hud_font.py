#!/usr/bin/env python3
"""Compare complete original HUD/arming-font writes, including clipping and NUL."""
import argparse
from pathlib import Path
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x10000);video=VgaCapture(image)
cases=[(bytes([code]),20+code%4,20,colour) for code in range(256) for colour in (0,1)]
texts=[b'',b'A\0B',b'E.F.2000',b'SIDEWINDER',b'ROLL INERTIA: 100 PERCENT',b'CURRENT SELECTION',b'0123456789',bytes(range(1,32))]
cases.extend((text,x,y,1) for text in texts for x,y in ((0,0),(1,1),(2,20),(3,20),(-3,20),(317,20),(20,197),(20,199)))
rows=[];expected=[]
for text,x,y,colour in cases:
    cpu.mem_write(0x300000,text+bytes(1));video.reset()
    for plane in video.planes:plane[:]=bytes([55])*16000
    image.call(0x87154,eax=colour,edx=x&0xffffffff,ebx=y&0xffffffff,ecx=0x300000,limit=1000000)
    rows.append(f'{x} {y} {colour} {text.hex() or "-"}\n');expected.append(bytes(video.pixels()))
result=subprocess.run([str(args.build/'hud_font_probe'),str(args.data_dir/'TFX.DAT')],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr
assert len(result.stdout)==len(expected)*64000
for number,frame in enumerate(expected):
    found=result.stdout[number*64000:(number+1)*64000]
    assert found==frame,(cases[number],sum(a!=b for a,b in zip(found,frame)),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(found,frame)) if a!=b][:12])
print(len(cases),'complete native HUD/arming-font frames agree, including every byte code, black/white ink, plane phases, edge clipping and embedded NUL')
