#!/usr/bin/env python3
"""Compare original OSL LAPC-I device output and shared channel state.

Complete native device callbacks execute. MPU ready/acknowledgement reads and
actual port writes are supplied/observed; post-SysEx busy waiting is skipped.
No notes, controllers, running status, patch mapping or checksum code is replaced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn import Uc,UC_ARCH_X86,UC_MODE_16,UC_HOOK_CODE,UC_HOOK_INSN
from unicorn import x86_const as r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/START.EXE';launcher=path.read_bytes()
assert hashlib.sha256(launcher).hexdigest()=='c5a60c7791c971a872aaed1e19ef2638aab0b21eb1e039907b8d64eb8f8980d6'
rng=random.Random(0x7120);rows=[]
for index in range(4096):
 operation=0 if index%127==0 else rng.randrange(1,11)
 row=[operation,rng.randrange(16),rng.choice([0,rng.randrange(128)]),rng.randrange(128),rng.choice([0x2000,rng.randrange(65536)]),rng.randrange(128),rng.randrange(128),rng.randrange(128)]
 if operation==6 and index%3==0:row[2]=row[6]
 if operation==10:row += [244,*rng.randbytes(244)]
 rows.append(row)
# Also cover every actual instrument payload in every LA resource, without
# depending on a name heuristic or the generated listening exports.
patches=0
for resource in json.loads((a.research/'analysis/audio/music-renders.json').read_text()):
 if resource['mode']!='rld':continue
 data=(a.research/'extracted/cd_1994_09/resources'/resource['source']).read_bytes()
 songs=struct.unpack_from('<H',data,0x26)[0];table=0x48+songs*4;count=struct.unpack_from('<H',data,table)[0]
 for index in range(count):
  pointer=struct.unpack_from('<I',data,table+2+index*4)[0]
  if not pointer:continue
  instrument=pointer+4
  if data[instrument+0x20]!=4:continue
  patch=data[instrument+0x2a:instrument+0x2a+244];assert len(patch)==244
  rows.append([10,0,index,0,0,0,0,0,len(patch),*patch]);patches+=1
output=subprocess.check_output([str((a.build/'osl_la_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(output)==len(rows)
c=Uc(UC_ARCH_X86,UC_MODE_16);c.mem_map(0,0x100000);c.mem_write(0x20000,launcher[0x7120:0x7670]);events=[]
c.hook_add(UC_HOOK_INSN,lambda cpu,port,size,user:0xfe if port==0x330 else 0,None,1,0,r.UC_X86_INS_IN)
c.hook_add(UC_HOOK_INSN,lambda cpu,port,size,value,user:events.append(value&255) if port==0x330 else None,None,1,0,r.UC_X86_INS_OUT)
def skip_wait(cpu,address,size,user):
 sp=cpu.reg_read(r.UC_X86_REG_SP);at=cpu.reg_read(r.UC_X86_REG_SS)*16+sp
 cpu.reg_write(r.UC_X86_REG_IP,int.from_bytes(cpu.mem_read(at,2),'little'));cpu.reg_write(r.UC_X86_REG_SP,(sp+2)&65535)
c.hook_add(UC_HOOK_CODE,skip_wait,None,0x20173,0x20173)
callbacks=[0xa2,0x308,0x346,0x35f,0x372,0x380,0x393,0x3b0,0x3cf,0x3ea,0x421]
bytes_checked=0
for index,(row,line) in enumerate(zip(rows,output)):
 operation,channel,first,second,bend,note,volume,extra=row[:8]
 c.mem_write(0x18000,bytes(21));c.mem_write(0x18009,struct.pack('<H',bend));c.mem_write(0x18011,bytes([note,0,volume]));c.mem_write(0x1700f,bytes([first,second,extra]))
 for name,value in [('CS',0x2000),('DS',0x1000),('ES',0x2000),('SS',0x5000),('SP',0xfff0),('AX',0),('BX',channel|(first<<8)),('CX',second),('DX',0),('DI',0x8000),('SI',0x7000),('BP',channel),('EFLAGS',0x202)]:c.reg_write(getattr(r,'UC_X86_REG_'+name),value)
 if operation==10:
  c.mem_write(0x30000,bytes(row[9:]));c.reg_write(r.UC_X86_REG_BX,0x3000);c.reg_write(r.UC_X86_REG_DI,0);c.reg_write(r.UC_X86_REG_DX,first)
 events.clear();c.mem_write(0x5fff0,struct.pack('<HH',0xff00,0x1000));c.emu_start(0x20000+callbacks[operation],0x1ff00,count=1000000)
 assert c.reg_read(r.UC_X86_REG_IP)==0xff00,(index,hex(c.reg_read(r.UC_X86_REG_IP)))
 expected=[int.from_bytes(c.mem_read(0x18009,2),'little'),c.mem_read(0x18011,1)[0],c.mem_read(0x18013,1)[0],len(events),*events]
 actual=list(map(int,line.split()));assert actual==expected,(index,row[:8],actual,expected)
 bytes_checked+=len(events)
print(f'{len(rows)} complete LA callbacks and {bytes_checked} MIDI bytes agree: all notes/controllers, channel caches, running status, reset/reverb, patch/timbre mapping, checksums and {patches} original instrument uploads')
