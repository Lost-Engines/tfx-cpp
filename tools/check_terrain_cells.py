#!/usr/bin/env python3
"""Compare complete original terrain-cell traversal, order and wrap seams.

Runs B0BA8 with supplied column-major low/high handle grids. Grid binding and
SSD delivery are declared boundaries; the original loop, dimensions, signed
remainders, source reads and narrow world-centre formation execute unchanged.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000,0x20000)
im.cpu.mem_write(0x300000,bytes(index>>8 for index in range(40000)))
im.cpu.mem_write(0x30a000,bytes(index&255 for index in range(40000)))
im.write(0x18f40,'<I',0x300000);im.write(0x18f50,'<I',0x30a000)
im.intercept(0xb098c,'Supply the already bound diagnostic grid; its handle layout is an explicit input.',lambda current:current.return_from())
submissions=[]
def deliver(current):
    submissions.append([current.cpu.reg_read(reg)&0xffffffff for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)])
    current.return_from()
im.intercept(0xb4fd0,'Observe the native SSD handle and signed-word world centre before its separate renderer.',deliver)
rng=random.Random(0xb0ba8)
edges=(-2147483648,-409601,-409600,-409599,-2049,-2048,-2047,-1,0,1,2047,2048,409599,409600,409601,2147483647)
rows=[]
for index in range(512):
    x=edges[index%len(edges)] if index<256 else rng.randrange(-2147483648,2147483648)
    z=edges[index//len(edges)] if index<256 else rng.randrange(-2147483648,2147483648)
    rows.append([x,z,(-2,0,1,2,3,7,8,16,20,40)[index%10],rng.randrange(-100000,100000)])
actual=subprocess.check_output([str((a.build/'terrain_cells_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).splitlines()
assert len(actual)==len(rows)
fixtures=[];total=0
for index,(row,line) in enumerate(zip(rows,actual)):
    x,z,width,height=row
    im.write(0xaac4,'<h',width);submissions.clear()
    im.call(0xb0ba8,eax=0,edx=x&0xffffffff,ecx=z&0xffffffff,stack=(height&0xffffffff,),limit=1000000)
    digest=14695981039346656037
    for call in submissions:
        for byte in struct.pack('<4I',*call):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
    expected=[len(submissions),digest]
    assert list(map(int,line.split()))==expected,(index,row,line,expected,submissions[:5])
    total+=len(submissions)
    if index<128 or index%17==0:fixtures.append(row+expected)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete native terrain traversals / {total} SSD submissions agree: Z-major order, half-open extents, signed world cells, original seam wrapping and narrow centres')
