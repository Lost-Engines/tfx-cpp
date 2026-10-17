#!/usr/bin/env python3
"""Compare original shadow height eligibility, fixed placement and visibility.

B6A44, matrix/camera setters, fixed query and native sphere admission execute.
The supplied SSD instance/definition, actor fixed position, global ground
height and camera are inputs. Shadow geometry submission is an observation
boundary; complete shadow raster has its own converted-model comparison.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off);rng=random.Random(0xb6a44);queries=[]
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==1
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300100);image.return_from()
im.intercept(0xc8568,'Resolve supplied SSD instance after shadow submission.',resolve)
im.intercept(0xcc238,'Observe completed placement/admission before the independently checked shadow geometry constructor.',lambda image:image.return_from(20))
def observe(cpu,at,size,unused):
 frame=cpu.reg_read(r.UC_X86_REG_EBP);queries.append([1,*struct.unpack('<3i',cpu.mem_read(frame-12,12)),int(bool(cpu.reg_read(r.UC_X86_REG_EAX)&255))])
im.cpu.hook_add(UC_HOOK_CODE,observe,begin=im.native(0xb6ac4),end=im.native(0xb6ac4))
rows=[];expected=[];fixtures=[]
for case in range(8192):
 wide=case%2;matrix=[32767,0,0,0,32767,0,0,0,32767] if case<128 else [rng.randrange(-32768,32768) for _ in range(9)];camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)];origin=[rng.randrange(-2147483648,2147483648) for _ in range(3)];y=(-32768,-1025,-1024,-1023,-1,0,1,32767)[case%8] if case<256 else rng.randrange(-2048,128);origin[1]=y*65536+rng.randrange(65536);ground=rng.randrange(-32768,32768);radius=rng.choice((-32768,-1,0,1,32767,rng.randrange(-32768,32768)));maximum=(319,199) if case%5 else (110,120);row=[wide,*matrix,*camera,159,99,*maximum,*origin,ground,radius]
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb94da,stack=(159,99,*maximum));im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f);im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)))
 im.cpu.mem_write(0x300000,bytes(64));im.cpu.mem_write(0x300002,struct.pack('<h',radius));im.cpu.mem_write(0x300100,bytes(64));im.cpu.mem_write(0x300119,struct.pack('<H',77));im.write(0x20b98,'<I',0x300000);im.write(0x20b9c,'<I',0x300100);im.write(0x20c4a,'<H',1);im.write(0x20bb0,'<3h',*[v>>16 for v in origin]);im.write(0x20b74,'<3i',*origin);im.write(0x20baa,'<3H',0,0,0);im.write(0xabf2,'<h',ground);im.write(0xac18,'<I',im.read(0xac1c,'<I')[0]);queries.clear();im.call(0xb6a44,eax=0)
 assert len(queries)<=1;value=queries[0] if queries else [0];rows.append(row);expected.append(value)
 if case<128 or case%97==0:fixtures.append(row+value)
actual=subprocess.check_output([str((a.build/'model_shadow_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,want) in enumerate(zip(actual,expected)):assert list(map(int,line.split()))==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 original shadow placements agree: height cutoff/equality, retained X/Z fractions, global signed ground height, wrapped fixed camera products, signed radius quirks and normal/wide viewport admission')
