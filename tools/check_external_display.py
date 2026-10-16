#!/usr/bin/env python3
"""Compare original external-view status-strip pixels and VGA logical writes.

The original polygon callbacks, VGA AND/OR operations, text formatting and font
painters execute. Radio is disabled at its separate, already checked boundary.
"""
import argparse
import importlib.util
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();directory=a.research/'installs/cd_1994_09/TFX'
spec=importlib.util.spec_from_file_location('research_vga',a.research/'tools/native_vga.py');vga_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(vga_module)
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0xa0000,0x10000);video=vga_module.NativeVGA(im.cpu,aperture=0xa0000);im.cpu.mem_map(0x300000,4096)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=5000)
im.cpu.mem_write(im.native(0x70aa4+0x6810a),struct.pack('<I',im.native(0xe5d5c)));im.cpu.mem_write(im.native(0x70aa4+0x4787e),struct.pack('<I',0x300000));im.cpu.mem_write(0x300000,bytes(range(256)))
im.call(0xde547);im.call(0xb9238,stack=(0,319,0,199));im.call(0xc0634,stack=(199,0,319,0));im.write(0x7612,'<B',1)
rng=random.Random(0x80794);cases=[]
for index in range(512):
    height=[0,.0625,-.0625,-1000,-10000][index%5] if index<64 else rng.uniform(-20000,2000)
    cases.append([height,rng.randrange(-1000,3000),rng.randrange(65536),int(index%17!=0),index%256])
output=subprocess.check_output([str((a.build/'external_display_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode());stride=128000;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    height,speed,heading,enabled,background=row
    im.write(0x13428,'<f',height);im.write(0x13444,'<i',speed);im.write(0x86ca,'<H',heading);im.write(0x6c40,'<B',enabled)
    video.clear(background);im.call(0x80794,limit=2000000)
    want=video.pixels()+video.mask();got=output[index*stride:(index+1)*stride]
    assert got==want,(index,row,[(i%64000%320,i%64000//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:25])
print(f'External-view strip, shadowed telemetry and complete palette-index/VGA coverage agree in {len(cases)} native frames')
