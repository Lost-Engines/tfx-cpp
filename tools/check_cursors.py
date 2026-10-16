#!/usr/bin/env python3
"""Compare original embedded menu pointers with native VGA sprite drawing."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');video=VgaCapture(image);rng=random.Random(0xd20d8);rows=[];frames=[]
for style in range(2):
    for active in range(2):
        record=(0xdf30 if active else 0xdf08)+style*20;pointer,=image.read(record,'<I');dx,dy=image.read(record+8,'<2h')
        positions=[(0,0),(319,0),(0,199),(319,199)]+[(rng.randrange(320),rng.randrange(200)) for _ in range(32)]
        for x,y in positions:
            video.reset()
            for plane in video.planes:plane[:]=bytes([99])*16000
            image.call(0xc0ef8,stack=((y+dy)&0xffffffff,(x+dx)&0xffffffff,0,pointer),limit=1000000)
            rows.append(f'{style} {active} {x} {y}\n');frames.append(bytes(video.pixels()))
result=subprocess.run([str(args.build/'cursor_probe'),str(args.data_dir/'TFX.DAT')],input=''.join(rows).encode(),capture_output=True);assert result.returncode==0,result.stderr.decode();assert len(result.stdout)==len(frames)*64000
for index,frame in enumerate(frames):
    actual=result.stdout[index*64000:(index+1)*64000];assert actual==frame,(rows[index],[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(actual,frame)) if a!=b][:30])
print(len(frames),'native menu-pointer frames agree, including all four clipped corners, transparent holes and both active/idle styles')
