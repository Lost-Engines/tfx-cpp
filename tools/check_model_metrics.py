#!/usr/bin/env python3
"""Compare native cached range, priority, fade row and complete detail selection.

Original header conversion, CC0BF queue insertion, BA98D range and header
selection execute. Model-handle resolution supplies the declared resource;
selected polygon/point raster entries are observed boundaries, not replaced
selection logic. --corpus checks all retail model headers at their thresholds.
"""
import argparse
from pathlib import Path
import json
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--corpus',action='store_true')
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,0x40000);rng=random.Random(0xba98d)
code=lambda off:im.native(0x70aa4+off)
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==77
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000);image.return_from()
im.intercept(0xc8568,'Resolve the declared converted model handle; native queue, metric and selector instructions still execute.',resolve)
selected=None;selected_index=-1
kinds={0xbaa21:0,0xbb021:2,0xbb094:3}
for file,kind in kinds.items():
 def observe(image,kind=kind):
  global selected
  pointer=image.cpu.reg_read(r.UC_X86_REG_ESI);selected=(kind,pointer-0x300000,image.cpu.mem_read(pointer,1)[0] if kind>=2 else 0);image.return_from()
 im.intercept(file,'Stop at the selected representation raster; range and complete header dispatch have already executed.',observe)
def index(cpu,address,size,unused):
 global selected_index
 selected_index=(cpu.reg_read(r.UC_X86_REG_ESI)-0x300000-20)//2
im.cpu.hook_add(UC_HOOK_CODE,index,begin=im.native(0xba9fe),end=im.native(0xba9fe))
if a.corpus:
 im.intercept(0xb9fd1,'Polygon instruction conversion is outside this header-selector comparison; original header and distant-colour conversion still execute, and polygon payloads are never drawn.',lambda image:image.return_from())
im.call(0xc54f6,stack=(9,));im.cpu.mem_write(0x33f020,bytes(16))
def synthetic(bias,minimum,records):
 raw=bytearray(48)
 def store(at,value):struct.pack_into('>H',raw,at,value&65535)
 store(0,minimum);store(16,bias)
 for i,(distance,kind,colour) in enumerate(records):
  field=34+i*2;store(2+i*2,distance);store(18+i*2,kind);store(field,len(raw)-field)
  raw.extend(struct.pack('>3H',65535,0,65535) if kind<=1 else struct.pack('>H',colour))
 return bytes(raw)
rows=[];models={}
if a.corpus:
 source=(a.research/'analysis/models/data.js').read_text();catalog=json.loads(source[source.index('=')+1:].strip().removesuffix(';'))['models']
 for model in catalog:
  key=int(model['id'],16);raw=(a.research/'extracted/cd_1994_09/resources'/model['path']).read_bytes();models[key]=raw
  distances={0,1,100,32766,32767}
  for detail in model['detail_records']:
   distances.update(max(0,min(32767,detail['distance']+delta)) for delta in (-1,0,1))
  for distance in sorted(distances):rows.append(([key,0,0,distance*65536],key))
  for _ in range(4):rows.append(([key,*[rng.randrange(-2147483648,2147483648) for _ in range(3)]],key))
else:
 for case in range(8192):
  point=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
  if case<128:point=[0,0,(case-64)*(1<<25)]
  count=rng.randrange(1,8);distances=sorted(rng.sample(range(32767),count-1))+[32767];bias=rng.randrange(-32768,32768);minimum=rng.choice((-32768,-1024,-1,0,1,32767));records=[(distance,0 if i==0 else rng.choice((0,2,3)),rng.randrange(256)) for i,distance in enumerate(distances)]
  row=[*point,bias,minimum,count,*[v for record in records for v in record]];models[case]=synthetic(bias,minimum,records);rows.append((row,case))
command=[str((a.build/'model_metrics_probe').resolve())]+(['--corpus',str(a.research/'installs/cd_1994_09/TFX')] if a.corpus else [])
actual=subprocess.check_output(command,input=('\n'.join(' '.join(map(str,row)) for row,_ in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);converted={};fixtures=[]
for case,((row,key),line) in enumerate(zip(rows,actual)):
 raw=models[key];assert len(raw)<0x3e000
 if key not in converted:
  im.cpu.mem_write(0x300000,raw)
  if a.corpus:
   # Execute the actual header stage after the separate missing-model/padding
   # diagnostic, stopping before the converter epilogue. No polygon program is
   # required by the subsequent native selector capture.
   im.cpu.mem_write(im.STACK+8,struct.pack('<I',0x300000));im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK-32);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
   im.cpu.emu_start(im.native(0xb9f5a),im.native(0xb9f8a),count=1000000)
   assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0xb9f8a)
  else:im.call(0xb9f3f,stack=(0x300000,),limit=1000000)
  converted[key]=bytes(im.cpu.mem_read(0x300000,len(raw)))
 else:im.cpu.mem_write(0x300000,converted[key])
 point=row[1:4] if a.corpus else row[:3];im.cpu.mem_write(0x33f000,struct.pack('<3i',*point));im.call(0xc488d);im.call(0xcc0bf,stack=(0x33f000,0x33f020,77))
 order,=struct.unpack('<h',im.cpu.mem_read(code(0x50b6e),2));fade=im.cpu.mem_read(code(0x51396),1)[0]
 selected=None;selected_index=-1;im.cpu.reg_write(r.UC_X86_REG_ESI,0);im.call(0xba98d,limit=1000000)
 distance,=struct.unpack('<h',im.cpu.mem_read(code(0x47c80),2))
 kind,offset,colour=selected if selected else (-1,-1,0)
 # Native representations 0 and 1 share their draw entry; retain the table's
 # declared kind when the selected program entry is identical.
 if selected:kind=struct.unpack_from('>H',raw,18+selected_index*2)[0]
 expected=[distance,order,fade,selected_index,kind,offset,colour]
 assert list(map(int,line.split()))==expected,(case,row,line,expected)
 if not a.corpus and (case<128 or case%97==0):fixtures.append(row+expected)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete native model metric/detail submissions agree across {len(models)} resources: wrapped three-axis range, signed priority, fade row, exact thresholds, program offsets and authored point representations')
