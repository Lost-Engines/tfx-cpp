#!/usr/bin/env python3
"""Compare complete original velocity/rate response (0x9f41c).

Original startup precision and complete response code execute. Only FPATAN,
FSIN and FCOS use host instructions instead of Unicorn's binary64 fallback.
Basis, aerodynamic derivatives, controls, loads and prior state are stage inputs.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build));rng=random.Random(0x9f41c)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
vectors=[0x14820,0x147f0,0x147a8,0x14708,0x14508]
parameters=[0x147a0,0x14218,0x14200,0x14098,0x140c8,0x14268,0x14158,0x14270,0x141b8,0x14120,0x14118,0x8cd0]
contexts=[0x142c0,0x14700,0x14438,0x14540,0x14730,0x14788,0x148a0,0x14780,0x141c0,0x14878,0x8cf8,0x14418,0x14338,0x14670]
for index in range(8192):
    flags=[(index>>bit)&1 for bit in range(6)]
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    axes=struct.unpack('<9h',im.cpu.mem_read(0x300000,18));basis=[axes[row*3+col]*3.051850947599719e-05 for col in range(3) for row in range(3)]
    vectors_in=[[rng.uniform(-1000,1000) for _ in range(3)],[rng.uniform(-100,100) for _ in range(3)],[rng.uniform(-100,100) for _ in range(3)],[rng.uniform(-100,100) for _ in range(3)],[rng.uniform(-5,5) for _ in range(3)]]
    vectors_in[2][0]=rng.choice([29.999,30,30.001,rng.uniform(-100,100)])
    vectors_in[3][0]=rng.choice([-1.001,-1,-.999,-0.0,0.0,.999,1,1.001,rng.uniform(-100,100)])
    state=[v for vector in vectors_in for v in vector]+[rng.uniform(-10,10) for _ in range(2)]+[rng.uniform(-.5,.5) for _ in range(3)]+[rng.choice([-20000,-20000.0000001,-19999.9999999,-1000,0])]
    inertia=[rng.uniform(3000,40000),rng.uniform(10000,200000),rng.uniform(10000,300000),rng.uniform(0,10000)]
    params=[rng.choice([50,78,105.9]),rng.choice([10.5,13.2,13.56]),rng.choice([5.697,6.4]),rng.uniform(.1,.3),.3,rng.choice([-.5,-50,-500]),rng.choice([-5,-50,-500]),rng.uniform(-5,-.1),rng.uniform(-.05,.05),rng.uniform(-1,1),rng.uniform(-6,0),rng.choice([-.8726638888888888,.10471966666666664])]
    context=[rng.choice([.02,.04,.1,1,5]),rng.choice([0,9.999,10,10.001,64.375,100,1000]),rng.choice([.088,1.225]),rng.choice([64.375,92.7,67.98]),rng.choice([0,rng.uniform(-1,1)]),rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-2,2),rng.uniform(-2,2),rng.uniform(0,1),rng.uniform(-100000,100000),rng.uniform(-.5,.5),rng.uniform(-.5,.5),rng.choice([0,rng.uniform(-10000,10000)])]
    cases.append([*flags,*map(bits,state),float_bits(rng.uniform(-3,9)),*map(bits,basis+inertia+params+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_response_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];roll_fallback=pitch_fallback=0
for index,(row,line) in enumerate(zip(cases,output)):
    warp,landed,auto,inhibited,realistic,pressure=row[:6];values=row[6:27];g=row[27];basis=row[28:37];inertia=row[37:41];params=row[41:53];context=row[53:]
    im.write(0xe780,'<B',warp);im.write(0x8d3a,'<H',landed);im.write(0x14958,'<H',auto);im.write(0x8d10,'<H',inhibited);im.write(0x1347a,'<B',6 if realistic else 1);im.write(0x8f32,'<B',pressure)
    at=0
    for offset in vectors:im.write(offset,'<3Q',*values[at:at+3]);at+=3
    im.write(0x13fe0,'<2Q',*values[15:17])
    for offset,value in zip((0x14410,0x143d0,0x143c8,0x14768),values[17:]):im.write(offset,'<Q',value)
    im.write(0x133f4,'<I',g)
    for offset,value in zip((0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870),basis):im.write(offset,'<Q',value)
    for offset,value in zip((0x14320,0x142d0,0x142d8,0x14858),inertia):im.write(offset,'<Q',value)
    for offset,value in zip(parameters,params):im.write(offset,'<Q',value)
    for offset,value in zip(contexts,context):im.write(offset,'<Q',value)
    im.call(0x9f41c)
    expected=[v for offset in vectors for v in im.read(offset,'<3Q')]+list(im.read(0x13fe0,'<2Q'))+[im.read(offset,'<Q')[0] for offset in (0x14410,0x143d0,0x143c8)]+[im.read(0x133f4,'<I')[0],int(im.read(0x8d38,'<H')[0]!=0)]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    roll_fallback+=im.read(0x13fe0,'<d')[0]==0;pitch_fallback+=im.read(0x13fe8,'<d')[0]==0
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert roll_fallback>100 and pitch_fallback>100
print(f'Aerodynamic response agrees in {len(cases)} complete original updates; {roll_fallback} roll and {pitch_fallback} pitch damping fallbacks; explicit hardware FPATAN/FSIN/FCOS')
