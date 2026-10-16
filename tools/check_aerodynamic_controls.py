#!/usr/bin/env python3
"""Compare complete advanced-model device/throttle/target input (0x9a104).

Original startup and complete numerical handler execute. Only host mouse
range/reset/acquisition and ordered afterburner-stop sound/model delivery are
intercepted. Direction/raw Alt keys, mouse/joystick samples and limits are inputs.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);im.write(0x1b23c,'<I',0x300000);rng=random.Random(0x9a104);events=[]
for file,reason in [(0x7457c,'Host mouse range is supplied, not a numerical flight rule'),(0x7459c,'Host mouse reset is supplied at the sample boundary'),(0x74508,'Host mouse position is explicitly supplied')]:im.intercept(file,reason,lambda image:image.return_from())
im.intercept(0xa4edc,'Record ordered afterburner-stop sound request',lambda image:(events.append(('sound',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
im.intercept(0xb52d4,'Record player afterburner SSD notification; delivery is separate',lambda image:(events.append(('model',image.cpu.reg_read(r.UC_X86_REG_EAX))),image.return_from()))
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
state_fields=[0x148a0,0x14788,0x14730,0x14898,0x140b8,0x148f0,0x142e8,0x14368,0x142e0]
context_fields=[0x142c0,0x14700,0x148b8,0x148b0,0x148a8,0x14360,0x14848,0x13d28]
cases=[]
for index in range(8192):
    source=index%3;keys=[rng.randrange(2) for _ in range(4)];alt=rng.randrange(2);ground=rng.randrange(2);accelerate=rng.randrange(2);decelerate=rng.randrange(2);auto=(index//3)%2;mode=rng.randrange(5);heading=rng.randrange(65536);afterburner=rng.randrange(5);control=rng.randrange(15);display=rng.randrange(15)
    mouse=[rng.choice([-512,-113,-112,-111,-53,-52,-51,0,51,52,53,111,112,113,512,rng.randrange(-512,513)]) for _ in range(2)]
    joystick=[rng.choice([-512,-1,0,1,512,rng.randrange(-512,513)]) for _ in range(2)]
    state=[rng.uniform(-1,1) for _ in range(6)]+[rng.uniform(-2,0),rng.uniform(0,2),rng.uniform(0,2)]
    targets=[rng.choice([-304.8,-19812,rng.uniform(-25000,0)]),rng.choice([52,590,rng.uniform(0,700)])]
    engines=[rng.choice([0,1,rng.uniform(0,1)]) for _ in range(2)]
    context=[rng.choice([.02,.1,1]),rng.choice([0,204.999,205,205.001,rng.uniform(0,700)]),rng.choice([.4,1]),rng.choice([.19,.152]),rng.choice([.03,.024]),rng.uniform(.5,2),rng.uniform(-.5,.5),rng.choice([590,306,678.5])]
    cases.append([source,*keys,alt,ground,accelerate,decelerate,auto,mode,heading,afterburner,control,display,*mouse,*joystick,float_bits(rng.choice([0,.59,.6,.61,1,rng.uniform(0,1)])),*map(bits,state+targets+engines+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_controls_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];stops=0
for index,(row,line) in enumerate(zip(cases,output)):
    source,up,left,down,right,alt,ground,accelerate,decelerate,auto,mode,heading,afterburner,control,display=row[:15];mouse=row[15:17];joystick=row[17:19];throttle=row[19];state=row[20:29];targets=row[29:31];engines=row[31:33];context=row[33:]
    im.write(0x13478,'<B',source);im.cpu.mem_write(0x300038,bytes([alt]));im.write(0x8d38,'<H',ground);im.write(0x14958,'<H',auto);im.write(0x14960,'<H',mode);im.write(0x1493a,'<H',heading);im.write(0x1496d,'<B',afterburner);im.write(0x10bed,'<B',control);im.write(0x6c38,'<B',display);im.write(0x133f8,'<I',throttle);im.write(0xe76c,'<H',23)
    for offset,value in zip((0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260),(up,left,down,right,accelerate,decelerate)):im.write(offset,'<H',value)
    im.write(0x5964,'<2h',*mouse);im.write(0xac60,'<2h',*joystick)
    for offset,value in zip(state_fields,state):im.write(offset,'<Q',value)
    im.write(0x14348,'<Q',targets[0]);im.write(0x8d40,'<Q',targets[1]);im.write(0x14880,'<2Q',*engines)
    for offset,value in zip(context_fields,context):im.write(offset,'<Q',value)
    events.clear();im.call(0x9a104)
    assert not events or events==[('sound',8,10),('model',23)],events
    expected=[im.read(offset,'<Q')[0] for offset in state_fields]+[im.read(offset,'<Q')[0] for offset in (0x14348,0x8d40)]+[im.read(0x1493a,'<H')[0],im.read(0x133f8,'<I')[0]]+[im.read(offset,'<B')[0] for offset in (0x1496d,0x10bed,0x6c38)]+[int(bool(events))]
    actual=list(map(int,line.split()));assert actual==expected,(index,source,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    stops+=bool(events)
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert stops>50
print(f'Aerodynamic input agrees in {len(cases)} complete original keyboard/joystick/mouse, throttle and autopilot-target updates, including {stops} afterburner stops; explicit device/output boundaries')
