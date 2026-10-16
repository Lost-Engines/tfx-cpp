#!/usr/bin/env python3
"""Compare persistent joined manual flight with complete native callbacks.

Original 0x95f3c initializes each scene, then full 0x9fe14/0x9fe50 callbacks run.
Gear remains deployed in this first corpus, excluding the separate airborne
automatic-recovery/autopilot producer. Device samples and output delivery are
explicit boundaries; no numerical flight routines are stubbed.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent
from aerodynamic_reference import initialise_reference
from aerodynamic_snapshot import fields,tail,snapshot

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,4096);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x9fe14)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size))
events=[]
for file,reason in ((0x7457c,'Supplied host mouse range'),(0x7459c,'Supplied host mouse reset'),(0x74508,'Supplied host mouse samples')):im.intercept(file,reason,lambda image:image.return_from())
im.intercept(0xa4edc,'Observe sound delivery; original reheat/controller logic executes',lambda image:(events.append(('sound',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
im.intercept(0xb52d4,'Observe player SSD reheat delivery',lambda image:(events.append(('model',image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX))),image.return_from()))
im.intercept(0x953b8,'Observe failed-gear output delivery',lambda image:(events.append(('gear',)),image.return_from()))
im.intercept(0x9d64d,'Observe cockpit bump scheduling; original instruction still executes',lambda image:events.append(('bump',)))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];scenes=[]
for craft in range(1,4):
 for model in range(2):
  for landed in range(2):
   for source in range(3):
    position=[10000,-5 if landed else -4000,10000]
    start=[craft,model,landed,0,landed,0,0,1,3,7,1,0x5926,0x3141,0,0 if landed else 400,*map(fbits,position),*identity,0,20]
    ticks=[]
    for tick in range(256):
     keys=[int(tick%100 in range(40,48)),int(tick%100 in range(70,78)),int(tick%100 in range(60,64)),int(tick%100 in range(90,94))]
     joystick=[rng.randrange(-100,101) for _ in range(2)]
     mouse=[rng.randrange(-150,151) for _ in range(2)]
     ticks.append([bits(.02),source,*keys,int(tick%70<5),int(tick<100),0,*joystick,*mouse,int(tick%2==0),0,int(tick%3==0),int(landed and tick<10),0,0,1,0])
    scenes.append((start,ticks))
requests=[]
for start,ticks in scenes:requests += [' '.join(map(str,start)),str(len(ticks)),*(' '.join(map(str,row)) for row in ticks)]
output=subprocess.check_output([str((a.build/'aerodynamic_probe').resolve()),str(path),'--trace'],input=('\n'.join(requests)+'\n').encode()).decode().splitlines();assert len(output)==sum(1+len(ticks) for _,ticks in scenes)
at=updates=0
for scene,(start,ticks) in enumerate(scenes):
 initialise_reference(im,start,baseline)
 expected=snapshot(im);actual=list(map(int,output[at].split()));at+=1
 assert actual==expected,('initialization',scene,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
 craft,model,landed=start[:3];im.write(0x1347b,'<B',6 if model else 1);im.write(0x8f82,'<B',0);im.write(0x1b23c,'<I',0x300000);im.write(0xe76c,'<H',23)
 for tick,row in enumerate(ticks):
  dt,source,up,left,down,right,alt,accelerate,decelerate,joyx,joyy,mx,my,wind,warp,pressure,braking,crashing,wet,gear_damage,surface=row
  im.write(0x142c0,'<Q',dt);im.write(0x13478,'<B',source);im.cpu.mem_write(0x300038,bytes([alt]))
  for field,value in zip((0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260),(up,left,down,right,accelerate,decelerate)):im.write(field,'<H',value)
  im.write(0xac60,'<2h',joyx,joyy);im.write(0x5964,'<2h',mx,my);im.write(0x8e25,'<B',wind);im.write(0xe780,'<B',warp);im.write(0x8f32,'<B',pressure);im.write(0x146b0,'<d',float(braking));im.write(0x8e22,'<B',crashing);im.write(0x8f31,'<B',wet);im.write(0x8e23,'<B',gear_damage);im.write(0xe75e,'<H',surface)
  events.clear();im.call(0x9fe50 if model else 0x9fe14,limit=2000000)
  expected=snapshot(im)
  actual=list(map(int,output[at].split()));at+=1
  assert actual[:282]==expected,(scene,tick,craft,model,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if i>=260 else 'random',x,y) for i,(x,y) in enumerate(zip(actual[:282],expected)) if x!=y])
  gear=sum(e[0]=='gear' for e in events);bump=int(any(e[0]=='bump' for e in events))
  assert actual[282:284]==[gear,bump],(scene,tick,'ground outputs',actual[282:],events)
  assert not events or all(e[0] in ('gear','bump') for e in events),(scene,tick,events)
  assert actual[284]==0,(scene,tick,'unexpected afterburner output')
  updates+=1
print(f'{updates} persistent advanced manual updates agree in {len(scenes)} complete native initialized trajectories across all aircraft/models/device sources; all 282 fields, view exports, random states and declared outputs')
