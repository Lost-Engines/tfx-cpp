#!/usr/bin/env python3
"""Compare full original automatic landing with initialized aircraft state.

Complete 0x95f3c initializes the scene and 0x9feb4 executes setup, approach,
rollout, touchdown, gear and view helpers. Score-variable lookup is a caller
boundary. Sound/model delivery and hardware transcendental adapters are the
only other intercepted dependencies; no numerical landing helper is replaced.
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
p.add_argument('--persistent',action='store_true')
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,0x4000);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x9feb4)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size));events=[];raw=[];finishes=[]
def score_lookup(image):
 assert bytes(image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_EAX),6))==b'score\0'
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x303000);image.return_from()
im.intercept(0xb1334,'Supply the caller-owned score variable address; subtraction executes natively',score_lookup)
def sound(image):
 sample=image.cpu.reg_read(r.UC_X86_REG_EAX);raw.append(('sound',sample))
 if sample==8:events.append(0)
 else:assert sample==1,sample
 image.return_from()
im.intercept(0xa4edc,'Observe afterburner/gear sound delivery',sound)
def stopped(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==0x31
 events.append(3);image.return_from()
im.intercept(0xa4dfc,'Observe stopped-landing sample delivery',stopped)
def model(image):
 entry=image.cpu.reg_read(r.UC_X86_REG_EDX);raw.append(('model',entry));assert entry in (3,4,10),entry
 if entry in (3,4):events.append(1 if entry==3 else 2)
 image.return_from()
im.intercept(0xb52d4,'Observe player SSD gear/reheat entries; model delivery is separate',model)
def auxiliary(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==5
 raw.append(('aux',image.cpu.reg_read(r.UC_X86_REG_EDX)));image.return_from()
im.intercept(0xa6068,'Observe auxiliary gear audio-driver request',auxiliary)
im.intercept(0xa02c8,'Observe touchdown finalization; instructions execute',lambda image:finishes.append(1))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];scenes=[]
for scene in range(48 if a.persistent else 1200):
 craft=1+scene%3;model=(scene//3)%2;phase=1 if scene%2 else 2
 im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
 if scene%4:
  for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
 frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18));start=[craft,model,0,0,0,0,0,1,3,7,1,0x5926,0x3141,0,400,*map(fbits,[rng.uniform(0,60000),-800,rng.uniform(0,60000)]),*frame,0,20]
 carrier=scene%2;inhibited=int(scene%23==0);ejected=int(scene%29==0);crashed=int(scene%31==0);condition=rng.choice([1,2,11,14]);gear=rng.choice([0,1])
 values=[gear,.02,rng.choice([0,.499999,.5,.500001,2.5,50,140]),rng.choice([-200,-50,-1,0]),rng.uniform(-.1,.1),0,rng.choice([-7,0,5,19,20]),rng.uniform(-63,63),rng.uniform(-63,63)]
 runway=[rng.randrange(200),rng.randrange(200),rng.randrange(-1000,1001),rng.randrange(-1000,1001),rng.randrange(65536),rng.choice([-20,-10,0,100])]
 target=[rng.randrange(1000000),0,rng.randrange(1000000)];player=[rng.randrange(1000000),0,rng.randrange(1000000)]
 ticks=[]
 for tick in range(512 if a.persistent else 1):ticks.append([phase if tick==0 else 255,carrier,inhibited,ejected,crashed,condition,*map(bits,values),*runway,*target,*player,int(scene%3==0)])
 scenes.append((start,ticks))
requests=[]
for start,ticks in scenes:requests+=[' '.join(map(str,start)),str(len(ticks)),*(' '.join(map(str,row)) for row in ticks)]
output=subprocess.check_output([str((a.build/'aerodynamic_probe').resolve()),str(path),'--landing-trace'],input=('\n'.join(requests)+'\n').encode()).decode().splitlines();assert len(output)==sum(1+len(ticks) for _,ticks in scenes)
at=updates=preparations=touchdowns=gear_changes=0
for scene,(start,ticks) in enumerate(scenes):
 initialise_reference(im,start,baseline);expected=snapshot(im);actual=list(map(int,output[at].split()));at+=1;assert actual==expected,('initialization',scene)
 im.cpu.mem_write(0x303000,struct.pack('<I',123456));im.write(0xe76c,'<H',23)
 for field in guide_fields:
  if field not in (0x143c8,0x14300):im.write(field,'<Q',0)
 for field,value,fmt in ((0x14962,1,'<H'),(0x1327a,0,'<H'),(0x1327c,0,'<H'),(0x1327e,0,'<H'),(0x13278,2,'<H'),(0x13270,0,'<Q'),(0x13269,0,'<B'),(0x597c,1,'<H'),(0x14938,0,'<H')):im.write(field,fmt,value)
 for tick,row in enumerate(ticks):
  phase,carrier,inhibited,ejected,crashed,condition=row[:6];values=row[6:15];cellx,cellz,offsetx,offsetz,heading,height=row[15:21];target=row[21:24];player=row[24:27];flare=row[27]
  im.write(0x142c0,'<Q',values[1]);im.write(0x14984,'<2h',cellx,cellz);im.write(0x8f84,'<2h',offsetx,offsetz);im.write(0x8f88,'<H',heading);im.write(0x8f8b,'<B',carrier);im.write(0xabf2,'<h',height);im.write(0x13eb8,'<Q',values[4]);im.write(0xabe9,'<B',inhibited);im.write(0x86ce,'<B',ejected)
  if phase!=255:
   im.write(0x86cf,'<B',phase);im.write(0x14920,'<3i',*target);im.write(0x1492c,'<3i',*player);im.write(0x14398,'<Q',values[5]);im.write(0x14378,'<Q',values[6]);im.write(0x1495a,'<H',flare);im.write(0x146d8,'<Q',values[0]);im.write(0x14700,'<Q',values[2]);im.write(0x14768,'<Q',values[3]);im.write(0x8c88,'<2Q',*values[7:]);im.write(0x12c04,'<H',crashed);im.write(0x7d7a,'<B',condition);im.write(0x1496d,'<B',2 if start[0]!=2 else 0)
  before=struct.unpack('<I',im.cpu.mem_read(0x303000,4))[0];events.clear();raw.clear();finishes.clear();enter_phase=im.read(0x86cf,'<B')[0]
  if enter_phase:im.call(0x9feb4,limit=1000000)
  expected=snapshot(im)+autopilot_snapshot(im)+[im.read(0x86cf,'<B')[0]]+[v&0xffffffff for f in (0x14920,0x1492c) for v in im.read(f,'<3i')]+[im.read(0x14398,'<Q')[0],im.read(0x14378,'<Q')[0],im.read(0x1495a,'<H')[0]]
  actual=list(map(int,output[at].split()));at+=1
  assert actual[:324]==expected,(scene,tick,start[0],[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if 260<=i<282 else 'landing',x,y) for i,(x,y) in enumerate(zip(actual[:324],expected)) if x!=y])
  change=(struct.unpack('<I',im.cpu.mem_read(0x303000,4))[0]-before)&0xffffffff
  assert actual[324:]==[change,int(enter_phase==1),len(events),*events],(scene,tick,'events',actual[324:],events,raw)
  gear=events.count(1)+events.count(2);assert sum(kind=='aux' for kind,_ in raw)==gear and raw.count(('sound',1))==gear
  updates+=bool(enter_phase);preparations+=enter_phase==1;touchdowns+=len(finishes);gear_changes+=gear
assert preparations>10 and touchdowns>100 if not a.persistent else touchdowns>10
print(f'{updates} complete original automatic landing callbacks agree across {len(scenes)} initialized scenes: {preparations} setups, {touchdowns} completed rollouts, {gear_changes} ordered gear changes; all 324 flight/autopilot/landing fields and score/output events')
