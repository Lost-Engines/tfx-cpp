#!/usr/bin/env python3
"""Compare full thrust, fuel and progressive engine-fault routines.

Native 0x99424, 0x995e0 and 0x9cc54 execute, separately and in native frame
order. Startup and random generation execute. Bounded FSIN/FCOS use actual
host instructions; only sound/model notifications are intercepted and checked.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backend=hardware_sine_cosine(im,a.build);rng=random.Random(0x9cc54);events=[]
im.intercept(0xa4edc,'Capture afterburner stop sound request; complete fuel/stop handler executes',lambda image:(events.append(('sound',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
im.intercept(0xb52d4,'Capture player afterburner SSD notification; resource delivery is outside the powerplant',lambda image:(events.append(('model',image.cpu.reg_read(r.UC_X86_REG_EAX))),image.return_from()))
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
state_vectors=[(0x14880,2),(0x14838,2),(0x147d8,3),(0x147c0,3)]
state_scalars=[0x14878,0x14858,0x14850,0x14750,0x14308]
parameters=[0x140a8,0x14078,0x14128,0x140c0,0x14070,0x14120,0x14118]
cases=[]
for index in range(8192):
    craft=1+index%3;stages=0 if craft==2 else 4;afterburner=rng.randrange(stages+1)
    factors=[rng.choice([0,1,.00001,.05,rng.uniform(0,1)]) for _ in range(2)]
    vectors=factors+[rng.uniform(-.35,.35) for _ in range(2)]+[rng.uniform(-1e5,1e5) for _ in range(6)]
    scalars=[rng.uniform(0,200000),rng.choice([0,.000001,100,70000,rng.uniform(0,10000)]),rng.choice([4000,7938,9979]),rng.choice([0,4000]),rng.uniform(0,20)]
    params=[rng.choice([120000,96000,187200]),rng.choice([60000,124800]),20.3,rng.choice([.00059,.0007,.00029]),.003,rng.choice([0,.675]),rng.choice([0,-5.7])]
    context=[rng.choice([0,10,20.3,25,rng.uniform(0,30)]),rng.choice([.02,.04,.1,1])]
    cases.append([index%4,craft,(index//4)%2,afterburner,rng.randrange(15),rng.randrange(15),rng.choice([1,2,11,14]),rng.choice([1,2,11,14]),stages,rng.randrange(65536),rng.randrange(65536),float_bits(rng.choice([0,.6,.6000001,1,rng.uniform(0,1)])),*map(bits,vectors+scalars),rng.randrange(-32768,32768),*map(bits,params+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_powerplant_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];stops=0
for index,(row,line) in enumerate(zip(cases,output)):
    op,craft,warp,afterburner,control,display,left,right,stages,low,high,throttle=row[:12];values=row[12:27];readout=row[27];params=row[28:35];altitude,seconds=row[35:]
    im.write(0x11b2a,'<H',craft-1);im.write(0xe780,'<B',warp);im.write(0x1496d,'<B',afterburner);im.write(0x10bed,'<B',control);im.write(0x6c38,'<B',display);im.write(0x7d72,'<B',left);im.write(0x7d75,'<B',right);im.write(0x8cd8+craft-1,'<B',stages);im.write(0x133f8,'<I',throttle);im.write(0xe76c,'<H',23)
    at=0
    for offset,count in state_vectors:im.write(offset,'<'+str(count)+'Q',*values[at:at+count]);at+=count
    for offset,value in zip(state_scalars,values[at:]):im.write(offset,'<Q',value)
    im.write(0x6c3c,'<h',readout)
    for offset,value in zip(parameters,params):im.write(offset,'<Q',value)
    im.write(0x14060,'<Q',altitude);im.write(0x142c0,'<Q',seconds)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high));events.clear()
    if op in (1,3):im.call(0x99424)
    if op in (2,3):im.call(0x995e0)
    if op in (0,3):im.call(0x9cc54)
    assert not events or events==[('sound',8,10),('model',23)],events
    expected=[v for offset,count in state_vectors for v in im.read(offset,'<'+str(count)+'Q')]+[im.read(offset,'<Q')[0] for offset in state_scalars]
    expected += [im.read(offset,'<B')[0] for offset in (0x7d72,0x7d75,0x1496d,0x10bed,0x6c38)]+[im.read(0x6c3c,'<H')[0],*struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4)),int(bool(events))]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    stops+=bool(events)
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert stops>100
print(f'Aerodynamic powerplants agree in {len(cases)} complete original thrust/fuel/fault cases, including {stops} ordered afterburner-stop notifications; explicit hardware FSIN/FCOS')
