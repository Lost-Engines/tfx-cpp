#!/usr/bin/env python3
"""Compare decoded compiled planner artwork with the complete native VGA painter.

The artwork remains in the user's original TFX.DAT. No framebuffer or paint
program is bundled with the reconstruction. VGA writes are captured externally;
the complete original painter executes without intercepted drawing helpers.
"""
import argparse
from pathlib import Path
import subprocess
import random
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');video=VgaCapture(image)
image.call(0xa9c34,limit=1000000)
expected=bytes(video.pixels())+bytes(video.coverage())
result=subprocess.run([str(args.build/'planning_probe'),str(args.data_dir),'--panel'],capture_output=True);assert result.returncode==0,result.stderr
assert result.stdout==expected,('compiled planner artwork differs',next((i for i,(a,b) in enumerate(zip(result.stdout,expected)) if a!=b),None))
image.cpu.mem_map(0x300000,0x10000);image.write(0x18078,'<I',0x300000);rng=random.Random(0xab3ac);rows=[];palettes=[]
for case in range(128):
    colours=bytes(rng.randrange(64) for _ in range(768));image.cpu.mem_write(0x30000f,colours);image.call(0xab3ac)
    rows.append(colours.hex()+'\n');palettes.append(bytes(image.cpu.mem_read(image.data+0x20ce0,768)))
result=subprocess.run([str(args.build/'planning_probe'),str(args.data_dir),'--palette'],input=''.join(rows).encode(),capture_output=True);assert result.returncode==0,result.stderr
assert result.stdout==b''.join(palettes),'planner palette composition differs'
print('Complete native compiled planner panel matches in all 64000 pixels and written coverage, including plane-mask details and transparent map region; 128 complete native map/UI/marker palette compositions agree')
