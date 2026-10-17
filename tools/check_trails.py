#!/usr/bin/env python3
"""Compare original smoke-trail segment sampling and the independent 200-slot pool.

For segments, visibility is supplied and enqueue output is observed; all word
arithmetic, native distance, midpoint, IDIV stepping and loop decisions execute.
For the pool, resource/model delivery and destroyed flags are boundaries;
allocation/reuse, records, queue order and native distance cleanup execute.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from check_projectiles import CALLBACKS

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record-segments',type=Path)
p.add_argument('--record-pool',type=Path)
p.add_argument('--record-dispatch',type=Path)
a=p.parse_args();data=a.research/'installs/cd_1994_09/TFX';rng=random.Random(0x7b7fc)
wrap=lambda n:struct.unpack('<i',struct.pack('<I',n&0xffffffff))[0]
word=lambda n:struct.unpack('<h',struct.pack('<H',n&65535))[0]
def digest(values):
 result=14695981039346656037
 for value in values:
  for byte in struct.pack('<I',value&0xffffffff):result=((result^byte)*1099511628211)&0xffffffffffffffff
 return result

def compare(rows,expected,record,*,stateful=False):
 output=subprocess.check_output([str((a.build/'trails_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
 assert len(output)==len(expected)
 for case,(line,value) in enumerate(zip(output,expected)):assert int(line)==value,(case,rows[case],line,value)
 if record:
  selected=[i for i in range(len(rows)) if stateful or i<768 or i%127==0]
  record.write_text('\n'.join(' '.join(map(str,[*rows[i],expected[i]])) for i in selected)+'\n')

im=NativeReference(data/'TFX.DAT');bounds=[];points=[];visible=[True]
def visibility(im):
 radius,z,y,x,out=struct.unpack('<5i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,20));bounds.extend([radius,x,y,z]);im.cpu.reg_write(r.UC_X86_REG_EAX,int(visible[0]));im.return_from(stack_bytes=20)
im.intercept(0xcbef0,'Supply separately verified sphere visibility, observing native midpoint/radius inputs.',visibility)
def enqueue(im):
 z,y,x=struct.unpack('<3i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,12));points.extend([x,y,z]);im.return_from(stack_bytes=12)
im.intercept(0x7b6cc,'Observe each Q8 trail sample; the actual pool is compared below.',enqueue)
rows=[];expected=[];samples=0
for case in range(8192):
 enabled=(0,1,2,255)[case%4];visible[0]=case%5!=0
 if case<256:
  previous=[0,0,0];current=[(-32768,-32767,-100,-20,-19,-10,-9,-1,0,1,9,10,19,20,100,32767)[case%16],0 if case<64 else (case%7-3),0]
 else:
  previous=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
  current=[wrap(v+rng.randrange(-1000,1001)) for v in previous] if case%7 else [rng.randrange(-2147483648,2147483648) for _ in range(3)]
 rows.append(['S',enabled,int(visible[0]),*previous,*current]);im.write(0x8864,'<B',enabled);bounds.clear();points.clear()
 im.call(0x7b7fc,eax=current[0]&0xffffffff,edx=current[1]&0xffffffff,ebx=current[2]&0xffffffff,ecx=previous[0]&0xffffffff,stack=tuple(v&0xffffffff for v in previous[1:]),limit=300000)
 assert len(bounds) in (0,4)
 values=[int(bool(bounds)),*bounds,len(points)//3,*points];expected.append(digest(values));samples+=len(points)//3
compare(rows,expected,a.record_segments)
print(f'8192 complete original trail segment cases agree: {samples} samples, detail/visibility gates, native word distance, midpoint, signed IDIV spacing and wrapped-length loop quirks',flush=True)

im=NativeReference(data/'TFX.DAT');im.cpu.mem_map(0x300000,4096);base=0x300000;loaded=[];events=[];dead=[False]*200
im.intercept(0xc90ec,'Supply the fixed 200-record/2800-byte pool allocation.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,base),im.return_from()))
def resource(im):
 name=bytes(im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),32)).split(b'\0')[0].decode();loaded.append(name);im.cpu.reg_write(r.UC_X86_REG_EAX,len(loaded));im.return_from()
im.intercept(0xb4d98,'Supply unique symbolic smokecld handles for all 200 slots.',resource)
def model(im):
 slot=im.cpu.reg_read(r.UC_X86_REG_EAX)-1;assert 0<=slot<200 and im.cpu.reg_read(r.UC_X86_REG_EDX)==0
 dead[slot]=False;events.extend([0,slot,*struct.unpack('<3i',im.cpu.mem_read(base+slot*14,12))]);im.return_from()
im.intercept(0xb52d4,'Observe each newly sampled slot/model reset and already-written Q8 record.',model)
im.intercept(0xb6e88,'Supply each independent model destroyed flag; pool cleanup executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,int(dead[im.cpu.reg_read(r.UC_X86_REG_EAX)-1])),im.return_from()))
def draw(im):
 slot=im.cpu.reg_read(r.UC_X86_REG_EAX)-1;events.extend([1,slot,*[wrap(im.cpu.reg_read(reg)) for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]]);im.return_from()
im.intercept(0xb4ff0,'Observe native Q16 drawing inputs before the independent model/projector consumer.',draw)
def active():
 result=[];seen=set()
 if not im.read(0x128c4,'<B')[0]:
  pointer=im.read(0x128b8,'<I')[0];end=im.read(0x128c0,'<I')[0]
  while True:
   slot=(pointer-base)//14;assert 0<=slot<200 and slot not in seen;seen.add(slot)
   result.append([slot,*struct.unpack('<3i',im.cpu.mem_read(pointer,12))]);pointer+=14
   if pointer==base+2800:pointer=base
   if pointer==end:break
 assert im.read(0x5d7c,'<H')[0]==len(result)
 return result
rows=[];expected=[]
for case in range(4096):
 events.clear()
 if case==0:
  im.call(0x7b624);assert loaded==['smokecld']*200;row=['R']
 elif case<1024 or case%5 not in (0,1):
  enabled=1 if case<1024 else (0,1,2,255)[case%4]
  position=[rng.randrange(-100000,100001) for _ in range(3)] if case%17 else [rng.randrange(-2147483648,2147483648) for _ in range(3)]
  row=['P',enabled,*position];im.write(0x8864,'<B',enabled);im.call(0x7b6cc,stack=tuple(v&0xffffffff for v in reversed(position)))
 elif case%5==1:
  row=['T']
  if active():im.call(0x7b690)
 else:
  current=active();head=current[0] if current else [0,0,0,0]
  reference=[word(v>>8) for v in head[1:]]
  if case%7==0:reference[0]+=rng.choice((8000,8001,-8000,-8001,32768))
  if case%37==0:reference=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
  killed=([head[0]] if current and case%3==0 else [])+[rng.randrange(200) for _ in range(case%4)]
  for slot in killed:dead[slot]=True
  row=['D',*reference,len(killed),*killed]
  for at,v in zip((0x13424,0x13430,0x1343c),reference):im.write(at,'<i',v)
  im.call(0x7b744,limit=1000000)
 records=active();values=[len(records),*[v for item in records for v in item],len(events),*events];rows.append(row);expected.append(digest(values))
compare(rows,expected,a.record_pool,stateful=True)
print('4096 complete original smoke-pool operations agree: all 200 model loads, slot reuse, Q8 records, Q16 queued poses, model reset order, draw-before-cleanup and consecutive expired/distant-prefix retirement',flush=True)

# Capture the real post-motion caller up to the ground-impact boundary.
# A nonplayer target suppresses the independently checked warning outputs.
im=NativeReference(data/'TFX.DAT');im.cpu.mem_map(0x300000,4096);shot=0x300000;requests=[];distance=[0]
im.cpu.mem_write(shot+6,b'\x01')
im.intercept(0x7d208,'Supply the separately checked player-distance query; retain the original caller gates.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,distance[0]&0xffffffff),im.return_from(stack_bytes=4)))
def requested(im):
 old_y,old_z=struct.unpack('<2i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,8))
 requests.extend([wrap(im.cpu.reg_read(r.UC_X86_REG_ECX)),old_y,old_z,*[wrap(im.cpu.reg_read(reg)) for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]]);im.return_from(stack_bytes=8)
im.intercept(0x7b7fc,'Observe real current/previous world-word arguments after the complete post-motion trail gates.',requested)
im.intercept(0xa33c9,'Stop before the separately compared ground-impact phase.',lambda im:im.cpu.reg_write(r.UC_X86_REG_EIP,im.RETURN))
rows=[];expected=[]
for case in range(8192):
 flags=(0,1,2,3,0x81,0x201)[case%6];enabled=(0,1,2,255)[case//6%4];motion=case//24%13
 distance[0]=(-2147483648,-1,0,1,1999,2000,3999,4000,4001,7999,8000,2147483647)[case//312%12]
 previous=[rng.randrange(-2147483648,2147483648) for _ in range(3)];current=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 row=['C',flags,enabled,motion,distance[0],*previous,*current];rows.append(row)
 im.cpu.mem_write(shot+8,struct.pack('<6i',*current,*previous));im.cpu.mem_write(shot+60,struct.pack('<I',im.native(CALLBACKS[motion]) if motion else 0));im.write(0xe774,'<H',flags);im.write(0x809c+48+43,'<B',enabled);im.cpu.reg_write(r.UC_X86_REG_ESI,shot);requests.clear();im.call(0xa32a6)
 assert len(requests) in (0,6);expected.append(digest([int(bool(requests)),*requests]))
compare(rows,expected,a.record_dispatch)
print('8192 original post-motion trail dispatches agree: world/weapon flags, all 13 callbacks, strict 4000-unit boundary and exact Q8-to-world-word handoff',flush=True)
