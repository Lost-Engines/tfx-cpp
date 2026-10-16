#!/usr/bin/env python3
"""Compare complete native 0x9ce5c military ground updates.

Startup, projection, spring/damper, friction/brakes, failures, random bumps and
native square roots execute without interception. Only failed-gear output
delivery is intercepted, with its request count observed.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x9ce5c)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
events=[]
def impact(image):
    events.append(1);image.return_from()
im.intercept(0x953b8,'failed-gear impact output notification; request is observed',impact)
vectors=[0x13ee8,0x13ea0,0x145f0,0x145b0,0x144d8,0x14660,0x14648]
scalars=[0x13d50,0x14578,0x14678,0x13ec0,0x14580,0x146a8,0x14590,0x14598,0x14518,0x8e18]
params=[0x14570,0x14278,0x14568,0x14560,0x14558,0x13d38,0x13d30,0x13e50,0x13e88,0x13e80,0x14220,0x145e0,0x13da0]
ground_vectors=[0x13dc0,0x14470,None,0x14490,0x144c0,0x144a8]
ground_scalars=[0x144f8,0x143c8,0x144f0,0x13e28]
offset_fields=[0x13ed0,0x145d8,0x13df8,0x13d60,0x13d78,0x13e10]
cases=[]
for i in range(8192):
    kind=i%3;terrain=(i//3)%2;wet=(i//6)%2;rough=(i//12)%2
    height=rng.choice([-20,0,8,100]);downward=rng.choice([1999,2000,2001,32767])
    # Exact level and tilted frames, plus edge-on horizontal projection gates.
    basis=rng.choice([[1,0,0,0,1,0,0,0,1],[.8,0,.6,0,1,0,-.6,0,.8],[1,0,0,0,0,1,0,-1,0],[0,0,1,0,1,0,-1,0,0],[.36,.48,.8,-.8,.6,0,-.48,-.64,.6]])
    offset=[rng.choice([-5,0,3]),rng.choice([-2,0,2]),rng.choice([-.5,.5,2])]
    state=offset+[rng.uniform(-1e4,1e4) for _ in range(18)]+[rng.uniform(-100,100) for _ in range(10)]
    par=[rng.uniform(10000,1e6),rng.uniform(1000,1e5),rng.choice([2,4,8]),60,110,90,140,rng.choice([.6,.7,.8]),.025,.8,rng.choice([9750,13381,16500]),-2,rng.uniform(0,5)]
    position=[0,0,height*8*.3048+rng.choice([-100,-2,0,2,10])]
    bodyvel=[rng.choice([-160,-10,0,5,9.99,10,30,40,60,100,160]),rng.uniform(-10,10),rng.choice([-20,0,2,5,10,11,20])]
    velocity=[rng.choice([0,5,10,30,100,150]),rng.choice([0,10]),rng.choice([0,5])]
    rates=[rng.choice([0,rng.uniform(-2,2)]),rng.choice([0,rng.uniform(-2,2)])]
    cases.append([kind,terrain,(i//24)%2,(i//48)%2,wet,rough,(i//96)%2,rng.choice([2,11,14]),rng.choice([2,11,14]),rng.randrange(65536),rng.randrange(65536),height,downward,rng.choice([0,0,0,1]),*map(bits,state+par+position+bodyvel+velocity+rates+[rng.uniform(14000,40000)]+basis)])
for i,row in enumerate(cases):
    ground_values=[rng.uniform(-10,10) for _ in range(18)]+[rng.choice([0,10,199,200,201,599,600,601]),rng.uniform(0,200),rng.uniform(0,100),rng.uniform(-10,10)]
    offsets=[6,0,2,-1,-2,2,-1,2,2,0,-6,0,0,6,0,10,0,0]
    hook=[-5,0,1];ground_context=[160,80000,30000,rng.choice([0,.5,1]),rng.uniform(0,200),rng.choice([.02,.04,.1]),rng.choice([0,1]),rng.choice([0,1])]
    row += [*map(bits,ground_values),rng.randrange(3),(i//192)%2,(i//384)%2,rng.randrange(3),*map(bits,offsets+hook+ground_context+[rng.uniform(-1e5,1e5) for _ in range(3)]),struct.unpack('<I',struct.pack('<f',rng.choice([0,.5,.6,.60001,1])))[0],(i//768)%2,(i//1536)%2,(i//3072)%2]
output=subprocess.check_output([str((a.build/'aerodynamic_ground_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases),(len(output),len(cases))
fixtures=[];impacts=contacts=bumps=arrests=shakes=0
for index,(row,line) in enumerate(zip(cases,output)):
    kind,terrain,damage,low_ground,wet,rough,braking,gear,brakes,lo,hi,height,downward,collision=row[:14]
    state=row[14:45];par=row[45:58];position=row[58:61];bodyvel=row[61:64];velocity=row[64:67];rates=row[67:69];mass=row[69];basis=row[70:79]
    im.write(0x14950,'<H',kind);im.write(0xabea,'<B',terrain);im.write(0x8e23,'<B',damage);im.write(0x8d38,'<H',low_ground);im.write(0x8f31,'<B',wet);im.write(0xe75e,'<H',2 if rough else 0);im.write(0x146b0,'<d',float(braking))
    im.write(0x7d7a,'<B',gear);im.write(0x7d74,'<B',brakes);im.write(0xabf2,'<h',height);im.write(0x1494e,'<h',downward);im.write(0x12c04,'<h',collision)
    at=0
    for offset in vectors:im.write(offset,'<3Q',*state[at:at+3]);at+=3
    for offset,value in zip(scalars,state[21:]):im.write(offset,'<Q',value)
    for offset,value in zip(params,par):im.write(offset,'<Q',value)
    im.write(0x14758,'<3Q',*position);im.write(0x147a8,'<3Q',*bodyvel);im.write(0x14820,'<3Q',*velocity);im.write(0x14508,'<2Q',*rates);im.write(0x14320,'<Q',mass)
    for column,offsets in zip((basis[:3],basis[3:6],basis[6:]),((0x148c0,0x148d8,0x14860),(0x148c8,0x148e0,0x14868),(0x148d0,0x148e8,0x14870))):
        for offset,value in zip(offsets,column):im.write(offset,'<Q',value)
    extra=row[79:101];phase,steering,landed,last_kind=row[101:105];offsets=row[105:123];hook=row[123:126];speed_limit,stiffness,damping,gear_fraction,speed,dt,engine_left,engine_right=row[126:134];previous_force=row[134:137];throttle,advanced,carrier,hook_down=row[137:]
    at=0
    for field in ground_vectors:
        if field is None:
            for offset,value in zip((0x13da8,0x13ce8,0x13cf0),extra[at:at+3]):im.write(offset,'<Q',value)
        else:im.write(field,'<3Q',*extra[at:at+3])
        at+=3
    for field,value in zip(ground_scalars,extra[18:]):im.write(field,'<Q',value)
    for field,value in zip((0x8d14,0x8d10,0x8d3a,0x14950),(phase,steering,landed,last_kind)):im.write(field,'<H',value)
    for at,field in enumerate(offset_fields):im.write(field,'<3Q',*offsets[at*3:at*3+3])
    im.write(0x13dd8,'<3Q',*hook)
    for field,value in zip((0x14550,0x13d40,0x13d98,0x146d8,0x14700,0x142c0,0x14880,0x14888),(speed_limit,stiffness,damping,gear_fraction,speed,dt,engine_left,engine_right)):im.write(field,'<Q',value)
    im.write(0x146e0,'<3Q',*previous_force);im.write(0x133f8,'<I',throttle);im.write(0x1347a,'<B',advanced);im.write(0xe75e,'<H',3 if carrier else 2 if rough else 0);im.write(0x8d12,'<H',hook_down);im.write(0xe70c,'<I',im.native(0x70b44))
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',lo,hi));events.clear();im.call(0x9ce5c)
    expected=[v for offset in vectors for v in im.read(offset,'<3Q')]+[im.read(offset,'<Q')[0] for offset in scalars]
    for field in ground_vectors:
        expected += [im.read(offset,'<Q')[0] for offset in (0x13da8,0x13ce8,0x13cf0)] if field is None else list(im.read(field,'<3Q'))
    expected += [im.read(field,'<Q')[0] for field in ground_scalars]
    expected += [im.read(0x7d7a,'<B')[0],im.read(0x7d74,'<B')[0],im.read(0x12c04,'<H')[0],*struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4)),len(events),int(im.read(0xe70c,'<I')[0]==im.native(0x7d9d4)),im.read(0x8d14,'<H')[0],im.read(0x8d10,'<H')[0],im.read(0x8d3a,'<H')[0],im.read(0x14950,'<H')[0]]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    impacts+=len(events);contacts+=expected[21]!=state[21];bumps+=expected[56]!=lo;arrests+=expected[60]!=phase;shakes+=expected[59]
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert impacts>10 and contacts>500 and bumps>100 and arrests>100 and shakes>10
print(f'{len(cases)} complete original military ground cases agree: {contacts} contact passes, {bumps} random bump sequences, {impacts} gear notifications, {arrests} arrestor transitions and {shakes} cockpit bumps')
