#!/usr/bin/env python3
"""Compare complete native physical initialization/model-switch routine 0x954fc.

Original startup, frame/pose/velocity conversion, both native store recalculations
and the special carrier tuning routine execute without intercepted dependencies.
The input loadout is a declared original store in one slot, with varied mounts,
prior store mass and fuel, making initialization ordering observable.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);rng=random.Random(0x954fc)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
im.call(0x968d4);carrier=[im.read(field,'<d')[0] for field in (0x14568,0x147a0,0x14430)]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for i in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if i%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18))
    craft=1+i%3;weapon=i%27;record=0x809c+weapon*48;store_mass=im.read(record+31,'<h')[0];drag=im.read(record+44,'<I')[0];tank=int(im.read(record+20,'<B')[0]==6)
    state=[rng.uniform(-2,2) for _ in range(8)]+[rng.choice([0,1]),rng.choice([0,1]),rng.uniform(0,10000),rng.uniform(0,5000)]
    geometry=[rng.choice([9750,13381,16500]),rng.uniform(-3,3),rng.uniform(-1,1),rng.uniform(10000,500000),rng.uniform(1,3),rng.choice([4000,7938,9979]),rng.uniform(50000,100000),rng.uniform(100000,200000),*carrier,rng.uniform(2,5),rng.choice([50,78,105.9]),rng.uniform(0,.1)]
    position=[rng.uniform(-10000,10000) for _ in range(3)];mount=[rng.uniform(-20,20) for _ in range(3)]
    cases.append([craft,(i//3)%2,(i//6)%2,(i//12)%2,(i//24)%2,(i//48)%2,weapon,rng.choice([-20,-11,-10,0,100]),rng.randrange(65536),rng.randrange(-100,2000),*map(fbits,position),*frame,fbits(rng.uniform(-5,10)),*map(bits,state+geometry+mount),store_mass,drag,tank])
output=subprocess.check_output([str((a.build/'aerodynamic_start_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];carrier_starts=ground_starts=0
for index,(row,line) in enumerate(zip(cases,output)):
    craft,landed,cold,terrain,steering,occupied,weapon,height,heading,speed=row[:10];position=row[10:13];frame=row[13:22];g=row[22];state=row[23:35];geometry=row[35:49];mount=row[49:52]
    for field,value,format in ((0x11b2a,craft-1,'<H'),(0x8d3a,landed,'<H'),(0x1347c,cold,'<B'),(0xabea,terrain,'<B'),(0x8d10,steering,'<H'),(0xabf2,height,'<h'),(0x86ca,heading,'<H'),(0x13444,speed,'<i'),(0x133f4,g,'<I')):im.write(field,format,value)
    for field,value in zip((0x1341c,0x13428,0x13434),position):im.write(field,'<I',value)
    im.write(0x1345e,'<9h',*frame);im.write(0x14508,'<3Q',*state[:3]);im.write(0x147f0,'<3Q',*state[3:6]);im.write(0x13fe0,'<2Q',*state[6:8]);im.write(0x14880,'<2Q',*state[8:10]);im.write(0x14858,'<Q',state[10]);im.write(0x142a0,'<Q',state[11])
    fields=[0x14220,0x8d28,0x8d30,0x14570,0x145e8,0x14850,0x142c8,0x14258]
    for field,value in zip(fields,geometry[:8]):im.write(field,'<Q',value)
    for field,value in zip((0x14568,0x147a0,0x14430),geometry[11:]):im.write(field,'<Q',value)
    im.cpu.mem_write(im.data+0x13374,bytes(20));im.write(0x13374,'<2B',weapon,occupied)
    for field,value in zip((0x13bd0,0x13c20,0x13c70),mount):im.write(field,'<Q',value)
    im.call(0x954fc,limit=2000000)
    expected=[word for field in (0x14758,0x14820,0x147f0,0x147a8,0x14508) for word in im.read(field,'<3Q')]+list(im.read(0x13fe0,'<2Q'))+list(im.read(0x14880,'<2Q'))
    expected += [im.read(field,'<Q')[0] for field in (0x14858,0x14320,0x142c0,0x142a0,0x14358,0x14350,0x13d08,0x142d0,0x142d8,0x14770,0x14568,0x147a0,0x14430)]
    expected += [im.read(0x133f4,'<I')[0],im.read(0x148f8,'<I')[0],im.read(0x8d10,'<H')[0],im.read(0x14968,'<H')[0]]+[v&0xffffffff for v in im.read(0x1493e,'<9h')]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
    ground_starts+=landed;carrier_starts+=craft==3 and landed and cold and terrain and height<-10
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert ground_starts>1000 and carrier_starts>100
print(f'{len(cases)} complete original physical initializations agree: {ground_starts} ground starts and {carrier_starts} special carrier starts, native stores and no intercepted dependencies')
