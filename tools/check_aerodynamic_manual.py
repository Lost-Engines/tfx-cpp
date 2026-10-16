#!/usr/bin/env python3
"""Compare the complete ordinary/manual 0x9ac9c flight-control path.

Autopilot enable is zero; the original dispatch and complete manual path run.
Startup, overspeed/reheat handlers and math execute. FPATAN, FSIN/FCOS and
bounded FPTAN use host instructions; only sound/model outputs are intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x9bce9);events=[]
im.intercept(0xa4edc,'Capture original overspeed/reheat sound requests',lambda image:(events.append(('sound',image.cpu.reg_read(r.UC_X86_REG_EAX))),image.return_from()))
im.intercept(0xb52d4,'Capture player afterburner model entry; SSD delivery is separate',lambda image:(events.append(('model',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
state_fields=[0x148a0,0x14788,0x14730,0x14898,0x140b8,0x148f0,0x142e8,0x14368,0x142e0,0x14848,0x14338,0x14728,0x143f8,0x14440,0x8cf8,0x145a8]
power_fields=[0x14880,0x14888,0x14838,0x14840,0x14878,0x14890,0x14858,0x8d40]
basis_fields=[0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870]
data_fields=[0x14418,0x14700,0x14778,0x14438,0x14790,0x14320,0x13b60]
coefficient_fields=[0x14680,0x14688,0x14160,0x14420,0x14270,0x14158,0x141c0,0x141d0,0x14268,0x14188,0x14780]
geometry_fields=[0x147a0,0x14218,0x14200,0x141e0,0x14088,0x14248,0x13fc8,0x141b8,0x14098,0x14430,0x8cd0]
surface_fields=[0x14400,0x14448,0x14238]
context_fields=[0x14488,0x14500,0x8d20,0x14118,0x14620,0x14610,0x8e18]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    craft=1+index%3;source=(index//3)%3;military=(index//9)%2;pressure=(index//18)%2
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if index%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    axes=struct.unpack('<9h',im.cpu.mem_read(0x300000,18));basis=[axes[row*3+col]*3.051850947599719e-05 for col in range(3) for row in range(3)]
    state=[rng.uniform(-.8,.8),rng.uniform(-.8,.8),rng.uniform(-1,1),rng.choice([0,rng.uniform(-1,1)]),rng.uniform(-1,1),rng.uniform(-1,1),-1,1,rng.uniform(.1,1),rng.uniform(-.2,.2),rng.uniform(-.1,.1),rng.uniform(0,1),1,-1,rng.uniform(0,1),rng.choice([0,1])]
    power=[rng.choice([0,1]),rng.choice([0,1]),rng.uniform(-.35,.35),rng.uniform(-.35,.35),rng.uniform(0,150000),rng.uniform(0,1),rng.uniform(100,10000),rng.uniform(100,700)]
    mass=rng.uniform(10000,20000);speed=rng.choice([0,1,1.001,10,20,20.001,50,60,75,90,150,300,700]);data=[rng.uniform(-.4,.8),speed,rng.choice([0,.8,.9,1,2,2.1,3]),rng.choice([.088,1.225]),340,mass,rng.uniform(0,10000)]
    coefficients=[.01,.02,.03,3,-.5,-.6,.7 if craft==1 else -1.5,.1,-1,0,.3]
    geometry=[rng.choice([50,78,105.9]),rng.choice([10.5,13.2,13.56]),rng.choice([5.697,6.4]),.523,1.0471966666666666,.0117,.4363319444444444,-.0311,.2268926111111111,rng.choice([0,.024]),-.8726638888888888 if craft==1 else .10471966666666664]
    surfaces=[1.5,-1.5,.02];context=[6 if craft==2 else 9,-1 if craft==2 else -3,-.85344,-5.7 if craft==3 else 0,-rng.uniform(-5,10)*mass*9.81,rng.uniform(-50000,50000),rng.choice([0,rng.uniform(.01,1)])]
    cases.append([craft,source,military,pressure,rng.choice([2,11,14]),0 if craft==2 else rng.randrange(5),rng.randrange(15),rng.randrange(15),rng.choice([1,2]),float_bits(rng.uniform(0,1)),*map(bits,state+power+basis+data+coefficients+geometry+surfaces+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_manual_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];changes=0
for index,(row,line) in enumerate(zip(cases,output)):
    craft,source,military,pressure,flaps,old,control,display,brake=row[:9];throttle=row[9];values=row[10:]
    im.write(0x14958,'<H',0);im.write(0x11b2a,'<H',craft-1);im.write(0x13478,'<B',source);im.write(0x1347a,'<B',1 if military else 6);im.write(0x8f32,'<B',pressure);im.write(0x7d71,'<B',flaps);im.write(0x1496d,'<B',old);im.write(0x10bed,'<B',control);im.write(0x6c38,'<B',display);im.write(0x7d77,'<B',brake);im.write(0x133f8,'<I',throttle);im.write(0xe76c,'<H',23)
    at=0
    for fields in (state_fields,power_fields,basis_fields,data_fields,coefficient_fields,geometry_fields,surface_fields,context_fields):
        for offset,value in zip(fields,values[at:at+len(fields)]):im.write(offset,'<Q',value)
        at+=len(fields)
    assert at==len(values),(at,len(values))
    events.clear();im.call(0x9ac9c,limit=1000000)
    new=im.read(0x1496d,'<B')[0];change=4 if new<old and new==0 else 3 if new<old else 0
    expected_events=[('sound',8)]+([('model',23,10)] if change==4 else []) if change else []
    assert events==expected_events,(index,change,events)
    expected=[im.read(offset,'<Q')[0] for offset in state_fields+power_fields]+[im.read(0x133f8,'<I')[0]]+[im.read(offset,'<B')[0] for offset in (0x1496d,0x10bed,0x6c38,0x7d77)]+[change]
    actual=list(map(int,line.split()));assert actual==expected,(index,craft,source,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    changes+=bool(change)
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Manual aerodynamic law agrees in {len(cases)} complete original trim/G-limit/damage/flap/nozzle/overspeed cases and {changes} afterburner changes; explicit hardware transcendental and output boundaries')
