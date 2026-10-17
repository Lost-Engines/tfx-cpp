#!/usr/bin/env python3
"""Compare original per-viewport jitter save/restore through C488D.

The animation gate, initial seed and post-draw working seeds are supplied
boundaries. This checks reset scheduling/state, not vertex consumption, whose
native BC114/BC13A comparison remains in check_native.py.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=256);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');at=im.native(0x70aa4+0x4862e);rng=random.Random(0xc48a3);rows=[]
for case in range(a.cases):
 row=[rng.randrange(65536),rng.randrange(65536),64]
 for step in range(64):row.extend([int((step%7)%3!=0) if case<16 else rng.randrange(2),rng.randrange(65536),rng.randrange(65536)])
 rows.append(row)
actual=subprocess.check_output([str((a.build/'model_jitter_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);fixtures=[]
for case,(row,line) in enumerate(zip(rows,actual)):
 x,y,count=row[:3];im.cpu.mem_write(at,struct.pack('<4H',x,y,x,y));digest=14695981039346656037
 for step in range(count):
  enabled,x,y=row[3+step*3:6+step*3];im.write(0xac90,'<B',enabled);im.call(0xc488d)
  for byte in im.cpu.mem_read(at+4,4):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  im.cpu.mem_write(at+4,struct.pack('<2H',x,y))
 assert int(line)==digest,(case,row[:20],line,digest)
 if case<16 or case%37==0:fixtures.append(row+[digest])
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} persistent sequences / {sum(row[2] for row in rows)} original viewport resets agree: tick-gated seed snapshots, intervening draw consumption and repeated main/instrument passes')
