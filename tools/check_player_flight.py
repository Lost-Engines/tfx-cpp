#!/usr/bin/env python3
"""Compare complete outer player callbacks and warm basic/autopilot handovers.

Original 0x8c184, 0x95f3c, 0x8c318 and 0x8f56c execute. Device acquisition,
timer inputs, surface lookup and output delivery are declared host boundaries.
No numerical flight callback, recovery, guidance or reset helper is replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent
from aerodynamic_snapshot import fields,tail,snapshot
from aerodynamic_autopilot_snapshot import snapshot as autopilot_snapshot

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--scenes',type=int,default=48)
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,0x4000);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x8f56c)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size));terrain_type=[50];callbacks=[];timer=[4,0];placing=[False]
im.intercept(0x8f686,'Stop only the initial-placement prefix; subsequent complete player callbacks execute',lambda image:image.cpu.emu_stop() if placing[0] else None)
im.intercept(0xb1334,'Supply caller-owned score variable; automatic landing subtraction executes',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0x303000),image.return_from()))
im.intercept(0x744e4,'Supply no DOS mouse driver',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
for file,reason in ((0x74614,'Host mouse reset'),(0x7457c,'Host mouse range'),(0x7459c,'Host mouse position'),(0x74508,'Host mouse samples'),(0xc4ac0,'Host calibrated joystick samples'),(0xc4b20,'Host joystick presence')):im.intercept(file,reason,lambda image:image.return_from())
im.intercept(0x8c43c,'Supply timer at its native call boundary, after any key-triggered physical reset',lambda image:(image.write(0x13476,'<H',timer[0]),image.write(0x142c0,'<Q',timer[1]),image.return_from()))
im.intercept(0xb0d80,'Supplied start-cell surface lookup',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
im.intercept(0xb7a3c,'Supplied start-surface classification',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,terrain_type[0]),image.return_from()))
for file in (0xb52d4,0xa4edc,0xa4dfc,0xa6068,0x81198,0x7dde4,0xa5074,0xa50a8):im.intercept(file,'Observe external model/radio/audio delivery; numerical player logic executes',lambda image:image.return_from())
for file,kind in ((0x8dc50,1),(0x8e280,2),(0x9fe14,3),(0x9fe50,4),(0x9feb4,5),(0x8e5a8,6),(0x8f198,7)):im.intercept(file,'Observe selected callback; instructions execute',lambda image,kind=kind:callbacks.append(kind))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
scenes=[]
for i in range(a.scenes):
 craft=1+i%3;model=(i//3)%4;landed=(i//12)%2;height=0
 start=[craft,model,landed,height,3,i%10,i%27,0,0x5926,0x3141,125952,0 if landed else -800,48128,0,32768,0,0,20,0,0]
 ticks=[]
 for t in range(96):
  action={8:3,9:6,36:4,50:6,60:2,61:6,84:6}.get(t,255)
  keys=rng.choice([0,0,0,1,2,4,8,16]) if t<8 or t>60 else 0
  ticks.append([rng.choice([2,4,6]),bits(.04),keys,int(t<30),int(t>80),0,(i//24)%2,action,3 if t%31==0 else 0,int(t>=76 and i%3==0),255,0,0,rng.randrange(-128,129),rng.randrange(-128,129),3 if landed and t==0 else 255,14 if t==32 else 255,11 if t==36 else 255,1 if t==60 and i%6==1 else 255])
 scenes.append((start,ticks))
requests=[]
for start,ticks in scenes:requests+=[' '.join(map(str,start)),str(len(ticks)),*(' '.join(map(str,row)) for row in ticks)]
output=subprocess.check_output([str((a.build/'player_flight_probe').resolve()),str(path)],input=('\n'.join(requests)+'\n').encode()).decode().splitlines();assert len(output)==sum(len(ticks) for _,ticks in scenes)
at=0;counts={}
for scene,(row,ticks) in enumerate(scenes):
 craft,model,landed,height,count,slot,weapon,occupied,low,high=row[:10];position=row[10:13];angles=row[13:16]
 im.cpu.mem_write(im.data,baseline);terrain_type[0]=50
 for field,value,fmt in ((0x11b2a,craft-1,'<H'),(0x1347a,(1,6,0,2)[model],'<B'),(0x11b3c,landed,'<B'),(0x1347b,255,'<B'),(0x86f4,.65 if not landed else 0,'<f'),(0x8f30,0,'<B'),(0x14956,0,'<H'),(0xe762,0,'<H'),(0xe774,0,'<B')):im.write(field,fmt,value)
 for field,value in zip((0x13424,0x13430,0x1343c),position):im.write(field,'<i',value)
 im.write(0x86c8,'<3H',*angles)
 for system in range(12):im.write(0x7d70+system,'<B',1 if (system in (2,5) and not landed) or (system==10 and landed) else 2)
 im.cpu.mem_write(im.data+0x13374,bytes(20));im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
 cells=bytes(v for index in range(count) for v in (30+index,40+index));im.cpu.mem_write(0x300100,struct.pack('<H',count)+cells);im.call(0x75228,eax=0x3000ff)
 im.call(0x8c184,limit=2000000);im.call(0x8c318)
 im.cpu.mem_write(im.STACK,struct.pack('<I',im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 placing[0]=True
 try:im.cpu.emu_start(im.native(0x8f56c),im.native(0x8f686),count=2000000)
 except Exception as error:raise RuntimeError(('placement',scene,hex(im.cpu.reg_read(r.UC_X86_REG_EIP)))) from error
 assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8f686)
 placing[0]=False
 for f,v,fmt in ((0x1b23c,0x300000,'<I'),(0xe76c,23,'<H'),(0x8867,1,'<B'),(0xabe9,0,'<B'),(0x8f32,1,'<B'),(0x8f31,0,'<B'),(0x8e22,1,'<B'),(0x8e23,1,'<B'),(0xabea,1,'<B'),(0xabf2,height,'<h'),(0x6c3c,9999,'<h'),(0x6c3a,2,'<h')):im.write(f,fmt,v)
 for tick,request in enumerate(ticks):
  elapsed,seconds,keys,accelerate,decelerate,buttons,source,action,refuel,disabled,gear,pitch,roll,joyx,joyy,engines,left_condition,right_condition,landing_phase=request
  timer[:]=[elapsed,seconds]
  im.write(0x13476,'<H',elapsed);im.write(0x142c0,'<Q',seconds);im.write(0x13478,'<B',source);im.write(0x13b04,'<B',refuel);im.write(0x86ce,'<B',disabled);im.write(0xac60,'<2h',joyx,joyy);im.write(0x10bf2,'<h',pitch);im.write(0x10bf0,'<h',roll);im.write(0x5968,'<H',buttons);im.write(0x596a,'<H',0);im.cpu.mem_write(0x300038,bytes([bool(keys&16)]))
  for f,v in zip((0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260),(bool(keys&1),bool(keys&2),bool(keys&4),bool(keys&8),accelerate,decelerate)):im.write(f,'<H',v)
  if engines!=255:im.write(0x14880,'<2d',float(bool(engines&1)),float(bool(engines&2)))
  if left_condition!=255:im.write(0x7d72,'<B',left_condition)
  if right_condition!=255:im.write(0x7d75,'<B',right_condition)
  if gear!=255:im.write(0x146d8,'<d',float(gear));im.write(0x7d7a,'<B',1 if gear else 2)
  if action!=255:im.call((0x85e3c,0x85e54,0x85e88,0x85ec4,0x85f00,0x85f24,0x85f90)[action],limit=2000000)
  if landing_phase!=255:im.write(0x86cf,'<B',landing_phase)
  im.write(0x14984,'<2h',30,40);im.write(0x8f84,'<2h',0,0);im.write(0x8f88,'<H',0);im.write(0x8f8b,'<B',0)
  im.cpu.mem_write(0x303000,struct.pack('<I',1000000))
  callbacks.clear();im.call(0x8f56c,limit=3000000);assert len(callbacks)==1
  expected=snapshot(im)+autopilot_snapshot(im)+[im.read(f,fmt)[0] for f,fmt in ((0x6c3c,'<h'),(0x6c3a,'<h'),(0x133f0,'<i'),(0x86f4,'<I'),(0x133e8,'<I'),(0x133cc,'<I'),(0x13440,'<I'))]+callbacks+[im.read(0x86cf,'<B')[0],(struct.unpack('<I',im.cpu.mem_read(0x303000,4))[0]-1000000)&0xffffffff]
  actual=list(map(int,output[at].split()));at+=1
  assert actual==expected,(scene,tick,craft,model,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if 260<=i<282 else 'outer',x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
  counts[callbacks[0]]=counts.get(callbacks[0],0)+1
print(f'{at} complete original outer player callbacks agree across {len(scenes)} initialized scenes and warm manual/autopilot transitions; all 324 retained fields, fuel smoothing and movement; callbacks {counts}')
