#!/usr/bin/env python3
"""Compare complete original OSL FM callbacks and every OPL register write.

Only the physical OPL timer/status probe and port I/O are supplied. Native voice
allocation, patch uploads, note/bend tables and volume quantisation execute.
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
rng=random.Random(0x57b0);rows=[]
for index in range(4096):
 operation=0 if index%127==0 else rng.randrange(1,11)
 row=[operation,rng.randrange(16),rng.choice([0,rng.randrange(128)]),rng.randrange(128),rng.choice([0x2000,rng.randrange(65536)]),rng.randrange(128),rng.randrange(128),rng.randrange(128)]
 if operation==1:row[2]=rng.choice([0,rng.randrange(12,108)])
 if operation==2:row[2]=rng.randrange(12,108)
 if operation==6 and index%3==0:row[2]=row[6]
 if operation==10:row += [16,*rng.randbytes(16)]
 rows.append(row)
# Also cover every actual instrument payload in every FM resource, without
# depending on a name heuristic or the generated listening exports.
patches=0
for resource in json.loads((a.research/'analysis/audio/music-renders.json').read_text()):
 if resource['mode']!='adl':continue
 data=(a.research/'extracted/cd_1994_09/resources'/resource['source']).read_bytes()
 songs=struct.unpack_from('<H',data,0x26)[0];table=0x48+songs*4;count=struct.unpack_from('<H',data,table)[0]
 for index in range(count):
  pointer=struct.unpack_from('<I',data,table+2+index*4)[0]
  if not pointer:continue
  instrument=pointer+4
  if data[instrument+0x20]!=2:continue
  patch=data[instrument+0x2a:instrument+0x2a+16];assert len(patch)==16
  rows.append([10,0,index,0,0,0,0,0,len(patch),*patch]);patches+=1
output=subprocess.check_output([str((a.build/'osl_fm_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(output)==len(rows)
c=Uc(UC_ARCH_X86,UC_MODE_16);c.mem_map(0,0x100000);c.mem_write(0x20000,launcher[0x57b0:0x6890]);events=[]
opl={'address':0,'timer':False}
def read(cpu,port,size,user):return 0xc0 if port==0x388 and opl['timer'] else 0
def write(cpu,port,size,value,user):
 if port==0x388:opl['address']=value&255
 if port==0x389:
  events.extend([opl['address'],value&255])
  if opl['address']==4:opl['timer']=bool(value&1) and not bool(value&128)
c.hook_add(UC_HOOK_INSN,read,None,1,0,r.UC_X86_INS_IN)
c.hook_add(UC_HOOK_INSN,write,None,1,0,r.UC_X86_INS_OUT)
callbacks=[0x9d,0x47c,0x49b,0x597,0x5ff,0x625,0x627,0x6a9,0x707,0x709,0x70b]
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
print(f'{len(rows)} complete FM callbacks, {bytes_checked//2} OPL register writes and {patches} actual instrument uploads agree, including nine-voice allocation, pitch-table bends, volume quantisation and shared channel caches')
