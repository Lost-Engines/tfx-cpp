#!/usr/bin/env python3
"""Compare native lift, drag, stall and pitch/roll surface-force stages.

Original 0x9c7f0, or its simplified lift/drag/projection sequence, executes with
original startup. Only bounded FSIN/FCOS use host instructions in place of
Unicorn's narrowed arithmetic. All coefficients, geometry and controls are inputs.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backend=hardware_sine_cosine(im,a.build);rng=random.Random(0x9c7f0)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
state_fields=[0x14720,0x14238,0x14400,0x14448,0x13fd0,0x14000,0x143c0,0x14428,0x146f8,0x14408,0x14130,0x13fd8,0x14468,0x13e58]
coefficient_fields=[0x14680,0x14688,0x14160,0x14420,0x14270,0x14158,0x141c0,0x141d0,0x14268,0x14188,0x14780]
parameter_fields=[0x147a0,0x14218,0x14200,0x141e0,0x14088,0x14148,0x14228,0x14140,0x14080,0x14248,0x13fc8,0x14150,0x14430,0x14068,0x141b0,0x140d0,0x141b8,0x140e0,0x140f8,0x14108,0x14098]
context_fields=[0x14418,0x14700,0x14438,0x143d8,0x14728,0x146d8,0x145a8,0x148a0,0x14788,0x14410,0x14510,0x14508]
cases=[]
for index in range(8192):
    state=[rng.uniform(-10,10) for _ in range(20)]
    coeff=[.01,.02,rng.uniform(.005,.1),rng.uniform(1,5),rng.uniform(-5,-.1),rng.uniform(-5,-.1),rng.uniform(-5,1),rng.uniform(0,.3),rng.uniform(-2,-.1),0,rng.uniform(.1,.5)]
    params=[rng.choice([50,78,105.9]),rng.choice([10.5,13.2,13.56]),rng.choice([5.697,6.4]),rng.uniform(.4,1),rng.uniform(.5,1.05),rng.uniform(.2,1),rng.uniform(.8,1.5),rng.uniform(1,3.5),rng.uniform(.2,.5),rng.uniform(.01,.03),rng.choice([.4363319444444444,.7243110277777777,.39269874999999993]),rng.uniform(.1,.2),rng.choice([0,.024]),rng.uniform(0,.001),rng.uniform(0,.2),78.53975,rng.uniform(-.04,-.02),rng.uniform(-5,0),rng.uniform(0,2),rng.uniform(-1,0),rng.uniform(.1,.25)]
    context=[rng.choice([-.5,0,.1,.5,1,rng.uniform(-1,1)]),rng.uniform(0,1000),rng.choice([.088,1.225]),rng.uniform(0,500000),rng.uniform(0,1),rng.choice([0,1]),rng.choice([0,1]),rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.2,.2),rng.uniform(-3,3),rng.uniform(-3,3)]
    cases.append([1+index%3,index%2,(index//2)%2,rng.choice([2,11,14]),*map(bits,state+coeff+params+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_surfaces_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];stalls=0
for index,(row,line) in enumerate(zip(cases,output)):
    craft,chute,moments,condition=row[:4];state=row[4:24];coeff=row[24:35];params=row[35:56];context=row[56:]
    im.write(0x11b2a,'<H',craft-1);im.write(0x14964,'<H',chute);im.write(0x7d71,'<B',condition)
    for offset,value in zip(state_fields,state[:14]):im.write(offset,'<Q',value)
    im.write(0x14528,'<3Q',*state[14:17]);im.write(0x14808,'<3Q',*state[17:20])
    for offset,value in zip(coefficient_fields,coeff):im.write(offset,'<Q',value)
    for offset,value in zip(parameter_fields,params):im.write(offset,'<Q',value)
    for offset,value in zip(context_fields,context):im.write(offset,'<Q',value)
    if moments:im.call(0x9c7f0)
    else:
        for routine in (0x9c810,0x9c9dc,0x9cbd0):im.call(routine)
    expected=[im.read(offset,'<Q')[0] for offset in state_fields]+list(im.read(0x14528,'<3Q'))+list(im.read(0x14808,'<3Q'))+[int(im.read(0x13474,'<H')[0]!=0)]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    stalls+=expected[-1]
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert stalls>100
print(f'Aerodynamic surfaces agree in {len(cases)} complete original lift/drag/moment/projection updates, including {stalls} stalls; explicit hardware FSIN/FCOS')
