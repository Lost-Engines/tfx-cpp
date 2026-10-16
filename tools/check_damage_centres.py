#!/usr/bin/env python3
"""Compare targetable SSD damage-box centres with the original 2.05 enumerator."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args()
text=(args.research/'analysis/maps/data.js').read_text();objects=json.loads(text[text.index('=')+1:].strip().removesuffix(';'))['objects']
image=NativeReference(args.research/'installs/cd_1994_09/TFX/TFX.DAT');image.cpu.mem_map(0x300000,0x20000)
image.intercept(0xc8568,'Resolve the controlled SSD handle; the native definition lookup, box walk, midpoint and orientation-zero transform execute.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000),im.return_from()))
image.write(0x1b250,'<I',0x300000);image.cpu.mem_write(0x310000,bytes(32))
rows=[];expected=[]
for obj in objects.values():
    raw=(args.research/'extracted/cd_1994_09/resources'/obj['path']).read_bytes();image.cpu.mem_write(0x300000,raw)
    centres=[]
    for index in range(4096):
        value=image.call(0xb7b90,eax=0,edx=0x311000,ebx=index)
        if not value&255:break
        centres.extend(struct.unpack('<3h',image.cpu.mem_read(0x311000,6)))
    else:raise AssertionError('unbounded SSD target enumeration')
    rows.append(f"{int(obj['id'],16)} 0\n");expected.append([len(centres)//3,*centres])
result=subprocess.run([str(args.build/'instance_probe'),str(args.research/'installs/cd_1994_09/TFX')],input=''.join(rows),capture_output=True,text=True,check=True)
actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()]
assert len(actual)==len(expected)
for row,a,b in zip(rows,actual,expected):assert a==b,(row,a,b)
print(len(expected),'original SSD damage-centre enumerations agree;',sum(v[0] for v in expected),'targetable boxes')
