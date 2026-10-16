#!/usr/bin/env python3
"""Compare complete native maintain/recovery speed controllers and reheat keys.

Original 0x9aa4c/0x9ab78 and 0x84ce8/0x84d2c execute under original startup.
Only ordered sound, player-model and external-device notifications are captured.
"""
import argparse
from pathlib import Path
import math
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x9aa4c);events=[]
im.intercept(0xa4edc,'Capture original reheat sound requests in order',lambda image:(events.append(('sound',image.cpu.reg_read(r.UC_X86_REG_EAX))),image.return_from()))
im.intercept(0xb52d4,'Capture player reheat entry in order; SSD delivery is separate',lambda image:(events.append(('model',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
im.intercept(0xa6068,'Capture optional external-device command; no host device is present',lambda image:(events.append(('device',image.cpu.reg_read(r.UC_X86_REG_EAX))),image.return_from()))
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
cases=[]
for index in range(8192):
    stages=rng.choice([0,1,4]);afterburner=rng.randrange(stages+1);speed=rng.uniform(0,1000)
    target=speed+rng.choice([-20,-10,-5,0,5,10,20,50,math.nextafter(20,0),math.nextafter(20,30),rng.uniform(-100,100)])
    values=[target,rng.choice([0,1,rng.uniform(0,1)]),rng.uniform(0,1),rng.choice([0,1]),rng.choice([0,1]),rng.choice([0,.001,1000])]
    context=[speed,rng.uniform(1000,30000),rng.uniform(-1e6,1e6),rng.choice([0,.024])]
    cases.append([index%2,stages,afterburner,rng.randrange(15),rng.randrange(15),rng.choice([1,2,11,14]),*map(bits,values),float_bits(rng.choice([0,.6,1,1.1,rng.uniform(0,1.5)])),*map(bits,context)])
output=subprocess.check_output([str((a.build/'aerodynamic_speed_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];changes=0
for index,(row,line) in enumerate(zip(cases,output)):
    strategy,stages,old,control,display,brake=row[:6];values=row[6:12];throttle=row[12];context=row[13:]
    im.write(0x11b2a,'<H',0);im.write(0x8cd8,'<B',stages);im.write(0x1496d,'<B',old);im.write(0x10bed,'<B',control);im.write(0x6c38,'<B',display);im.write(0x7d77,'<B',brake);im.write(0x133f8,'<I',throttle);im.write(0xe76c,'<H',23)
    for offset,value in zip((0x8d40,0x145a8,0x14890,0x14880,0x14888,0x14858),values):im.write(offset,'<Q',value)
    for offset,value in zip((0x14700,0x14320,0x14610,0x14430),context):im.write(offset,'<Q',value)
    events.clear();im.call(0x9ab78 if strategy else 0x9aa4c)
    new=im.read(0x1496d,'<B')[0]
    change=1 if new>old and old==0 else 2 if new>old else 4 if new<old and new==0 else 3 if new<old else 0
    wanted=[]
    if change in (1,2):
        if change==1:wanted.append(('model',23,9))
        wanted.extend([('sound',75),('device',1)])
    if change in (3,4):
        wanted.append(('sound',8))
        if change==4:wanted.append(('model',23,10))
    assert events==wanted,(index,change,events,wanted)
    expected=[im.read(offset,'<Q')[0] for offset in (0x8d40,0x145a8,0x14890)]+[im.read(0x133f8,'<I')[0]]+[im.read(offset,'<B')[0] for offset in (0x1496d,0x10bed,0x6c38,0x7d77)]+[change]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    changes+=bool(change)
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert changes>100
print(f'Aerodynamic maintain/recovery speed control agrees in {len(cases)} complete original updates and {changes} ordered afterburner changes; explicit output boundaries')
