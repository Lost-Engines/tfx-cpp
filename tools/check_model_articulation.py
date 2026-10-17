#!/usr/bin/env python3
"""Compare original nested model helpers and carried stores through VGA.

Native endian/load fixups, angle conversion, queue and outer body composition,
helper matrix/translation save/restore, shared vertex slots, projection and
flat raster execute. Model-handle resolution is the only substituted consumer.
Matrices/cache, model bytes, two anchors and helper angles are supplied inputs.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path);a=p.parse_args()
code=lambda off:im.native(0x70aa4+off)
def resolve(image):
 handle=image.cpu.reg_read(r.UC_X86_REG_EAX)&65535;assert handle in (77,88),hex(handle)
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000 if handle==77 else 0x304000);image.return_from()
observed=[]
def face(cpu,address,size,user):
 at=cpu.reg_read(r.UC_X86_REG_ESI);colour,*indices=struct.unpack('<4H',cpu.mem_read(at,8))
 for index in indices:observed.extend(struct.unpack('<3i',cpu.mem_read(code(0x6814c)+index,12)))
def initialise():
 image=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(image,aperture=0xa0000);image.cpu.mem_map(0x300000,0x10000)
 image.cpu.emu_start(image.native(0xb9110),image.native(0xb9133),count=10000);image.cpu.mem_write(image.data+0x24c9c,bytes(range(256))*16);image.cpu.mem_write(image.native(0x70aa4+0x47cea),bytes(image.cpu.mem_read(image.native(0x70aa4+0x68106),4)));image.call(0xc54f6,stack=(9,))
 image.intercept(0xc8568,'Resolve the supplied parent and carried-store models; original helpers and all geometry/VGA consumers execute.',resolve)
 image.cpu.hook_add(UC_HOOK_CODE,face,begin=image.native(0xbbd28),end=image.native(0xbbd28));return image,video
im,vga=initialise()
def programs(row):
 mode,wide,scale,delta=row[:4];kind=mode%4;first_angles=row[19:22];second_angles=row[22:25];anchor=row[25:28];second=row[28:31];vertices=[row[i:i+3] for i in range(31,40,3)]
 def blank():
  source=bytearray(50)
  for at,value in ((0,32768),(2,32767),(34,14),(48,65535)):struct.pack_into('>H',source,at,value)
  return source
 source=blank();child=blank()
 def emit(words,target=None):
  (source if target is None else target).extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 def vertex(index,v,target=None):emit([98,index,*v],target)
 def triangle(index,ink,target=None):
  vertex(index,vertices[0],target)
  for i in (1,2):
   if delta:emit([99,*[v-u for v,u in zip(vertices[i],vertices[i-1])]],target)
   else:vertex(index+i,vertices[i],target)
  emit([97,3,index,2,ink,index,index+1,index+2],target)
 def call(rotated,index,angles):
  emit([73,*angles,*([0]*6),index,0] if rotated else [45,index,0]);return len(source)-2
 emit([55 if mode//4==1 else 48,scale]);
 if mode//4==2:emit([54,65533])
 vertex(0,anchor);emit([97,1,0]);first=call(kind!=0,0,first_angles);triangle(40,23);emit([0]);struct.pack_into('>H',source,first,len(source)-first);vertex(1,second);emit([97,1,1])
 if kind==3:emit([81,1,2])
 else:nested=call(kind==1,1,second_angles)
 triangle(10,19);emit([0])
 if kind!=3:struct.pack_into('>H',source,nested,len(source)-nested);triangle(20,17);emit([0])
 emit([65535]);triangle(20,17,child);emit([0,65535],child);return source,child
rng=random.Random(0xbc2a8);rows=[]
for case in range(a.cases):
 matrix=[32767,0,0,0,32767,0,0,0,32767] if case<32 else [rng.randrange(-32768,32768) for _ in range(9)];angles=[0,0,0] if case%7==0 else [rng.randrange(65536) for _ in range(3)];cache=[rng.randrange(-1<<22,1<<22),rng.randrange(-1<<22,1<<22),rng.randrange(100<<16,1000<<16)];helpers=[[0,0,0] if case%11==0 else [rng.randrange(65536) for _ in range(3)] for _ in range(2)];anchors=[[rng.randrange(-400,401) for _ in range(3)] for _ in range(2)];vertices=[[rng.randrange(-800,801) for _ in range(3)] for _ in range(3)]
 rows.append([case%12,case%2,(1,2,5,10,400)[case%5],(case//4)%2,*matrix,*angles,*cache,*helpers[0],*helpers[1],*anchors[0],*anchors[1],*[v for point in vertices for v in point]])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_articulation_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[];undefined=painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 parent,child=programs(row);im.cpu.mem_write(0x300000,bytes(parent));im.cpu.mem_write(0x304000,bytes(child));im.call(0xb9f3f,stack=(0x300000,));im.call(0xb9f3f,stack=(0x304000,));im.call(0xca780)
 if row[1]:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',*row[4:13]));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f);im.cpu.mem_write(0x308000,struct.pack('<3i',*row[16:19]));im.cpu.mem_write(0x308020,bytes(16));im.cpu.mem_write(0x308040,struct.pack('<3H',*row[13:16]));im.cpu.mem_write(code(0x47c94+2),struct.pack('<H',88));im.call(0xc488d);vga.reset(99);observed.clear()
 try:im.call(0xcc164,stack=(1,0x308040,0x308000,0x308020,77),limit=3000000);im.call(0xc49d9,limit=3000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':raise
  undefined+=1;im,vga=initialise();continue # A trapped original CPU must not retain its pending fault into another case.
 assert not line.endswith('overflow'),(case,'C++ declined a completed original frame',row)
 values=list(map(int,line.split()));assert values[:-1]==observed,(case,row,'camera vertices',values[:-1],observed)
 want=bytes(vga.pixels());painted+=any(v!=99 for v in want);got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,'pixels',sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[-1]==digest
 if case<96 or case%31==0:fixtures.append(row+observed+[digest])
 if case and case%256==0:print(f'Checked {case} articulated frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete original articulated frames agree in all submitted camera vertices and every VGA pixel; {painted} nonempty, {undefined} original IDIV overflows excluded. Nested anchor/rotated helpers, restoration, carried stores and absolute/delta vertices execute with supplied view/body bases and poses.')
