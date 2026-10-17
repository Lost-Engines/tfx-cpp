#!/usr/bin/env python3
"""Compare mixed original immediate, deferred and shadow model delivery.

Original CBFEC/CC0BF/CC164/CC238 constructors, all queue allocation/replacement,
wrapped size-cache scaling and complete sorted flush execute. Supplied model
handles resolve to one zero-bias header; geometry header entries and post-draw
notification are observation boundaries. No original queue or size wrapper is
replaced. Draw records retain handles, cache, parameter bytes and Euler words.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=256);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);im.cpu.mem_write(0x300000,bytes(256));im.cpu.mem_write(0x300f00,b'\xc3');code=lambda off:im.native(0x70aa4+off);im.cpu.mem_write(code(0x6812a),struct.pack('<I',0x300f00));im.call(0xc54f6,stack=(9,));events=[]
def resolve(image):
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000);image.return_from()
im.intercept(0xc8568,'Resolve supplied model IDs to the same zero-sort-bias header; geometry is observed separately.',resolve)
def observe(image,tag):
 slot=image.cpu.reg_read(r.UC_X86_REG_ESI);assert slot<348
 handle=struct.unpack('<H',image.cpu.mem_read(code(0x5164e+slot*2),2))[0]
 cache=[struct.unpack('<I',image.cpu.mem_read(code(offset+slot*4),4))[0] for offset in (0x5212e,0x5269e,0x52c0e)]
 parameters=struct.unpack('<2I',image.cpu.mem_read(code(0x5317e+slot*8),8));used=struct.unpack('<2I',image.cpu.mem_read(code(0x47cb0),8))
 angles=[struct.unpack('<H',image.cpu.mem_read(code(offset+slot*2),2))[0] for offset in (0x51906,0x51bbe,0x51e76)] if tag else [0,0,0]
 events.extend([handle,tag,*cache,*parameters,*used,*angles]);image.return_from()
for file,tag in ((0xba98d,0),(0xbab39,1),(0xbace9,2)):
 im.intercept(file,'Observe geometry header after original constructor, copied payload, cache-size wrapper and queue dispatch.',lambda image,tag=tag:observe(image,tag))
rng=random.Random(0xcbfec);rows=[];edges=(0,1,2,3,14,15,16,17,347,348,349,350,400,700,700,700)
for case in range(a.cases):
 count=edges[case] if case<len(edges) else rng.randrange(300,701);row=[count]
 for i in range(count):
  mode=case%8
  kind=3 if mode==0 else 0 if mode==1 else (1 if i%2==0 else 3) if mode==2 else i%3 if mode in (3,4) and i<348 else 3 if mode==3 else 2 if mode==5 and i<count-1 else rng.randrange(4)
  key=0 if case%5==0 else i-count//2 if case%5==1 else rng.choice((-32767,32767)) if case%5==2 else rng.randrange(-30,31)
  if case%8 in (6,7) and i and i%113==0:kind=4
  row.extend([kind,key,(1,255,2,254,3,253,127,128)[i%8],int(i%3!=0)])
 rows.append(row)
actual=subprocess.check_output([str((a.build/'model_delivery_probe').resolve()),'--full'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);fixtures=[];total=draws=0
for case,(row,line) in enumerate(zip(rows,actual)):
 im.cpu.mem_write(code(0x514f2),bytes([255])*348);im.cpu.mem_write(code(0x47cb0),bytes(8));im.call(0xc488d);events.clear();expected=[]
 for i in range(row[0]):
  kind,key,scale,rotated=row[1+i*4:5+i*4];slot=struct.unpack('<H',im.cpu.mem_read(code(0x50b6a),2))[0]
  if kind==4:
   im.call(0xc48e1,limit=5000000);im.call(0xc488d);expected.extend([65535,0]);continue
  cache=[i*65537,(-i*63591)&4294967295,((key&65535)<<16)|((i*313)&65535)];angles=[(i*factor+1)&65535 for factor in (37,83,159)] if rotated else [0,0,0]
  im.cpu.mem_write(0x300100,struct.pack('<3I',*cache));im.cpu.mem_write(0x300120,bytes((i*11+j)&255 for j in range(8)));im.cpu.mem_write(0x300140,struct.pack('<3H',*angles))
  if kind==0:im.call(0xcc0bf,stack=(0x300100,0x300120,i+1),limit=3000000)
  else:im.call((0xcc164,0xcc238,0xcbfec)[kind-1],stack=(scale,0x300140,0x300100,0x300120,i+1),limit=3000000)
  size=struct.unpack('<H',im.cpu.mem_read(code(0x50b68),2))[0];expected.extend([slot,size])
 im.call(0xc48e1,limit=5000000);expected.extend([len(events)//12,*events]);total+=row[0];draws+=len(events)//12
 got=list(map(int,line.split()))
 if got!=expected:
  mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y),('length',len(got),len(expected)));raise AssertionError((case,row[:40],mismatch))
 if case<len(edges) or case%37==0:
  digest=14695981039346656037
  for value in expected:
   for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(row+[digest])
 if case and case%64==0:print(f'Checked {case} complete mixed delivery sequences',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} mixed native sequences / {total} submissions / {draws} delivered payloads agree: immediate scratch reuse, deferred types, repeated size-cache mutations, parameter/Euler snapshots, full-queue replacement and ordered flush')
