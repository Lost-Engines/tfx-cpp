#!/usr/bin/env python3
"""Compare both original float-to-fixed down-axis alignment helpers.

Native normalization, cross products, x87 storage/rounding and matrix writes
execute without intercepted dependencies. Camera and pilot consumers share
one C++ implementation; complete flight sessions are outside this comparison.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
rng=random.Random(0x8e86c);identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
changed=False
def completed(cpu,address,size,unused):
    global changed
    changed=True
for address in (0x8eb07,0x91ee3):im.cpu.hook_add(UC_HOOK_CODE,completed,begin=im.native(address),end=im.native(address))
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
for index in range(2048):
    basis=list(identity)
    if index%4:
        im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
        basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    if index%31==0:basis=[0]*9
    elif index%37==0:basis=[rng.randrange(-32768,32768) for _ in range(9)]
    directions=[(0,0,0),(0,1,0),(0,-1,0),(0,.0009,0),(0,.001,0),(0,.001001,0),tuple(basis[2::3]),tuple(rng.uniform(-3,3) for _ in range(3))]
    direction=list(map(f32,directions[index%len(directions)]))
    cases.append([*basis,*direction])
output=subprocess.check_output([str((a.build/'down_alignment_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];writes=0
for index,(row,line) in enumerate(zip(cases,output)):
    expected=[]
    for function,field in ((0x8e86c,0x1345e),(0x91c48,0x13562)):
        im.write(field,'<9h',*row[:9]);changed=False
        im.call(function,stack=struct.unpack('<3I',struct.pack('<3f',*row[9:])),limit=1000000)
        result=[int(changed),*im.read(field,'<9h')]
        if expected:assert expected==result,(index,'original copies differ',expected,result)
        expected=result
    actual=list(map(int,line.split()))
    assert actual==expected,(index,row,actual,expected)
    writes+=expected[0]
    if index%31==0 or index%37==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Down-axis alignment agrees in {len(cases)*2} complete native matrix cases across both original helpers; {writes} accepted C++ updates')
