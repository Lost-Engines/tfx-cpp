#!/usr/bin/env python3
"""Compare complete original force/moment summation and acceleration stages.

Native 0x9f128 and 0x9f3b0, including the refuelling asin helper, execute; FPATAN is
provided by actual host x87 rather than Unicorn's binary64 approximation.
Local force/moment producers, normalized physical axes, aircraft inertia,
fuel and prior velocities are supplied at their stage boundaries.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_fpatan

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);backend=hardware_fpatan(im,a.build);rng=random.Random(0x9f128)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
fields=[0x14528,0x147d8,0x14660,0x14808,0x147c0,0x14648,0x14820,0x147a8,0x14708]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    axes=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    axes=[axes[row*3+col]*3.051850947599719e-05 for col in range(3) for row in range(3)]
    forces=[rng.uniform(-2e6,2e6) for _ in range(18)]
    velocities=[rng.uniform(-1000,1000) for _ in range(9)]
    params=[rng.uniform(3000,40000),rng.uniform(10000,200000),rng.uniform(10000,300000),rng.uniform(0,10000),rng.choice([-.85344,rng.uniform(-4,4)]),rng.uniform(-2,2)]
    cases.append([index%2,(index//2)%2,*map(bits,axes+forces+velocities+params)])
output=subprocess.check_output([str((a.build/'aerodynamic_forces_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    connected,arrested=row[:2];values=row[2:]
    for offset,value in zip((0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870),values[:9]):im.write(offset,'<Q',value)
    at=9
    for offset in fields:im.write(offset,'<3Q',*values[at:at+3]);at+=3
    for offset,value in zip((0x14320,0x142d0,0x142d8,0x14858,0x8d20,0x14508),values[at:]):im.write(offset,'<Q',value)
    im.write(0x13b04,'<B',3 if connected else 0);im.write(0x8d14,'<H',2 if arrested else 0)
    im.call(0x9f128);im.call(0x9f3b0)
    expected=[v for offset in (0x14610,0x146e0,0x14738,0x14820,0x147a8,0x14708,0x147f0) for v in im.read(offset,'<3Q')]
    expected += list(im.read(0x13fe0,'<2Q'))+[im.read(0x133f4,'<I')[0]]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Aerodynamic forces agree in {len(cases)} complete original body/NED load, inertia, acceleration, G and arrested-velocity cases with explicit hardware FPATAN')
