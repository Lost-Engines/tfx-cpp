#!/usr/bin/env python3
"""Compare joined advanced autopilot callbacks after complete native initialization.

Every scene warms the full manual model before requesting an autopilot mode.
Original 0x95f3c and 0x9fe14/0x9fe50 execute. Host input/output and the declared
hardware transcendental adapters are the only intercepted dependencies. Recovery
restoration is exercised on the final tick, before its pending next-frame reset.
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
from aerodynamic_autopilot_snapshot import guide_fields,snapshot as autopilot_snapshot

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--all-models',action='store_true',help='Exercise adaptive aerodynamic callbacks under Arcade and Simple settings too')
p.add_argument('--ils',action='store_true',help='Toggle ILS reference calculations during the trace')
p.add_argument('--persistent',action='store_true',help='Continue all modes through 96 ticks, including original outer-marker acknowledgment and key-triggered resets')
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,0x4000);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x9ac9c)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size));events=[];guided=[];recovering=[];recovery_changes=[];resets=[]
for file,reason in ((0x7457c,'Supplied host mouse range'),(0x7459c,'Supplied host mouse reset'),(0x74508,'Supplied host mouse samples')):im.intercept(file,reason,lambda image:image.return_from())
def sound(image):
 sample=image.cpu.reg_read(r.UC_X86_REG_EAX);count=image.read(0x1496d,'<B')[0]
 if sample==8:events.append(('reheat',4 if count==1 else 3))
 elif sample==0x4b:events.append(('reheat',1 if count==0 else 2))
 else:raise AssertionError(('unexpected controller sound',sample))
 image.return_from()
im.intercept(0xa4edc,'Observe ordered reheat sound delivery; handlers execute',sound)
for file in (0xb52d4,0xa4dfc,0x81198):
 def delivery(image,file=file):
  if file==0xa4dfc and image.cpu.reg_read(r.UC_X86_REG_EAX)==0x3d:events.append(('warning',))
  image.return_from()
 im.intercept(file,'Observe model/radio output delivery',delivery)
im.intercept(0x7dde4,'Observe descent warning radio delivery',lambda image:image.return_from())
for file,change in ((0x85ad0,1),(0x85b50,2)):
 im.intercept(file,'Observe recovery transition; instruction executes',lambda image,change=change:recovery_changes.append(change))
im.intercept(0x954fc,'Observe physical model reset; instructions execute',lambda image:resets.append(1))
im.intercept(0x953b8,'Observe failed-gear output delivery',lambda image:(events.append(('gear',)),image.return_from()))
im.intercept(0x9d64d,'Observe cockpit bump; instruction executes',lambda image:events.append(('bump',)))
im.intercept(0x9adae,'Observe guided branch entry; instruction executes',lambda image:guided.append(1))
im.intercept(0x9ab78,'Observe low-speed recovery entry; instruction executes',lambda image:recovering.append(1))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];scenes=[]
model_count=4 if a.all_models else 2
for scene in range((120 if a.persistent else 1200)*model_count//2):
 craft=1+scene%3;model=(scene//3)%model_count;mode=(scene//(3*model_count))%5
 im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
 if scene%4:
  for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
 frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18));position=[rng.uniform(0,60000),rng.choice([-20,-100,-1000,-8000]) if a.persistent else rng.uniform(-8000,-1000),rng.uniform(0,60000)]
 start=[craft,model,0,0,0,0,0,2 if a.persistent and scene%2 else 1,3,7,1,0x5926,0x3141,0,rng.choice([60,150,300,400,600,1000]),*map(fbits,position),*frame,0,20]
 cells=[rng.randrange(256) for _ in range(rng.choice([0,1,3,8])*2)]
 target=[rng.randrange(-1000000,10000000) for _ in range(3)]+[rng.randrange(200,1000)*65536]
 ticks=[]
 for tick in range(96 if a.persistent else 4):
  base=[bits(.02),scene%3,0,0,0,0,0,0,0,0,0,0,0,tick%2,scene%2,scene%3==0,0,0,0,1,0]
  requested_mode=65534 if a.persistent and tick in (40,80) else 65535 if tick>3 else mode if tick==3 else 0
  auto=[requested_mode,int(tick==3),rng.randrange(65536),bits(rng.uniform(-19000,-305)),bits(rng.uniform(100,600)),-32768 if tick>3 else rng.choice([0,1,len(cells)//2]),rng.randrange(65536),(scene//30)%2,len(cells)//2,int(a.ils and tick%3!=0),(1+tick%2) if model>=2 else 0,*cells,*target]
  ticks.append(base+auto)
 scenes.append((start,ticks))
requests=[]
for start,ticks in scenes:requests+=[' '.join(map(str,start)),str(len(ticks)),*(' '.join(str(int(v)) for v in row) for row in ticks)]
output=subprocess.check_output([str((a.build/'aerodynamic_probe').resolve()),str(path),'--autopilot-trace'],input=('\n'.join(requests)+'\n').encode()).decode().splitlines();assert len(output)==sum(1+len(ticks) for _,ticks in scenes)
at=updates=restores=engages=reheat=warnings=reset_updates=0
for scene,(start,ticks) in enumerate(scenes):
 initialise_reference(im,start,baseline)
 expected=snapshot(im);actual=list(map(int,output[at].split()));at+=1
 assert actual==expected,('initialization',scene)
 craft,model,landed=start[:3]
 for field,value,fmt in ((0x1347b,(1,6,0,2)[model],'<B'),(0x8f82,0,'<B'),(0x1b23c,0x300000,'<I'),(0xe76c,23,'<H'),(0x14962,1,'<H'),(0x1327a,0,'<H'),(0x1327c,0,'<H'),(0x1327e,0,'<H'),(0x13278,2,'<H'),(0x13270,0,'<Q'),(0x13269,0,'<B'),(0x8867,1,'<B'),(0xabe9,0,'<B'),(0x86ce,0,'<B')):im.write(field,fmt,value)
 for field in guide_fields:
  if field not in (0x143c8,0x14300):im.write(field,'<Q',0)
 im.write(0x14920,'<3i',0,0,0);im.write(0x1492c,'<3i',0,0,0)
 for field in (0x14280,0x142b0,0x14290,0x142a8):im.write(field,'<Q',0)
 for tick,row in enumerate(ticks):
  dt,source,up,left,down,right,alt,accelerate,decelerate,joyx,joyy,mx,my,wind,warp,pressure,braking,crashing,wet,gear_damage,surface=row[:21]
  mode,enabled,heading,target_down,target_speed,index,pitch,followed,count,ils,callback=row[21:32];cells=row[32:32+count*2];target=row[32+count*2:]
  im.write(0x142c0,'<Q',dt);im.write(0x13478,'<B',source);im.cpu.mem_write(0x300038,bytes([alt]))
  for f,v in zip((0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260),(up,left,down,right,accelerate,decelerate)):im.write(f,'<H',v)
  im.write(0xac60,'<2h',joyx,joyy);im.write(0x5964,'<2h',mx,my)
  for f,v,fmt in ((0x8f82,ils,'<B'),(0x8e25,wind,'<B'),(0xe780,warp,'<B'),(0x8f32,int(pressure),'<B'),(0x146b0,float(braking),'<d'),(0x8e22,crashing,'<B'),(0x8f31,wet,'<B'),(0x8e23,gear_damage,'<B'),(0xe75e,surface,'<H'),(0x11108,0x302000 if followed else 0,'<I'),(0x5978,0x301000,'<I')):im.write(f,fmt,v)
  if mode==65534:im.call(0x85a7c)
  elif mode!=65535:
   for f,v,fmt in ((0x14960,mode,'<H'),(0x14958,enabled,'<H'),(0x1493a,heading,'<H'),(0x14348,target_down,'<Q'),(0x8d40,target_speed,'<Q')):im.write(f,fmt,v)
  if index!=-32768:im.write(0x597c,'<h',index);im.write(0x14938,'<H',pitch)
  im.cpu.mem_write(0x301000,struct.pack('<H',count)+bytes(cells));im.cpu.mem_write(0x302000,struct.pack('<3i',*target[:3]));im.cpu.mem_write(0x30200e,struct.pack('<H',12345));im.cpu.mem_write(0x302012,struct.pack('<i',target[3]))
  events.clear();recovery_changes.clear();resets.clear();im.call(0x9fe50 if callback==2 or (callback==0 and model==1) else 0x9fe14,limit=2000000)
  expected=snapshot(im)+autopilot_snapshot(im)+[im.read(f,'<Q')[0] for f in (0x14280,0x142b0,0x14290,0x142a8,0x143c8)];actual=list(map(int,output[at].split()));at+=1
  assert actual[:319]==expected,(scene,tick,craft,model,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if 260<=i<282 else 'autopilot',x,y) for i,(x,y) in enumerate(zip(actual[:319],expected)) if x!=y],len(expected))
  gear=sum(e[0]=='gear' for e in events);bump=int(any(e[0]=='bump' for e in events));changes=[e[1] for e in events if e[0]=='reheat'];warning=int(any(e[0]=='warning' for e in events))
  assert actual[319:]==[gear,bump,len(changes),*changes,len(recovery_changes),*recovery_changes,warning],(scene,tick,'outputs',actual[319:],events)
  updates+=1;restores+=recovery_changes.count(2);engages+=recovery_changes.count(1);reheat+=len(changes);warnings+=warning;reset_updates+=len(resets)
  im.write(0x1347b,'<B',(1,6,0,2)[model]) # Original outer caller 0x8f98c, after snapshot.
assert len(guided)>100 and len(recovering)>100
if a.persistent:assert engages>10 and reset_updates>10
print(f'{updates} joined flight updates agree in {len(scenes)} complete original-initialized scenes: {len(guided)} guided branches, {len(recovering)} speed recoveries, {engages} automatic engagements, {restores} recovery restorations, {reset_updates} entry resets, {warnings} descent warnings, {reheat} reheat changes; all 319 snapshot fields and outputs')
