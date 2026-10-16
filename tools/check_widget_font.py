#!/usr/bin/env python3
"""Compare the original widget font's measurement and complete VGA output.

The original proportional code-object font executes directly, including its
compiled plane selection. No font graphics, game instructions or captured
frames are bundled. Original resources remain read-only.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x10000);video=VgaCapture(image)
cases=[(bytes([code]),20+code%4,20,0 if code%17==0 else 127) for code in range(256)]
texts=[b'',b'OPERATION EAGLE',b'Enforce the no-fly zone',b'Wingman 2: 123.45',b'abcXYZ',b'A\0B','Höhe über Straße'.encode('cp437'),'Décollage immédiat'.encode('cp437')]
cases.extend((text,20+phase,y,255) for text in texts for phase in range(4) for y in (0,1,2,20,198))
rows=[];expected=[]
for text,x,y,colour in cases:
    cpu.mem_write(0x300000,text+bytes(1));width=image.call(0xd1701,stack=(0x300000,));video.reset();image.call(0xd172b,stack=(0x300000,y,x,colour),limit=1000000)
    rows.append(f'{x} {y} {colour} {text.hex() or "-"}\n');expected.append(struct.pack('<I',width)+bytes(video.pixels())+bytes(video.coverage()))
result=subprocess.run([str(args.build/'widget_font_probe'),str(args.data_dir/'TFX.DAT')],input=''.join(rows).encode(),capture_output=True);assert result.returncode==0,result.stderr
size=4+64000*2;assert len(result.stdout)==len(expected)*size
for index,frame in enumerate(expected):
    actual=result.stdout[index*size:(index+1)*size]
    assert actual==frame,(index,rows[index],next((i for i,(a,b) in enumerate(zip(actual,frame)) if a!=b),None))
print(len(cases),'complete native widget-font cases agree in width, every pixel and written coverage, including all byte codes, horizontal phases, accents, top clamp and bottom edge')
