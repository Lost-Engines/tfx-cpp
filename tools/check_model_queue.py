#!/usr/bin/env python3
"""Compare original bounded model queue allocation and complete draw orders.

C488D, every C4930 insertion/replacement and C48E1/C4750/C4824/C49D9 flush
execute. Payload records carry supplied numeric IDs; the final geometry and
post-draw notification callbacks are explicit no-op/observation boundaries.
The native minimum-word sentinel itself is excluded from priorities because
its insertion loop does not define a bounded array result for that value.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=512);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);im.cpu.mem_write(0x300000,b'\xc3');im.cpu.mem_write(0x300100,b'\xc3');code=lambda off:im.native(0x70aa4+off);im.cpu.mem_write(code(0x53c5e+40),struct.pack('<I',0x300000));im.cpu.mem_write(code(0x6812a),struct.pack('<I',0x300100));draws=[]
def observe(cpu,address,size,unused):
 slot=cpu.reg_read(r.UC_X86_REG_ESI);assert slot<348;draws.append(struct.unpack('<H',cpu.mem_read(code(0x5164e+slot*2),2))[0])
im.cpu.hook_add(UC_HOOK_CODE,observe,begin=0x300000,end=0x300000);rng=random.Random(0xc4930);rows=[];edge=(0,1,2,3,4,14,15,16,17,347,348,349,350,400,700)
for case in range(a.cases):
 count=edge[case] if case<len(edge) else rng.choice((rng.randrange(349),rng.randrange(340,400),rng.randrange(348,701)))
 if case%8==0:count=min(count,352);keys=[0]*count
 elif case%8==1:keys=[i-count//2 for i in range(count)]
 elif case%8==2:keys=[count//2-i for i in range(count)]
 elif case%8==3:keys=[-32767 if i%2 else 32767 for i in range(count)]
 elif case%8==4:keys=[rng.choice((-1,0,1)) for _ in range(count)]
 elif case%8==5:keys=[rng.randrange(-32767,32768) for _ in range(count)]
 elif case%8==6:keys=[rng.randrange(-30,31) for _ in range(count)]
 else:keys=[i%7-3 for i in range(count)]
 rows.append([count,*keys])
actual=subprocess.check_output([str((a.build/'model_queue_probe').resolve()),'--full'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);fixtures=[];submissions=drawn=0
for case,(row,line) in enumerate(zip(rows,actual)):
 count,*keys=row;im.call(0xc488d);expected=[]
 for index,key in enumerate(keys):
  slot,=struct.unpack('<H',im.cpu.mem_read(code(0x50b6a),2));assert slot<348;expected.append(slot);im.cpu.mem_write(code(0x5164e+slot*2),struct.pack('<H',index));im.cpu.mem_write(code(0x510de+slot),bytes([40]));im.call(0xc4930,eax=key&65535,limit=3000000)
 draws.clear();im.call(0xc48e1,limit=5000000);expected.extend([len(draws),*draws]);submissions+=count;drawn+=len(draws)
 got=list(map(int,line.split()));assert got==expected,(case,row[:20],next((i,x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y) if len(got)==len(expected) else (len(got),len(expected)))
 if case<len(edge) or case%67==0:
  digest=14695981039346656037
  for value in expected:
   for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(row+[digest])
 if case and case%64==0:print(f'Checked {case} complete native queue sequences',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete native queue sequences / {submissions} slot allocations / {drawn} draws agree, including signed priorities, duplicate keys, small/quick/insertion sorts, 348-slot replacement and final back-to-front delivery')
