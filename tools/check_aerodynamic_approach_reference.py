#!/usr/bin/env python3
"""Compare complete native ILS aerodynamic reference calculations (0x99a30).

Original startup and the complete reference routine execute. Only the explicit
hardware FCOS/FPATAN adapters intercept numerical helpers; no flight law or
reference calculations are substituted. This is not the automatic-landing law.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_fpatan,hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build));rng=random.Random(0x99a30)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
state_fields=[0x14280,0x142b0,0x14290,0x142a8,0x143c8];context_fields=[0x14820,0x14828,0x14830,0x14438,0x14320,0x14548,0x147a0,0x141e0,0x14088,0x14248,0x14420];cases=[]
for i in range(8192):
 velocity=[rng.uniform(-300,300),rng.uniform(-300,300),rng.uniform(-50,50)]
 if i%4==0:velocity=[0,0,rng.choice([0,.999999,1,1.000001,50])]
 values=[rng.uniform(-10,10) for _ in state_fields]+velocity+[rng.choice([.088,.4,1.225]),rng.uniform(9000,26000),rng.choice([0,50,100,200]),rng.choice([50,78,105.9]),rng.uniform(.1,1),rng.uniform(.1,1.5),rng.uniform(-.1,.1),rng.uniform(1,5)]
 cases.append([1+i%3,rng.choice([1,2,11,14]),*map(bits,values)])
output=subprocess.check_output([str((a.build/'aerodynamic_approach_reference_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];retained=0
for i,(row,line) in enumerate(zip(cases,output)):
 craft,condition=row[:2];im.write(0x11b2a,'<H',craft-1);im.write(0x7d71,'<B',condition)
 for field,value in zip(state_fields+context_fields,row[2:]):im.write(field,'<Q',value)
 im.call(0x99a30)
 expected=[im.read(field,'<Q')[0] for field in state_fields];actual=list(map(int,line.split()))
 assert actual==expected,(i,row,[(j,x,y) for j,(x,y) in enumerate(zip(actual,expected)) if x!=y])
 retained+=expected[3]==row[5]
 if i%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert retained>1000
print(f'{len(cases)} original ILS aerodynamic reference updates agree, including {retained} retained flight-path cases; only hardware transcendental adapters')
