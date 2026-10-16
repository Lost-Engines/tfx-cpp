#!/usr/bin/env python3
"""Compare original word and Q16 world-point projection, including native clipping.

The actual original matrix/translation setters and both point projectors execute.
Synthetic poses and points are supplied, without world rendering or resource I/O.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from unicorn import x86_const as r

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--save-fixture',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
rng=random.Random(0xc5759);identity=[32767,0,0,0,32767,0,0,0,32767];cases=[];expected=[]
for mode in range(2):
    for index in range(8192):
        matrix=identity if index<128 else [rng.randrange(-32768,32768) for _ in range(9)]
        camera=[0,0,0] if index<128 else [rng.randrange(-2147483648,2147483648) for _ in range(3)]
        point=[[-1,0,1,100,-100][index%5],[-1,0,1,-100,100][index%5],[31,32,33,34,100,20000,32767,32768,40000][index%9]] if index<128 else [rng.randrange(-2147483648,2147483648) for _ in range(3)]
        if mode and index<128:point=[n*65536 if -32768<=n<=32767 else (n-65536)*65536 for n in point]
        origin=[159,56] if index<128 else [rng.randrange(-32768,32768) for _ in range(2)]
        row=[mode,*matrix,*camera,*point,*origin];cases.append(row)
        matrix_address=im.native(0x70aa4+0x47c4a);im.cpu.mem_write(matrix_address,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_address);im.call(0xb959f)
        im.call(0xb9ab9,stack=tuple(n&0xffffffff for n in reversed(camera)));im.call(0xb94da,stack=tuple(n&0xffffffff for n in [*origin,319,199]))
        valid=bool(im.call(0xc57d1 if mode else 0xc5759,stack=(*[n&0xffffffff for n in reversed(point)],0x300000)))
        x,y=struct.unpack('<2h',im.cpu.mem_read(0x300000,4));expected.append([int(valid),x,y])
output=subprocess.check_output([str((a.build/'point_projection_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for row,line,want in zip(cases,output,expected):assert list(map(int,line.split()))==want,(row,line,want)
if a.save_fixture:
    selected=list(range(64))+list(range(8192,8256))+[n for n in range(128,len(cases),173) if expected[n][0]]
    a.save_fixture.write_text(''.join(' '.join(map(str,[*cases[n],*expected[n]]))+'\n' for n in selected))
print(f'Original word/Q16 world-point clipping, reciprocal projection and wrapping agree in {len(cases)} native cases')
