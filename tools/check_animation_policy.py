#!/usr/bin/env python3
"""Compare persistent original unconditional/visible/frozen animation paths.

B4F44, B4FF0 and B518C execute with real definition/instance resolution, fixed
camera query, native visibility and stream interpreter. Synthetic increment
streams, global animation gate, camera and actor positions are supplied inputs.
Only the single instance handle and post-query notification are supplied. The
empty drawing entry contains no geometry or intercepted animation helper.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=128);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off);im.cpu.mem_write(0x300f00,b'\xc3');im.write(0xac08,'<I',0x300f00)
for field,offset in ((0xabf4,0),(0xabf8,4),(0xabfc,8)):im.write(field,'<I',0x300800+offset)
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==1
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300400);image.return_from()
im.intercept(0xc8568,'Resolve the single supplied SSD instance; definition, animation, query and drawing-entry execution remain native.',resolve)
def definition(all_parameters):
 source=bytearray(14);source[1]=1;source[5]=int(all_parameters);source[8]=2;source[10]=2
 for parameter in range(8):source.extend(struct.pack('<6H',20+parameter,0,4,1,4,65534))
 source.extend(bytes(2));struct.pack_into('<H',source,12,(len(source)-12)//2);source.extend(bytes(2));return bytes(source)
rng=random.Random(0xb50e9);rows=[]
for case in range(a.cases):
 row=[case%2,64]
 for step in range(64):
  policy=step%3;enabled=int(step%5!=0);wide=(step//3)%2;matrix=[32767,0,0,0,32767,0,0,0,32767] if case<32 else [rng.randrange(-32768,32768) for _ in range(9)];camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)] if case>=16 else [0,0,0]
  depth=rng.choice((-32768,-1000,-1,0,15,16,17,18,100,500,1000,16000,16384,16385,32767));origin=[rng.randrange(-8000,8000)*65536+rng.randrange(65536),rng.randrange(-8000,8000)*65536+rng.randrange(65536),depth*65536+rng.randrange(65536)];radius=rng.choice((-32768,-1,0,1,32767,500));maximum=(110,120) if step%7==0 else (319,199)
  if case<8 and step%4==0:origin=[0,0,1000*65536];radius=500
  row.extend([policy,enabled,wide,*matrix,*camera,159,99,*maximum,*origin,radius])
 rows.append(row)
actual=subprocess.check_output([str((a.build/'animation_policy_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);fixtures=[]
for case,(row,line) in enumerate(zip(rows,actual)):
 all_parameters,count=row[:2];source=definition(all_parameters);im.cpu.mem_write(0x300000,source);im.cpu.mem_write(0x300400,bytes(64));im.cpu.mem_write(0x300400,struct.pack('<H',1));im.cpu.mem_write(0x300400+16+11,struct.pack('<8H',*([65535]*8)));im.write(0x1b254,'<I',0x300000);im.write(0x20b98,'<I',0x300000);im.write(0x20b9c,'<I',0x300400);im.write(0x20c4a,'<H',1);im.write(0x20ba0,'<I',im.native(0xb6c84));im.call(0xb54dc,eax=0x300000+14);im.cpu.mem_write(0x300400+16,bytes([250])*8);digest=14695981039346656037
 for step in range(count):
  op=row[2+step*23:2+(step+1)*23];policy,enabled,wide=op[:3];matrix=op[3:12];camera=op[12:15];ox,oy,hx,hy=op[15:19];origin=op[19:22];radius=op[22]
  im.call(0xca780)
  if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
  im.call(0xb94da,stack=(ox,oy,hx,hy));im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f);im.call(0xb9ab9,stack=tuple(v&4294967295 for v in reversed(camera)));im.write(0xac90,'<B',enabled);im.cpu.mem_write(0x300002,struct.pack('<h',radius))
  im.call((0xb4f44,0xb4ff0,0xb518c)[policy],eax=1,edx=origin[0]&4294967295,ebx=origin[1]&4294967295,ecx=origin[2]&4294967295)
  memory=bytes(im.cpu.mem_read(0x300400+16,29));values=memory[:8]+struct.pack('<8H',*[v*2 for v in struct.unpack_from('<8H',memory,11)])
  for byte in values:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 assert int(line)==digest,(case,row[:30],line,digest)
 if case<16 or case%13==0:fixtures.append(row+[digest])
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} persistent sequences / {sum(row[1] for row in rows)} native model calls agree: unconditional player updates, visibility-gated ordinary updates, frozen pose submission, global tick gate and primary/all-eight parameter streams')
