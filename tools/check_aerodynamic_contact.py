#!/usr/bin/env python3
"""Compare complete native 0x9d734 gear/body contact evaluations.

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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x9d734)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
events=[]
def impact(image):
    events.append(1);image.return_from()
im.intercept(0x953b8,'failed-gear impact output notification; request is observed',impact)
vectors=[0x13ee8,0x13ea0,0x145f0,0x145b0,0x144d8,0x14660,0x14648]
scalars=[0x13d50,0x14578,0x14678,0x13ec0,0x14580,0x146a8,0x14590,0x14598,0x14518,0x8e18]
params=[0x14570,0x14278,0x14568,0x14560,0x14558,0x13d38,0x13d30,0x13e50,0x13e88,0x13e80,0x14220,0x145e0,0x13da0]
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
output=subprocess.check_output([str((a.build/'aerodynamic_contact_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases),(len(output),len(cases))
fixtures=[];impacts=contacts=bumps=failures=0
for index,(row,line) in enumerate(zip(cases,output)):
    kind,terrain,damage,low_ground,wet,rough,braking,gear,brakes,lo,hi,height,downward,collision=row[:14]
    state=row[14:45];par=row[45:58];position=row[58:61];bodyvel=row[61:64];velocity=row[64:67];rates=row[67:69];mass=row[69];basis=row[70:]
    im.write(0x14950,'<H',kind);im.write(0xabea,'<B',terrain);im.write(0x8e23,'<B',damage);im.write(0x8d38,'<H',low_ground);im.write(0x8f31,'<B',wet);im.write(0xe75e,'<H',2 if rough else 0);im.write(0x146b0,'<d',float(braking))
    im.write(0x7d7a,'<B',gear);im.write(0x7d74,'<B',brakes);im.write(0xabf2,'<h',height);im.write(0x1494e,'<h',downward);im.write(0x12c04,'<h',collision)
    at=0
    for offset in vectors:im.write(offset,'<3Q',*state[at:at+3]);at+=3
    for offset,value in zip(scalars,state[21:]):im.write(offset,'<Q',value)
    for offset,value in zip(params,par):im.write(offset,'<Q',value)
    im.write(0x14758,'<3Q',*position);im.write(0x147a8,'<3Q',*bodyvel);im.write(0x14820,'<3Q',*velocity);im.write(0x14508,'<2Q',*rates);im.write(0x14320,'<Q',mass)
    for column,offsets in zip((basis[:3],basis[3:6],basis[6:]),((0x148c0,0x148d8,0x14860),(0x148c8,0x148e0,0x14868),(0x148d0,0x148e8,0x14870))):
        for offset,value in zip(offsets,column):im.write(offset,'<Q',value)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',lo,hi));events.clear();im.call(0x9d734)
    expected=[v for offset in vectors for v in im.read(offset,'<3Q')]+[im.read(offset,'<Q')[0] for offset in scalars]
    expected += [im.read(0x13e28,'<Q')[0],im.read(0x7d7a,'<B')[0],im.read(0x7d74,'<B')[0],im.read(0x12c04,'<H')[0],*struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4)),int(bool(events))]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    impacts+=bool(events);contacts+=expected[21]!=state[21];bumps+=expected[-3]!=lo;failures+=expected[-6]==11
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert impacts>10 and contacts>500 and bumps>100
print(f'{len(cases)} complete original contact-point cases agree: {contacts} reactions, {bumps} random bumps and {impacts} failed-gear notifications; no numerical dependencies intercepted')
