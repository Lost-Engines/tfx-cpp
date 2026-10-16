#!/usr/bin/env python3
"""Compare native player callback selection and pilot-state flag clearing.

The full original dispatch 0x8f8e2..0x8f98c executes its mode tables, guards and
frame-duration comparison. Selected callbacks are observed and returned from;
their numerical behavior has separate complete execution comparisons. This
capture checks selection only, not the flight routines behind the callbacks.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x8f918);selected=[]
for file,kind in ((0x8dc50,1),(0x8e280,2),(0x9fe14,3),(0x9fe50,4),(0x9feb4,5),(0x8e5a8,6),(0x8f198,7)):
 im.intercept(file,'Observe selected callback; its numerical behavior is outside this dispatch-only capture',lambda image,kind=kind:(selected.append(kind),image.return_from()))
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
cases=[]
for i in range(8192):cases.append([i%8,rng.choice([0,1,2,3,4,5,18,65535]),fbits(rng.choice([-1,0,3.999999,4,4.000001,18,float('inf'),float('nan')])),(i//8)%2,(i//16)%2,(i//32)%2,(i//64)%2])
output=subprocess.check_output([str((a.build/'player_dispatch_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];counts=[0]*8
for i,(row,line) in enumerate(zip(cases,output)):
 model,elapsed,limit,autopilot,landing,disabled,pilot=row
 for f,v,fmt in ((0x1347a,model,'<B'),(0x13476,elapsed,'<H'),(0x8774,limit,'<I'),(0x14958,autopilot,'<H'),(0x86cf,landing,'<B'),(0x86ce,disabled,'<B'),(0xe784,pilot,'<B')):im.write(f,fmt,v)
 selected.clear();im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x8f8e2),im.native(0x8f98c),count=10000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8f98c) and len(selected)<=1
 kind=selected[0] if selected else 0;expected=[kind,im.read(0x14958,'<H')[0],im.read(0x86cf,'<B')[0]];actual=list(map(int,line.split()));assert actual==expected,(i,row,actual,expected)
 counts[kind]+=1
 if i%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert all(count>20 for count in counts)
print(f'{len(cases)} original player dispatch cases agree across all {len(counts)} callback outcomes, duration/NaN boundaries and pilot-state flag clearing; numerical callbacks are declared observer boundaries')
