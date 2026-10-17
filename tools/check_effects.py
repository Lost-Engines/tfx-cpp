#!/usr/bin/env python3
"""Compare complete original temporary-effect pool allocation and reuse.

Resource allocation, SSD reset and audio delivery are observed boundaries.
Original initialization, both linked lists, slot/model choice, word positions,
oldest-first traversal and reuse execute unchanged.
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
a=p.parse_args();rng=random.Random(0x7b144)
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
names=['hit','miss','splash','boom','clatter','can_spsh','can_hit','can_miss','crash','fireball'];loaded=[];handles={};events=[]
def resource(im):
 name=bytes(im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),32)).split(b'\0')[0].decode();index=len(loaded);loaded.append(name);handles[index+1]=(index//10,names.index(name));im.cpu.reg_write(r.UC_X86_REG_EAX,index+1);im.return_from()
im.intercept(0xb4d98,'Allocate a unique symbolic SSD handle for every slot/model resource.',resource)
def model(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EDX)==0
 slot,kind=handles[im.cpu.reg_read(r.UC_X86_REG_EAX)];events.extend([1,slot,kind]);im.return_from()
im.intercept(0xb52d4,'Record the selected SSD reset; its own animation has separate VM comparisons.',model)
def sample(im):
 priority,descriptor,end=struct.unpack('<3I',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,12));assert end==0
 events.extend([0,priority,(descriptor-im.data-0x9860)//26]);im.return_from()
im.write(0xac74,'<I',im.native(0x75954));im.intercept(0x75954,'Capture the original normal cannon-hit sample descriptor.',sample)
rows=[];expected=[];fixtures=[]
for case in range(8192):
 if case==0 or case%1024==0:
  loaded.clear();handles.clear();events.clear();im.call(0x7afa4)
  assert loaded==['miss','hit','splash','boom','clatter','can_miss','can_hit','can_spsh','crash','fireball']*100
  row=['R']
 else:
  position=[rng.choice([-2147483648,-65537,-32768,-1,0,32767,32768,65535,65536,2147483647,rng.randrange(-2147483648,2147483648)])for _ in range(3)];kind=case%10;row=['S',*position,kind]
  im.cpu.mem_write(0x300000,struct.pack('<3i',*position));events.clear();im.call(0x7b144,eax=0x300000,edx=kind)
 values=[];pointer=im.read(0x127cc,'<I')[0];seen=set()
 while pointer:
  assert pointer not in seen and len(seen)<100;seen.add(pointer)
  slot=(pointer-im.data-0x11b44)//32;body=bytes(im.cpu.mem_read(pointer,32));handle=struct.unpack_from('<H',body,6)[0];owner,kind=handles[handle];assert owner==slot
  values.extend([slot,kind,*struct.unpack_from('<3h',body)]);pointer=struct.unpack_from('<I',body,28)[0]
 values=[len(values)//5,*values,len(events),*events];digest=14695981039346656037
 for value in values:
  for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 rows.append(row);expected.append(digest)
 if case<768:fixtures.append(row+[digest])
result=subprocess.check_output([str((a.build/'effects_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert int(line)==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
print('8192 complete original temporary-effect pool operations agree: 1000 independent slot/model loads, all ten kinds, signed word positions, ordered SSD/audio requests, oldest-first traversal, repeated reuse and reset')
