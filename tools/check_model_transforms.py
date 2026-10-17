#!/usr/bin/env python3
"""Compare complete rotated, queued model frames with original 2.05 VGA.

The resource converter, queue constructor/flush, component matrix generator,
view/body composition, model bytecode, scale, projection, near clip and raster
execute. Only resolution of the supplied model handle is intercepted. Camera
matrix/cache, Euler angles, source model and identity remaps are inputs. These
absolute-vertex programs do not establish model-local articulation fidelity.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--gouraud',action='store_true',help='verify forced-flat shadows of authored Gouraud model faces')
p.add_argument('--shadow',action='store_true',help='exercise the original flattened black ground-shadow constructor')
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path)
a=p.parse_args();assert not a.gouraud or a.shadow;im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
im.cpu.mem_write(im.data+0x24c9c,bytes(range(256))*16);im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.call(0xc54f6,stack=(9,))
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==77
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000);image.return_from()
im.intercept(0xc8568,'Resolve supplied converted model 77; original queue, matrix construction, bytecode and VGA execute.',resolve)
def model(vertices,scale):
 data=bytearray(50)
 def put(at,value):struct.pack_into('>H',data,at,value&65535)
 def emit(words):data.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 put(0,32768);put(2,32767);put(34,14);put(48,65535);emit([48,scale])
 for i,v in enumerate(vertices):emit([98,i,*v])
 emit([97,3,0]);emit([76,0xc0cf,0xc700,77,0,1,2,0,65535] if a.gouraud else [2,17,0,1,2,0,65535]);return bytes(data)
rng=random.Random(0xb972a);rows=[]
identity=[32767,0,0,0,32767,0,0,0,32767]
for case in range(a.cases):
 wide=case%2;scale=(1,2,5,10,400)[case%5];angles=[rng.randrange(65536) for _ in range(3)]
 if case%7==0:angles=[0,0,0]
 if case%11==0:angles=[0,(case%4)*16384,0]
 matrix=identity if case<16 else [rng.randrange(-32768,32768) for _ in range(9)]
 origin=[rng.randrange(-1<<22,1<<22),rng.randrange(-1<<22,1<<22),rng.randrange(18<<16,1500<<16)]
 vertices=[[rng.randrange(-800,801) for _ in range(3)] for _ in range(3)]
 if case%13==0:vertices[2]=list(vertices[1])
 rows.append([wide,scale,(1,255,2,254,3,253,127,128)[case%8],*angles,*matrix,*origin,*[v for point in vertices for v in point]])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_transform_probe').resolve())]+(['--shadow'] if a.shadow else [])+(['--shaded'] if a.gouraud else [])
actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000
fixtures=[];undefined=0;painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,scale,draw_scale=row[:3];angles=row[3:6];matrix=row[6:15];origin=row[15:18];vertices=[row[i:i+3] for i in range(18,27,3)]
 im.cpu.mem_write(0x300000,model(vertices,scale));im.call(0xb9f3f,stack=(0x300000,))
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199))
 im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f)
 im.cpu.mem_write(0x300600,struct.pack('<3i',*origin));im.cpu.mem_write(0x300620,bytes(16));im.cpu.mem_write(0x300640,struct.pack('<3H',*angles))
 im.call(0xc488d);im.call(0xcc238 if a.shadow else 0xcc164,stack=(draw_scale,0x300640,0x300600,0x300620,77));vga.reset(99)
 try:im.call(0xc49d9,limit=3000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':raise
  undefined+=1;continue # Original word-IDIV overflow has no completed native frame.
 assert not line.endswith('overflow'),(case,'C++ declined a completed original frame',row)
 want=bytes(vga.pixels());painted+=any(pixel!=99 for pixel in want);got=pixels[case*64000:(case+1)*64000];basis=list(struct.unpack('<9h',im.cpu.mem_read(code(0x47c6e),18)));digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 assert list(map(int,line.split()))[:9]==basis,(case,'basis',row,line,basis)
 if want!=got:
  diff=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y];raise AssertionError((case,row,len(diff),diff[:20]))
 if case<128 or case%31==0:fixtures.append(row+[*basis,digest])
 if case and case%256==0:print(f'Checked {case} complete rotated model frames',flush=True)
print(f'Nonempty native frames: {painted}')
if undefined:print(f'Excluded {undefined} original IDIV-overflow inputs: native frame does not return')
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete native queued '+('shadow' if a.shadow else 'rotated-model')+f' frames and all nine Q15 basis words agree: conversion, component generation, wrapped view composition, cached translation/scale, bytecode, near clipping and every VGA pixel')
