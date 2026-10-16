#!/usr/bin/env python3
"""Compare native 6/5/7/8/9/0/A flight keys on complete initialized aircraft.

Original 0x95f3c and complete key handlers execute, including physical resets
and recovery/afterburner helpers. The external autopilo on/off callback and
radio/sound/SSD delivery are caller boundaries. Hardware transcendental
adapters are the only intercepted numerical dependencies.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent
from aerodynamic_reference import initialise_reference
from aerodynamic_snapshot import fields,tail,snapshot
from aerodynamic_autopilot_snapshot import guide_fields,snapshot as autopilot_snapshot

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,0x5000);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x85f90)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size));notices=[];external=[];recovery=[];reheat=[];resets=[]
messages={0x19d4:1,0x1a60:1,0x19fc:2,0x1a1c:3,0x1a3c:4,0x1aa0:4,0x1a80:5,0x1ac4:6,0x19a4:7,0x19bc:8}
def message(image):
 notices.append(messages[image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data]);image.return_from()
im.intercept(0x81198,'Observe pilot-key radio delivery',message)
def sound(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==8
 reheat.append(4 if image.read(0x1496d,'<B')[0]==1 else 3);image.return_from()
im.intercept(0xa4edc,'Observe ordered recovery reheat-stop delivery',sound)
im.intercept(0xb52d4,'Observe recovery player SSD delivery',lambda image:image.return_from())
im.intercept(0x954fc,'Observe immediate physical reset; instructions execute',lambda image:resets.append(1))
im.intercept(0x85b50,'Observe recovery restoration; instructions execute',lambda image:recovery.append(2))
def status(cpu,address,size,unused):
 stack=cpu.reg_read(r.UC_X86_REG_ESP);kind,name,value,last=struct.unpack('<4I',cpu.mem_read(stack+4,16))
 assert (kind,name,last)==(1,im.data+0x9e2a,0)
 assert value in (im.data+0x9e78,im.data+0x9e5e)
 external.append(1 if value==im.data+0x9e78 else 2);im.return_from()
im.cpu.hook_add(UC_HOOK_CODE,status,begin=0x304000,end=0x304000)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for i in range(1536):
 craft=1+i%3;model=(i//3)%2
 im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
 if i%4:
  for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
 frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18))
 start=[craft,model,(i//6)%2,(i//12)%2,(i//24)%2,0,0,rng.choice([1,2]),3,rng.randrange(27),1,0x5926,0x3141,rng.choice([-20,-11,-10,0,100]),rng.choice([0,100,400,1000]),*map(fbits,[rng.uniform(0,60000),rng.choice([-800,-10,5]),rng.uniform(0,60000)]),*frame,0,20]
 key=[i%7,i%2,int(i%13==0),int(i%17==0),int(i%19==0),(i//2)%2,(i//3)%2,rng.choice([0,1,2,3,4,5,65535]),rng.randrange(65536),rng.choice([1,2,11,14]),rng.choice([1,2,11,14]),0 if craft==2 else 2,bits(rng.choice([0,-0.,180.25,500])),bits(rng.uniform(-20000,0)),bits(rng.uniform(0,700)),fbits(rng.uniform(-10000,10)),rng.randrange(-32768,32768),bits(rng.choice([200,300,340,360]))]
 cases.append((start,key))
requests=[]
for start,key in cases:requests+=[' '.join(map(str,start)),' '.join(map(str,key))]
output=subprocess.check_output([str((a.build/'aerodynamic_probe').resolve()),str(path),'--pilot-key'],input=('\n'.join(requests)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)*2
reset_count=restores=externals=announcements=0
for case,(start,key) in enumerate(cases):
 initialise_reference(im,start,baseline);actual=list(map(int,output[case*2].split()));assert actual==snapshot(im),('initialization',case)
 action,pressure,inhibited,ejected,crashed,available,enabled,mode,heading,brake,saved_brake,after,speed,down,physical_speed,view_height,track,sound_speed=key
 for f in guide_fields:
  if f not in (0x143c8,0x14300):im.write(f,'<Q',0)
 im.write(0x14920,'<3i',0,0,0);im.write(0x1492c,'<3i',0,0,0)
 for f,v,fmt in ((0x14962,1,'<H'),(0x1327a,0,'<H'),(0x1327c,0,'<H'),(0x1327e,0,'<H'),(0x13278,2,'<H'),(0x13270,0,'<Q'),(0x13269,0,'<B'),(0x597c,1,'<H'),(0x14938,0,'<H'),(0x13280,saved_brake,'<H'),(0x8f32,pressure,'<B'),(0xabe9,inhibited,'<B'),(0x86ce,ejected,'<B'),(0x12c04,crashed,'<H'),(0x8867,available,'<B'),(0x14958,enabled,'<H'),(0x14960,mode,'<H'),(0x1493a,heading,'<H'),(0x7d77,brake,'<B'),(0x1496d,after,'<B'),(0x8d40,speed,'<Q'),(0x14348,down,'<Q'),(0x14700,physical_speed,'<Q'),(0x13428,view_height,'<I'),(0x148f8,track,'<i'),(0x14790,sound_speed,'<Q'),(0x142c0,.1,'<d'),(0xac74,0x304000,'<I'),(0xe76c,23,'<H')):im.write(f,fmt,v)
 notices.clear();external.clear();recovery.clear();reheat.clear();resets.clear();im.call((0x85e3c,0x85e54,0x85e88,0x85ec4,0x85f00,0x85f24,0x85f90)[action],limit=2000000)
 expected=snapshot(im)+autopilot_snapshot(im)+[im.read(0x13280,'<H')[0],im.read(0x8f32,'<B')[0]]
 actual=list(map(int,output[case*2+1].split()))
 assert actual[:316]==expected,(case,action,start,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if 260<=i<282 else 'autopilot',x,y) for i,(x,y) in enumerate(zip(actual[:316],expected)) if x!=y])
 assert len(notices)<=1 and len(external)<=1 and len(recovery)<=1 and len(resets)<=1
 assert actual[316:]==[notices[0] if notices else 0,external[0] if external else 0,recovery[0] if recovery else 0,int(bool(resets)),len(reheat),*reheat],(case,'outputs',actual[316:],notices,external,recovery,resets,reheat)
 reset_count+=len(resets);restores+=len(recovery);externals+=len(external);announcements+=len(notices)
assert reset_count>30 and restores>5 and announcements>100
print(f'{len(cases)} complete original pilot-key updates agree: {reset_count} immediate physical resets, {restores} recovery restorations, {externals} external on/off requests and {announcements} notices; all 316 flight/control fields and output events')
