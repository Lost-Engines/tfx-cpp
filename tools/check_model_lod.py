#!/usr/bin/env python3
"""Compare complete queued, converted multi-level model rendering with native VGA.

CC0BF constructs each cached submission. BA98D executes real range selection,
polygon construction, matrix/scale setup, bytecode, near clipping and pixels,
or the authored one/two-pixel representation. Only model-handle resolution is
supplied. Source bytes, identity view matrix, viewport, raw camera cache and
identity colour rows are declared inputs; no model/raster helper is replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=1024);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);rng=random.Random(0xba9e7);code=lambda off:im.native(0x70aa4+off)
source=bytearray(48)
def store(at,value):struct.pack_into('>H',source,at,value&65535)
def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
store(0,32768)
for i,distance in enumerate((500,2000,8000,32767)):
 field=34+i*2;store(2+i*2,distance);store(18+i*2,0 if i<2 else i);store(field,len(source)-field)
 if i<2:
  size=200 if i else 40;emit([65535,48,1,98,0,-size,-size,0,98,1,size,-size,0,98,2,0,size,0,97,3,0,2,17+i*2,0,1,2,0,65535])
 else:emit([200+i-2])
im.cpu.mem_write(0x300000,bytes(source));im.call(0xb9f3f,stack=(0x300000,));im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000);im.cpu.mem_write(im.data+0x24c9c,bytes(range(256))*16);im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.call(0xc54f6,stack=(9,))
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==77
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000);image.return_from()
im.intercept(0xc8568,'Resolve the supplied converted multi-level model; original construction, selection, bytecode and VGA still execute.',resolve)
selected=-1
def observe(cpu,address,size,unused):
 global selected
 selected=(cpu.reg_read(r.UC_X86_REG_ESI)-0x300000-20)//2
im.cpu.hook_add(UC_HOOK_CODE,observe,begin=im.native(0xba9fe),end=im.native(0xba9fe));rows=[]
wrap=lambda value:((value+2147483648)&4294967295)-2147483648
boundaries=(-32768,-1,0,15,16,17,18,499,500,501,1999,2000,2001,7999,8000,8001,32767)
for case in range(a.cases):
 wide=case%2
 if case<len(boundaries)*6:depth=boundaries[(case//6)%len(boundaries)];point=[0,0,wrap(depth*65536+(-1,0,1)[(case//2)%3])]
 else:
  depth=rng.randrange(17,32768);point=[wrap(rng.randrange(-180,181)*depth*256+rng.randrange(256)),wrap(rng.randrange(-130,131)*depth*256+rng.randrange(256)),depth*65536+rng.randrange(65536)]
 rows.append([wide,*point])
text=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_lod_probe').resolve())];actual=subprocess.check_output(command,input=text).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=text);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[];seen=set()
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,*point=row;im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(0x300600,struct.pack('<3i',*point));im.cpu.mem_write(0x300620,bytes(16));im.call(0xc488d);im.call(0xcc0bf,stack=(0x300600,0x300620,77));vga.reset()
 for plane in vga.planes:plane[:]=bytes([99])*16000
 selected=-1;im.cpu.reg_write(r.UC_X86_REG_ESI,0);im.call(0xba98d,limit=3000000);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 seen.add(selected);assert int(line.split()[0])==selected,(case,row,line,[selected,digest])
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y]
  from collections import Counter
  from PIL import Image
  for name,pixels in [('native',want),('cpp',got)]:Image.frombytes('L',(320,200),pixels).resize((960,600),Image.Resampling.NEAREST).save(a.build/f'model-lod-{name}.png')
  raise AssertionError((case,row,len(differences),Counter(got),Counter(want),differences[:30]))
 if case<128 or case%31==0:fixtures.append(row+[selected,digest])
assert seen=={0,1,2,3},seen
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete native queued LOD model frames agree across all four representations: original conversion, cached submission, metric/header selection, polygon constructor/VM/projection/near clipping and one/two-pixel VGA paths')
