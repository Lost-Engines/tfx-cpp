#!/usr/bin/env python3
"""Compare the original incoming-projectile warning pass and shared randomness.

The whole native 0xa31cc population pass executes. Motion is a supplied no-op,
player distance is supplied independently of geometry, and nearby projectile-trail output is
omitted. Music output and the actual urgent-sample descriptor call are observed.
No warning, timer, range, target, gate or random-selection branch is replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0xa31cc)
im=NativeReference(a.data_dir/'TFX.DAT');cpu=im.cpu
cpu.mem_map(0x300000,0x30000)
head,tail,motion,audio=0x300000,0x300100,0x320000,0x320100
cpu.mem_write(motion,b'\xc3');cpu.mem_write(audio,b'\xc3')
im.write(0x16e80,'<I',head);im.write(0x16e7c,'<I',tail);im.write(0xac74,'<I',audio)
events=[];distances={}
def distance(image):
 value=distances[cpu.reg_read(r.UC_X86_REG_ESI)]
 cpu.reg_write(r.UC_X86_REG_EAX,value&0xffffffff);image.return_from(stack_bytes=4)
im.intercept(0x7d208,'Supply the post-motion player distance; coordinate arithmetic is a separate verified helper.',distance)
im.intercept(0x7b7fc,'Omit the nearby-projectile trail-point producer; it does not feed warning decisions.',lambda image:image.return_from(stack_bytes=8))
def music(image):
 events.extend((0,cpu.reg_read(r.UC_X86_REG_EAX)));image.return_from()
im.intercept(0xa5a9c,'Observe the requested music cue without running the separately compared controller/OSL devices.',music)
def sample(cpu,address,size,user):
 sp=cpu.reg_read(r.UC_X86_REG_ESP)
 priority,descriptor,end=struct.unpack('<3I',cpu.mem_read(sp+4,12))
 assert end==0 and (descriptor-im.data-0x9860)%26==0
 events.extend((1,priority,(descriptor-im.data-0x9860)//26));im.return_from()
cpu.hook_add(UC_HOOK_CODE,sample,begin=audio,end=audio)
im.intercept(0xa373c,'No actor/world contacts are supplied for the synthetic warning population.',lambda image:image.return_from())

def original(row,frames=1,population=False):
 count=row[6]
 cooldown,low,high,elapsed,enabled,inhibited,_=row[:7]
 im.write(0x16e90,'<h',cooldown);im.write(0x16e94,'<H',65535)
 im.write(0x13476,'<H',elapsed);im.write(0xe774,'<B',enabled);im.write(0xabe9,'<B',inhibited)
 cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
 records=[0x300200+i*80 for i in range(count)];distances.clear()
 cpu.mem_write(head+52,struct.pack('<I',records[0] if count else tail))
 shots=[row[7+i*3:10+i*3] for i in range(count)]
 for i,(pointer,(separation,proximity,targeted)) in enumerate(zip(records,shots)):
  body=bytearray(80);body[6]=i
  struct.pack_into('<3i',body,8,0,-25600,0)
  struct.pack_into('<I',body,48,im.data+0x10f28 if targeted else 0x310000)
  struct.pack_into('<I',body,52,records[i+1] if i+1<count else tail)
  struct.pack_into('<I',body,60,motion);struct.pack_into('<h',body,64,1)
  cpu.mem_write(pointer,bytes(body));im.write(0x809c+48*i+43,'<B',proximity);distances[pointer]=separation
 events.clear()
 for _ in range(frames):im.call(0x71fd4,eax=elapsed,limit=1000000) if population else im.call(0xa31cc,limit=100000)
 values=[im.read(0x16e90,'<h')[0],im.read(0x16e94,'<H')[0],*struct.unpack('<2H',cpu.mem_read(im.native(0xc9894),4)),len(events),*events]
 return values

cases=[];expected=[];fixtures=[]
for index in range(8192):
 count=index%17
 row=[rng.choice([0,0,0,1,499,500,32767,-32768,rng.randrange(-32768,32768)]),rng.randrange(65536),rng.randrange(65536),rng.choice([0,1,4,10,499,500,501,32767,32768,65535]),int(rng.randrange(6)!=0),int(rng.randrange(6)==0),count]
 # Preserve list order so simultaneous near threats compete for one cooldown.
 shots=[(rng.choice([-1,0,1999,2000,3999,4000,7999,8000,8001,rng.randrange(20000)]),int(rng.randrange(4)!=0),int(rng.randrange(4)!=0)) for _ in range(count)]
 for shot in shots:row.extend(shot)
 values=original(row)
 cases.append(row);expected.append(values)
 if index<256:fixtures.append(' '.join(map(str,row+values)))
result=subprocess.check_output([str((a.build/'projectile_warnings_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in cases)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for index,(line,values) in enumerate(zip(result,expected)):
 actual=list(map(int,line.split()));assert actual==values,(index,cases[index],actual,values)
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(cases)} original population warning passes agree: signed cooldown wrapping, substep count reset, both strict distance boundaries, target/gate suppression, ordered music/urgent samples and shared RNG')

rows=[];reference=[];total=0
for index in range(512):
 row=list(cases[index*16]);row[0]=0;row[3]=rng.choice([0,1,10,18,55])
 frames=rng.choice([1,2,16,64]);rows.append([frames,*row]);reference.append(original(row,frames,True));total+=frames
result=subprocess.check_output([str((a.build/'projectile_warnings_probe').resolve()),'--population'],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(reference)
for index,(line,values) in enumerate(zip(result,reference)):
 actual=list(map(int,line.split()));assert actual==values,('population',index,rows[index],actual,values)
print(f'{total} joined original projectile frames across {len(rows)} persistent populations agree, including the real clock wrapper, zero-tick updates, cooldown expiry, suppression and exact RNG/output order')
