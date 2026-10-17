#!/usr/bin/env python3
"""Compare the complete original projectile contact pass's terrain-credit path.

Geometry/SSD fatal observations and absent air/mobile hits are supplied. The
full 0xa373c pass, target-cell search, authorization gates, counters, audio and
radio ordering execute. Generic debris is a declared output boundary.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0xa373c)
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
# 0x75940 clears its active-shot pointer by passing zero, then reads owner at
# flat address 0x4b. Supply zeroed DOS low memory; that cleared owner is unused
# by the following terrain credit path. Keep the original helper unmodified.
im.cpu.mem_map(0,4096)
head,tail,shot=0x300000,0x300100,0x300200
events=[];terrain=[0,0,0]
im.intercept(0xb752c,'Supply the swept projectile source; motion and SSD query geometry have separate captures.',lambda im:im.return_from(stack_bytes=12))
for address in (0xa3504,0xa3678):im.intercept(address,'Supply no player or decoy contact before the terrain query.',lambda im:im.return_from())
im.intercept(0x7595c,'Supply no aircraft/mobile victim; their complete credit handlers are independently checked.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
im.intercept(0xb0d80,'Supply the terrain cell handle or native missing-definition sentinel.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,2 if terrain[0] else 65535),im.return_from()))
im.intercept(0xb6e88,'Supply intact projectile and the pre/post-query terrain destroyed state.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,terrain[1] if im.cpu.reg_read(r.UC_X86_REG_EAX)==2 else 0),im.return_from()))
def contact(im):terrain[1]=terrain[2];im.return_from(stack_bytes=4)
im.intercept(0xb0cbc,'Supply the terrain SSD collision result; all new-destruction and authorization tests execute.',contact)
im.intercept(0xb1334,'Resolve Arcade/training variables to supplied parser values.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300500 if im.cpu.reg_read(r.UC_X86_REG_EAX)==im.data+0x3674 else 0x300504),im.return_from()))
im.intercept(0xa5a9c,'Capture the original music request at its output boundary.',lambda im:(events.extend([0,im.cpu.reg_read(r.UC_X86_REG_EAX)]),im.return_from()))
def sample(im):
 sp=im.cpu.reg_read(r.UC_X86_REG_ESP);priority=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0];cursor=sp+8;ids=[]
 while True:
  pointer=struct.unpack('<I',im.cpu.mem_read(cursor,4))[0];cursor+=4
  if not pointer:break
  assert len(ids)<8 and (pointer-im.data-0x9860)%26==0
  ids.append((pointer-im.data-0x9860)//26)
 events.extend([1,priority,len(ids),*ids]);im.return_from()
im.write(0xac74,'<I',im.native(0x75954))
im.intercept(0x75954,'Capture actual sample descriptor lists and priorities.',sample)
def radio(im,persistent):
 offset=im.cpu.reg_read(r.UC_X86_REG_EAX)-im.data
 assert offset==(0x3764 if persistent else 0x370c),hex(offset)
 events.extend([3 if persistent else 2,int(persistent)]);im.return_from()
im.intercept(0x81198,'Capture the exact ordinary training-warning text.',lambda im:radio(im,False))
im.intercept(0x81254,'Capture the exact persistent unauthorized-target orders message.',lambda im:radio(im,True))
im.intercept(0x7b144,'Generic blast/debris output is outside the terrain-credit comparison.',lambda im:im.return_from())
rows=[];expected=[];fixtures=[]
for case in range(8192):
 x=rng.choice((-1,0,1,7,199,200,255));z=rng.choice((-1,0,1,17,199,200,255));weapon=case%27;player=(case>>1)&1;arcade=(case>>2)&1;training=(case>>3)&1
 present=0 if case%11==0 else 1;before=1 if case%7==0 else 0;after=0 if case%5==0 else 1;violations=rng.choice((-32768,-1,0,1,32767));count=rng.randrange(10)
 targets=[(rng.choice((-1,0,10,199,200))*2048+rng.randrange(2048),-rng.randrange(1000),rng.choice((-1,0,20,199,200))*2048+rng.randrange(2048))for _ in range(count)]
 if count and case&1:targets[rng.randrange(count)]=(x*2048+rng.randrange(2048),-rng.randrange(1000),z*2048+rng.randrange(2048))
 row=[x,z,weapon,player,arcade,training,present,before,after,violations,count,*[v for target in targets for v in target]];rows.append(row)
 im.cpu.mem_write(head+52,struct.pack('<I',shot));im.cpu.mem_write(shot,bytes(80));im.cpu.mem_write(shot+52,struct.pack('<I',tail));im.cpu.mem_write(shot+6,bytes([weapon]));im.cpu.mem_write(shot+8,struct.pack('<6i',x*524288+262144,-25600,z*524288+262144,x*524288+262144,-30000,z*524288+262144));im.cpu.mem_write(shot+46,struct.pack('<H',1));im.cpu.mem_write(shot+75,struct.pack('<I',im.data+0x10f28 if player else 0))
 for at,fmt,value in [(0x16e80,'<I',head),(0x16e7c,'<I',tail),(0xe762,'<H',0),(0xe768,'<H',1),(0xe774,'<B',0),(0xe75c,'<h',violations),(0x11b22,'<h',count)]:im.write(at,fmt,value)
 im.cpu.mem_write(0x300500,struct.pack('<2i',arcade,training))
 for index,target in enumerate(targets):im.write(0x5c40+index*26,'<3i',*target)
 terrain[:]=[present,before,after];events.clear();im.call(0xa373c)
 value=[im.read(0xe75c,'<h')[0],len(events),*events];expected.append(value)
 if case<512:fixtures.append(row+value)
result=subprocess.check_output([str((a.build/'terrain_credit_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
print('8192 complete original projectile terrain-credit passes agree: exact authored cells, missing/already destroyed/intact cells, ownership, all weapons, Arcade/training, signed violations, and ordered music/sample/radio output')
