#!/usr/bin/env python3
"""Check every OSL note/effect row against original 16-bit decompression.

Original relocation 0xebe and row decoder 0x14fe execute unchanged. Instrument
uploads are an external device consumer, omitted from this resource-only check.
Packed masks, row sizes, cursor movement and decoded eight-byte channel cells
are retained in the comparisons; no source instructions/data are bundled.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
import struct
import subprocess
from unicorn import Uc,UC_ARCH_X86,UC_MODE_16,UC_HOOK_CODE
from unicorn import x86_const as r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path,help='record independently executed synthetic packed/unpacked rows')
a=p.parse_args();launcher=(a.research/'installs/cd_1994_09/TFX/START.EXE').read_bytes()
assert hashlib.sha256(launcher).hexdigest()=='c5a60c7791c971a872aaed1e19ef2638aab0b21eb1e039907b8d64eb8f8980d6'
resources=json.loads((a.research/'analysis/audio/music-renders.json').read_text())
paths=[a.research/'extracted/cd_1994_09/resources'/entry['source'] for entry in resources]
output=iter(subprocess.check_output([str((a.build/'osl_resource_probe').resolve()),*map(str,paths)]).decode().splitlines())
patterns=rows=0
for entry,path in zip(resources,paths):
 song=path.read_bytes();assert hashlib.sha256(song).hexdigest()==entry['music_sha256']
 c=Uc(UC_ARCH_X86,UC_MODE_16);c.mem_map(0,0x100000);c.mem_write(0x10000,launcher[0x3730:0x57b0]);c.mem_write(0x30000,song)
 def return_near(cpu,address,size,user):
  sp=cpu.reg_read(r.UC_X86_REG_SP);at=cpu.reg_read(r.UC_X86_REG_SS)*16+sp
  cpu.reg_write(r.UC_X86_REG_IP,int.from_bytes(cpu.mem_read(at,2),'little'));cpu.reg_write(r.UC_X86_REG_SP,(sp+2)&65535)
 c.hook_add(UC_HOOK_CODE,return_near,None,0x10fb9,0x10fb9)
 def call(ip,**registers):
  for name,value in [('CS',0x1000),('DS',0x1000),('ES',0x1000),('SS',0x5000),('SP',0xfff0),('AX',0),('BX',0),('CX',0),('DX',0),('DI',0),('SI',0),('BP',0),('EFLAGS',0x202)]:c.reg_write(getattr(r,'UC_X86_REG_'+name),value)
  for name,value in registers.items():c.reg_write(getattr(r,'UC_X86_REG_'+name),value)
  c.mem_write(0x5fff0,struct.pack('<H',0xff00));c.emu_start(0x10000+ip,0x1ff00,count=100000)
  assert c.reg_read(r.UC_X86_REG_IP)==0xff00,(path,hex(c.reg_read(r.UC_X86_REG_IP)))
 call(0xebe,BX=0x3000)
 count=struct.unpack_from('<H',song,0x26)[0];instruments=struct.unpack_from('<H',song,0x48+count*4)[0]
 assert list(map(int,next(output).split()))==[song[7],count,instruments]
 for index in range(count):
  at=struct.unpack_from('<I',song,0x48+index*4)[0]
  channels,orders,loop,number=[struct.unpack_from('<H',song,at+offset)[0] for offset in (0x12,0x14,0x10,0x4e)]
  expected=[channels,orders,loop,number,struct.unpack_from('<H',song,at+0x2a)[0],song[at+0x2c],song[at+0x2e]]
  assert list(map(int,next(output).split()))==expected,(path,index)
  assert list(map(int,next(output).split()))==list(song[at+0x16:at+0x26])+list(song[at+0x50:at+0x150])
  pointer=bytes(c.mem_read(0x30048+index*4,4))
  for pattern in range(number):
   original=struct.unpack_from('<I',song,at+0x150+pattern*4)[0]
   actual=list(map(int,next(output).split()))
   if not original:assert actual==[pattern,0,0,0];continue
   flags=struct.unpack_from('<H',song,original+2)[0];length=flags&(0xfff if flags&0x8000 else 0x7fff)
   c.mem_write(0x30000+at+0x50,bytes([pattern]));c.mem_write(0x10037,bytes(0x39));c.mem_write(0x10038,bytes([channels]));c.mem_write(0x10049,pointer)
   for channel in range(channels):
    channel_at=0x3c9+channel*21;c.mem_write(0x10000+channel_at,bytes(21));c.mem_write(0x10050+channel*2,struct.pack('<H',channel_at))
   checksum=14695981039346656037
   for row in range(length):
    call(0x14fe,SI=0x37)
    cells=b''.join(bytes(c.mem_read(0x103ca+channel*21,8)) for channel in range(channels))
    cursor=bytes(c.mem_read(0x10043,2))
    for byte in cells+cursor:checksum=((checksum^byte)*1099511628211)&0xffffffffffffffff
   offset=int.from_bytes(c.mem_read(0x10043,2),'little')
   assert actual==[pattern,length,offset,checksum],(path.name,index,pattern,actual,[pattern,length,offset,checksum],hex(flags))
   patterns+=1;rows+=length
if a.record:
 rng=random.Random(0x14fe);fixtures=[]
 for index in range(128):
  channels=1+index%16;stored=rng.randrange(channels+1);length=1+index%4
  flags=length if index%9==0 else 0x8000|((index%8)<<12)|length
  body=bytearray()
  for row in range(length):
   if not flags&0x8000:body.extend(rng.randbytes(128));continue
   types=[rng.randrange(4) for _ in range(stored)]
   mask=sum(kind<<(30-2*channel) for channel,kind in enumerate(types))
   size=max(1,(stored+3)//4) if flags&0x4000 else 4
   body.extend((mask>>((4-size)*8)).to_bytes(size,'little'))
   for kind in types:
    count=(0,2,2,4+(0 if flags&0x1000 else 3)+(0 if flags&0x2000 else 1))[kind]
    body.extend(rng.randbytes(count))
  c.mem_write(0x30000,bytes(0x400));c.mem_write(0x30150,struct.pack('<HH',0x400,0x3000))
  c.mem_write(0x30400,struct.pack('<HH',flags,stored)+body if flags&0x8000 else struct.pack('<H',flags)+body)
  c.mem_write(0x10037,bytes(0x39));c.mem_write(0x10038,bytes([channels]));c.mem_write(0x10049,struct.pack('<HH',0,0x3000))
  for channel in range(channels):
   channel_at=0x3c9+channel*21;c.mem_write(0x10000+channel_at,bytes(21));c.mem_write(0x10050+channel*2,struct.pack('<H',channel_at))
  checksum=14695981039346656037
  for row in range(length):
   call(0x14fe,SI=0x37)
   cells=b''.join(bytes(c.mem_read(0x103ca+channel*21,8)) for channel in range(channels))
   cursor=bytes(c.mem_read(0x10043,2))
   for byte in cells+cursor:checksum=((checksum^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(' '.join(map(str,[flags,channels,stored,len(body),*body,checksum,int.from_bytes(cursor,'little')])))
 a.record.write_text('\n'.join(fixtures)+'\n')
assert list(output)==[]
print(f'{len(resources)} OSL resources, {patterns} complete patterns and {rows} native note/effect rows agree, including every packed/unpacked cell and cursor boundary')
