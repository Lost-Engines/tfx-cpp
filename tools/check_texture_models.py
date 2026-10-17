#!/usr/bin/env python3
"""Compare complete textured model programs, projection and optional near clip.

Original resource/UV conversion, absolute vertices, projection, global texture
binding, opcode 47, near dispatcher and VGA texture raster execute. Model bytes,
identity basis, zero translation, declared diagnostic atlas and remap are inputs.
Only the supplied atlas handle is resolved externally. This is not a complete
retail-texture or world-session capture.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=512);p.add_argument('--near',action='store_true');p.add_argument('--record',type=Path);a=p.parse_args()
def initialise():
 image=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(image,aperture=0xa0000);image.cpu.mem_map(0x300000,0x20000);code=lambda off:image.native(0x70aa4+off)
 image.cpu.emu_start(image.native(0xb9110),image.native(0xb9133),count=10000)
 for file in (0xb9447,0xb944d,0xb9452,0xbc3ef,0xbc3fd,0xbc40b):image.cpu.mem_write(image.native(file),bytes(4))
 image.cpu.mem_write(code(0x47c6e),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767));image.cpu.mem_write(code(0x47cea),bytes(image.cpu.mem_read(code(0x68106),4)));image.cpu.mem_write(code(0x47c84),struct.pack('<H',42));image.cpu.mem_write(0x310000,bytes((u*3+v*5+(u^v))&255 for v in range(256) for u in range(256)))
 def resolve(im):
  assert im.cpu.reg_read(r.UC_X86_REG_EAX)&65535==42
  im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000);im.return_from()
 image.intercept(0xc85a0,'Resolve supplied diagnostic atlas handle 42; model binding, UV conversion and all drawing helpers execute.',resolve);return image,video
im,vga=initialise();code=lambda off:im.native(0x70aa4+off);rng=random.Random(0xbc3d1);rows=[]
for case in range(a.cases):
 count=3 if case%3==0 else 4;depth=rng.randrange(200,1600);points=[(-500,-350),(500,-350),(500,350),(-500,350)] if count==4 else [(-500,-350),(500,-350),(0,350)]
 if case%11==0:points.reverse()
 row=[case%2,count,rng.randrange(256)]
 for i,(x,y) in enumerate(points):
  z=rng.choice((-1000,-1,0,31,32,33,34,35,1000,32767)) if a.near else depth
  row.extend([x+rng.randrange(-100,101),y+rng.randrange(-100,101),z,rng.randrange(2,250),rng.randrange(2,185)])
 rows.append(row)
def program(row):
 wide,count,offset=row[:3];source=bytearray(50)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 for at,value in ((2,32767),(34,14),(48,65535)):struct.pack_into('>H',source,at,value)
 emit([48,1])
 for i in range(count):emit([98,i,*row[3+i*5:6+i*5]])
 emit([97,count,0,71,0,count])
 for i in range(count):emit(row[6+i*5:8+i*5])
 emit([47,count,*range(count),0,65535]);return bytes(source)
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_texture_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[];undefined=painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,count,offset=row[:3];im.cpu.mem_write(0x300000,program(row));im.call(0xb9f3f,stack=(0x300000,));im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(code(0x47cce),bytes(im.cpu.mem_read(code(0x47cc6),4)));im.cpu.mem_write(code(0x47cda),bytes(im.cpu.mem_read(code(0x47cd2),4)));im.cpu.mem_write(code(0x47ce6),bytes(im.cpu.mem_read(code(0x47cde),4)));im.cpu.mem_write(0x30f000,bytes((i*5+offset)&255 for i in range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x30f000));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300032);vga.reset(99)
 try:im.call(0xbb2aa,limit=3000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':raise
  undefined+=1;im,vga=initialise();continue
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined original frame',row);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[0]==digest;painted+=any(v!=99 for v in want)
 if case<96 or case%31==0:fixtures.append(row+[digest])
 if case and case%128==0:print(f'Checked {case} complete textured-model frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete original textured-model frames agree; {painted} nonempty, {undefined} native division faults excluded: actual converter, projection, global atlas binding, UV state, '+('near dispatch/clipping, ' if a.near else '')+'palette lookup and all VGA pixels.')
