#!/usr/bin/env python3
"""Compare native TFX projectile impact selection and ordered model/audio output.

Original 0xa33c9..0xa34a9 runs with supplied classifier results and caller-word
input. The real 100-slot effect allocator and normal sample helper execute.
0x75030 executes too: it is disabled by bit 1 in all retail TFX environments.
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
a=p.parse_args();rng=random.Random(0xa33c9)
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
definitions=subprocess.check_output([str((a.build/'projectile_impact_probe').resolve()),'--definitions',str(a.data_dir/'TFX.DAT')]).decode().splitlines()
assert len(definitions)==27
for index,line in enumerate(definitions):
 at=0xedaa4+0x809c+index*48
 assert list(map(int,line.split()))==[index,im.executable[at+29],int(im.executable[at+30]!=2)]

shot=0x300100;frame=0x300800;sampled=[-1];events=[];handles={};full=[False]
names=['hit','miss','splash','boom','clatter','can_spsh','can_hit','can_miss','crash','fireball']
def resource(im):
 name=bytes(im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),32)).split(b'\0')[0].decode();handle=len(handles)+1;handles[handle]=names.index(name);im.cpu.reg_write(r.UC_X86_REG_EAX,handle);im.return_from()
im.intercept(0xb4d98,'Supply independent symbolic SSD handles for the native effect pool.',resource)
im.intercept(0xb52d4,'Capture selected effect model reset; its stream execution is independently checked.',lambda im:(events.extend([1,handles[im.cpu.reg_read(r.UC_X86_REG_EAX)]]),im.return_from()))
def sample(im):
 priority,descriptor,end=struct.unpack('<3I',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,12));assert end==0
 events.extend([0,priority,(descriptor-im.data-0x9860)//26]);im.return_from()
im.write(0xac74,'<I',im.native(0x75954));im.intercept(0x75954,'Capture exact sample descriptors and priority, preserving the callback registers.',sample)
im.intercept(0x7da20,'Supply the independently compared framebuffer classifier result.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,sampled[0]&0xffffffff),im.return_from()))
for address in (0xa34a9,0xa34b8):im.intercept(address,'Stop at the declared post-impact boundary for fragment cases; full motion passes continue.',lambda im:None if full[0] else im.return_from())
im.call(0x7afa4);rows=[];expected=[];fixtures=[]
for case in range(8192):
 flags=rng.choice((0,1,0x41,0x81,0xc1,0x201));mode=rng.choice((0,1,2,2,3,13));weapon=case%27;player=(case>>1)&1;y=rng.choice((-2147483648,-257,-1,0,0,1,255,256,2147483647));previous=rng.choice((-32768,-1,0,1,2,5,6,7,32767));surface=rng.choice((-1,0,1,2,5,6,7))
 row=[flags,mode,weapon,player,y,previous,surface];rows.append(row)
 im.cpu.mem_write(shot,bytes(80));im.cpu.mem_write(shot+6,bytes([weapon]));im.cpu.mem_write(shot+8,struct.pack('<3i',1000000,y,2000000));im.cpu.mem_write(shot+75,struct.pack('<I',im.data+0x10f28 if player else 0));im.write(0x809c+weapon*48+30,'<B',mode);im.write(0xe774,'<H',flags);im.cpu.mem_write(frame-4,struct.pack('<i',previous));im.cpu.reg_write(r.UC_X86_REG_EBP,frame);im.cpu.reg_write(r.UC_X86_REG_ESI,shot);sampled[0]=surface;events.clear();im.call(0xa33c9)
 value=[struct.unpack('<h',im.cpu.mem_read(frame-4,2))[0],int(im.cpu.mem_read(shot+66,1)[0]),len(events),*events];expected.append(value)
 if case<512:fixtures.append(row+value)
result=subprocess.check_output([str((a.build/'projectile_impact_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
# A373c and A31cc use identical six-register prologues: the terrain-world local
# occupies the next motion pass's classifier slot. Check both retail world IDs.
full[0]=True;head,tail=0x300a00,0x300b00
for upper in (0,1):
 for high in (0,1):
  im.cpu.mem_write(head+52,struct.pack('<I',tail));im.write(0x16e80,'<I',head);im.write(0x16e7c,'<I',tail)
  im.write(0xe768,'<h',0);im.write(0xe766,'<h',1);im.write(0xe762,'<h',upper);im.write(0xe75a,'<h',-200);im.write(0xe760,'<h',-100);im.write(0x13430,'<i',-300 if high else -100)
  im.call(0xa373c)
  prior=struct.unpack('<h',im.cpu.mem_read(im.STACK-28,2))[0];assert prior==int(bool(upper and high))
  im.cpu.mem_write(head+52,struct.pack('<I',shot));im.cpu.mem_write(shot,bytes(80));im.cpu.mem_write(shot+6,b'\x04');im.cpu.mem_write(shot+8,struct.pack('<3i',1000000,0,2000000));im.cpu.mem_write(shot+52,struct.pack('<I',tail));im.cpu.mem_write(shot+60,struct.pack('<I',im.native(0xa2754)));im.cpu.mem_write(shot+64,struct.pack('<h',1));im.cpu.mem_write(shot+75,struct.pack('<I',im.data+0x10f28));im.write(0x809c+4*48+30,'<B',2);im.write(0x809c+4*48+43,'<B',0);im.write(0xe774,'<H',1);im.write(0x13476,'<H',0);events.clear();im.call(0xa31cc)
  assert events==[0,1,12],(upper,high,prior,events)
print('All 27 original weapon definitions agree in independent guidance category and impact-effects mode')
print('8192 original TFX projectile impacts agree: gates, nonsampling-mode retained classifier, cannon/ordinary models, exact sample order and retirement')
print('Four complete adjacent contact/motion passes establish base/upper world IDs 0/1 in the aliased classifier slot and their equivalent non-water sound decision')
