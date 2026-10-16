#!/usr/bin/env python3
"""Compare view matrix and orbit position with the original camera setters."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from unicorn import x86_const as r

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
    im.call(0xb9b7a,stack=(0,0,0,pitch,yaw,distance&0xffffffff))
    position=list(struct.unpack('<3i',im.cpu.mem_read(im.native(0x70aa4+0x47722),12)))
    expected.append(matrix+position)
actual=subprocess.check_output([str((args.build/'tfx_probe').resolve()),'orbit'],input=''.join(' '.join(map(str,case))+'\n' for case in cases).encode()).splitlines()
assert len(actual)==len(expected)
for case,got,want in zip(cases,actual,expected):assert list(map(int,got.split()))==want,(case,got,want)
print(f'Native view matrix and Q16 orbit position agree exactly in {len(cases)} camera states')

# Execute the original model projection loop on supplied signed-Q16 camera vertices.
# This distinguishes the original 256-pixel polygon focal length from the separately
# encoded circle radius scale, and verifies its signed shifts and IDIV truncation.
im.cpu.mem_map(0x300000,4096)
im.call(0xb94da,stack=(105,75,200,180))
for file in (0xb9447,0xb944d,0xb9452):im.cpu.mem_write(im.native(file),bytes(4))
points=[];expected=[]
for _ in range(4096):
    point=[rng.randrange(-1000*65536,1000*65536),rng.randrange(-1000*65536,1000*65536),rng.randrange(17*65536,3000*65536)]
    im.cpu.mem_write(0x300000,bytes(20)+struct.pack('<3i',*point))
    im.cpu.reg_write(r.UC_X86_REG_EDI,0x300000)
    im.call(0xb9434,ecx=1)
    points.append(point);expected.append(list(struct.unpack('<2h',im.cpu.mem_read(0x30000e,4))))
actual=subprocess.check_output([str((args.build/'tfx_probe').resolve()),'model_projection'],input=''.join(' '.join(map(str,point))+'\n' for point in points).encode()).splitlines()
assert len(actual)==len(expected)
for point,got,want in zip(points,actual,expected):assert list(map(int,got.split()))==want,(point,got,want)
print(f'Native model projection agrees exactly for {len(points)} fractional signed-Q16 camera vertices')

# Execute native opcode 98 with the independently verified camera matrix supplied
# as the combined matrix (an identity actor rotation). Its products are Q15;
# the following projection loop adds Q16 actor/camera translations.
vertices=[];expected=[]
for _ in range(4096):
    angles=[rng.randrange(65536) for _ in range(3)]
    vertex=[rng.randrange(-10000,10001) for _ in range(3)]
    im.call(0xb9566,stack=tuple(reversed(angles)))
    matrix=bytes(im.cpu.mem_read(im.native(0x70aa4+0x47c4a),18))
    im.cpu.mem_write(im.native(0x70aa4+0x47c6e),matrix)
    im.cpu.mem_write(0x300100,struct.pack('<H3h',0,*vertex))
    im.cpu.reg_write(r.UC_X86_REG_ESI,0x300100)
    im.cpu.emu_start(im.native(0xbcb64),im.native(0xbcbeb),count=1000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0xbcbeb)
    expected.append(list(struct.unpack('<3i',im.cpu.mem_read(im.native(0x70aa4+0x6814c+20),12))))
    vertices.append(angles+vertex)
actual=subprocess.check_output([str((args.build/'tfx_probe').resolve()),'model_vertex'],input=''.join(' '.join(map(str,vertex))+'\n' for vertex in vertices).encode()).splitlines()
assert len(actual)==len(expected)
for vertex,got,want in zip(vertices,actual,expected):assert list(map(int,got.split()))==want,(vertex,got,want)
print(f'Native model vertex products agree exactly in {len(vertices)} camera/vertex states')
