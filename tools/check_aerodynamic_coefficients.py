#!/usr/bin/env python3
"""Compare complete native Mach-dependent aerodynamic derivatives (0x99bc0).

Original startup and complete coefficient code execute, with bounded FSIN/FCOS
supplied as actual host instructions. Aircraft coefficients and Mach are inputs.
"""
import argparse
from pathlib import Path
import math
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backend=hardware_sine_cosine(im,a.build);rng=random.Random(0x99bc0)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
fields=[0x146a0,0x14630,0x14640,0x14608,0x147a0,0x8d00,0x141a8,0x141a0,0x14190,0x14198,0x14178,0x14180,0x14168,0x140b0]
cases=[]
for index in range(8192):
    critical=rng.choice([.95,rng.uniform(.8,1)]);full=rng.choice([1.1,rng.uniform(1.05,1.3)])
    mach=rng.choice([0,critical,math.nextafter(critical,0),math.nextafter(critical,2),full,math.nextafter(full,0),math.nextafter(full,2),1,1.4,2.1,3,rng.uniform(0,4)])
    params=[rng.uniform(.005,.05),critical,full,rng.uniform(.01,.06),rng.choice([50,78,105.9]),rng.choice([0,2.4,12.72]),rng.uniform(-2,0),rng.uniform(-1,1),rng.uniform(-2,2),rng.uniform(-1,0),rng.uniform(-2,2),rng.uniform(-.1,.1),rng.uniform(-1,0),rng.uniform(.05,.2)]
    cases.append([1+index%3,bits(mach),*map(bits,params)])
output=subprocess.check_output([str((a.build/'aerodynamic_coefficients_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    im.write(0x11b2a,'<H',row[0]-1);im.write(0x14778,'<Q',row[1])
    for offset,value in zip(fields,row[2:]):im.write(offset,'<Q',value)
    im.call(0x99bc0)
    expected=[im.read(offset,'<Q')[0] for offset in (0x14680,0x14688,0x14160,0x14420,0x14270,0x14158,0x141c0,0x141d0,0x14268,0x14188,0x14780)]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Aerodynamic coefficients agree in {len(cases)} complete original transonic drag, aircraft lift curves and pitch/roll/control derivative cases; explicit hardware FSIN/FCOS')
