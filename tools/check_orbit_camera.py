#!/usr/bin/env python3
"""Compare view matrix and orbit position with the original camera setters."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();im=NativeReference(args.data_dir/'TFX.DAT');rng=random.Random(0xb9566)
cases=[(x,y,z,distance) for x,y,z in [(0,0,0),(0x14f0,0x7130,0),(0x2fff,0x7fff,0),(0x6000,0,0),(0xffff,0xffff,0xffff)] for distance in (880,1200,8000,-32768,32767)]
cases += [(*[rng.randrange(65536) for _ in range(3)],rng.randrange(-32768,32768)) for _ in range(4096)]
expected=[]
for pitch,yaw,roll,distance in cases:
    im.call(0xb9566,stack=(roll,yaw,pitch))
    matrix=list(struct.unpack('<9h',im.cpu.mem_read(im.native(0x70aa4+0x47c4a),18)))
    matrix=[matrix[i] for i in (0,3,6,1,4,7,2,5,8)]
    im.call(0xb9b7a,stack=(0,0,0,pitch,yaw,distance&0xffffffff))
    position=list(struct.unpack('<3i',im.cpu.mem_read(im.native(0x70aa4+0x47722),12)))
    expected.append(matrix+position)
actual=subprocess.check_output([str((args.build/'tfx_probe').resolve()),'orbit'],input=''.join(' '.join(map(str,case))+'\n' for case in cases).encode()).splitlines()
assert len(actual)==len(expected)
for case,got,want in zip(cases,actual,expected):assert list(map(int,got.split()))==want,(case,got,want)
print(f'Native view matrix and Q16 orbit position agree exactly in {len(cases)} camera states')
