#!/usr/bin/env python3
"""Compare original Sound Blaster request priority, concatenation and cooldowns.

Complete 0xdcfa4, queue preparation and DSP/DMA command construction execute.
Sound Blaster reads report ready; writes are observed without a physical device.
A declared completion marks the whole previous stream idle. No selection,
cooldown, queue arithmetic or priority routine is replaced. PCM/effect synthesis
and actual hardware interrupt timing are outside this controller comparison.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_INSN
from unicorn import x86_const as r
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000,0x2000);im.cpu.mem_map(0x91000,0xf000)
im.write(0x25cc8,'<I',0x300000);im.write(0x20c70,'<I',0x2000);im.write(0x20c74,'<I',0x98000)
im.cpu.hook_add(UC_HOOK_INSN,lambda cpu,port,size,user:0,None,1,0,r.UC_X86_INS_IN)
im.cpu.hook_add(UC_HOOK_INSN,lambda cpu,port,size,value,user:None,None,1,0,r.UC_X86_INS_OUT)
queued=[];stops=[];starts=[]
im.intercept(0xdd22c,'Observe descriptor transfer into the native queue; queue preparation executes',lambda image:queued.append((image.cpu.reg_read(r.UC_X86_REG_EAX)-im.data-0x9860)//26))
im.intercept(0xdd4e0,'Observe old-stream stop; original hardware command construction executes',lambda image:stops.append(True))
im.intercept(0xdd46c,'Observe new-stream start; original hardware command construction executes',lambda image:starts.append(True))
rng=random.Random(0xdcfa4);rows=[]
for index in range(8192):
 sequence=[rng.randrange(6) for _ in range(rng.randrange(1,7))]
 header=[int(index%32==0),int(rng.randrange(10)!=0),rng.randrange(2),rng.choice([0,1,2,255]),rng.choice([0,1,2,18,50,65535]),rng.choice([0,1,2,3,255]),int(index%13==0),len(sequence)]
 definitions=[value for sample in range(6) for value in (rng.choice([0,1,10,50,32767,-1,-32768]),rng.choice([0,rng.randrange(1,500)]),int(rng.randrange(8)!=0))]
 rows.append(header+sequence+definitions)
payload='\n'.join(' '.join(map(str,row)) for row in rows)+'\n'
output=subprocess.check_output([str((a.build/'sample_scheduler_probe').resolve())],input=payload.encode()).decode().splitlines();assert len(output)==len(rows)
fixtures=[];counts={'starts':0,'interrupts':0,'rejected':0}
for index,(row,line) in enumerate(zip(rows,output)):
 reset,enabled,active,last,elapsed,priority,complete,count=row[:8];sequence=row[8:8+count];definitions=row[8+count:]
 if reset:
  im.cpu.mem_write(0x300000,bytes(512));im.cpu.mem_write(0x300002,struct.pack('<H',not active));im.cpu.mem_write(0x300016,struct.pack('<I',0x91000));im.write(0xdfa8,'<B',last)
  for sample in range(6):
   delay,size,available=definitions[sample*3:sample*3+3];at=0x9860+sample*26
   im.write(at,'<I',im.data+0x3874);im.write(at+4,'<HHIhIIHH',8363,delay&65535,0,0,size,0x92000+sample*1024,0,available)
  im.write(0x9860+6*26,'<I',0)
 if complete:im.cpu.mem_write(0x300002,struct.pack('<H',1))
 im.write(0xac85,'<B',enabled);im.call(0xc513c,eax=im.data+0x9860,edx=elapsed)
 queued.clear();stops.clear();starts.clear();im.call(0xdcfa4,stack=(priority,*(im.data+0x9860+sample*26 for sample in sequence),0),limit=1000000)
 accepted=[sample for sample in queued if im.read(0x9860+sample*26+14,'<I')[0]] if starts else []
 expected=[int(struct.unpack('<H',im.cpu.mem_read(0x300002,2))[0]==0),im.read(0xdfa8,'<B')[0],int(bool(stops)),int(bool(starts)),len(accepted)]+accepted+[im.read(0x9860+sample*26+12,'<h')[0] for sample in range(6)]
 actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
 counts['starts']+=bool(starts);counts['interrupts']+=bool(stops);counts['rejected']+=not starts and not stops
 if index<256:fixtures.append(' '.join(map(str,row+expected)))
assert all(counts.values()),counts
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(rows)} complete original sound requests/cooldown updates agree: priorities, disabled output, persistent signed timers, preemption, concatenated/empty/unavailable samples and completion; {counts}')
