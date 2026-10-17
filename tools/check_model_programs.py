#!/usr/bin/env python3
"""Compare converted synthetic model programs through original VM and VGA.

The original resource converter, vertex handlers, camera scaling, projection,
facing branch, colour remap, near clipper and flat raster execute. Supplied
model bytes, identity camera/actor matrix, actor translation and viewport are
explicit inputs. No bytecode, projection or drawing helper is intercepted.
Overflow cases additionally supply the enclosing model-entry unwind stack and
execute the actual installed DPMI handler before its native early return.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_dpmi import DpmiReference
from native_vga import VgaCapture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--gouraud',action='store_true',help='execute authored vertex-colour and Gouraud face instructions')
p.add_argument('--cases',type=int,default=512)
p.add_argument('--overflow',action='store_true',help='exercise large vertices and the actual installed divide-overflow handler')
a=p.parse_args();kind='Gouraud' if a.gouraud else 'flat';reference=DpmiReference if a.overflow else NativeReference;im=reference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);rng=random.Random(0xbb2aa)
if a.overflow:
 im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK-256)
 im.cpu.emu_start(im.native(0xb90de),im.native(0xb9110),count=1000)
code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.cpu.mem_write(0x300800,bytes(range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x300800))
im.cpu.mem_write(code(0x47c6e),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767))
colour_calls=[]
im.cpu.hook_add(UC_HOOK_CODE,lambda cpu,at,size,unused:colour_calls.append(at),begin=im.native(0xbc498 if a.gouraud else 0xbbbb0),end=im.native(0xbc498 if a.gouraud else 0xbbbb0))
def program(points,scale):
 source=bytearray(50)
 def store(at,v):struct.pack_into('>H',source,at,v&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 store(2,32767);store(18,0);store(34,14);store(48,65535);emit([48,scale])
 for i,point in enumerate(points):emit([98,i,*point])
 emit([97,3,0,21,0,1,2,0]);field=len(source)-2
 emit([76,0xc0cf,0xc700,77,0,1,2,76,0xc0cf,0xc700,77,0,1,2,0] if a.gouraud else [2,17,0,1,2,2,17,0,1,2,0]);store(field,len(source)-field);emit([76,0xc5d3,0xcb00,77,0,1,2,0,65535] if a.gouraud else [2,19,0,1,2,0,65535]);return bytes(source)
rows=[]
for case in range(a.cases):
 wide=(case//2)%2;scale=(1,2,5,10,400)[case%5];offset=[rng.randrange(-5,6),rng.randrange(-5,6),rng.choice((0,1,10,100))]
 points=[[rng.randrange(-500,501),rng.randrange(-500,501),rng.choice((-100,-1,0,15,16,17,31,32,33,34,35,64,1000))] for _ in range(3)]
 if a.overflow:
  points=[[rng.randrange(-32768,32768),rng.randrange(-32768,32768),rng.choice((16,17,31,32,33,34,35,64,1000))]for _ in range(3)]
  if case%4==0:scale=1;offset=[0,0,0];points=[[-32760,-32760,34],[32760,-32760,34],[0,32760,34]]
 if case%11==0:points[2]=list(points[1])
 rows.append([wide,scale,*offset,*[v for point in points for v in point]])
text='\n'.join(' '.join(map(str,row)) for row in rows)+'\n'
flags=(['--shaded']if a.gouraud else[])+(['--native-camera']if a.overflow else[])
actual=subprocess.check_output([str((a.build/'model_program_probe').resolve()),*flags],input=text.encode()).decode().splitlines();pixels=subprocess.check_output([str((a.build/'model_program_probe').resolve()),'--pixels',*flags],input=text.encode());assert len(pixels)==len(rows)*64000
fixtures=[];branches=set()
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,scale,*_=row;offset=row[2:5];points=[row[i:i+3] for i in range(5,len(row),3)]
 raw=program(points,scale);im.cpu.mem_write(0x300000,raw);im.call(0xb9f3f,stack=(0x300000,),limit=100000)
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199))
 for file,value in zip((0xb9447,0xb944d,0xb9452),offset):im.cpu.mem_write(im.native(file),struct.pack('<i',value*32767))
 for file,value in zip((0xbc3ef,0xbc3fd,0xbc40b),offset):im.cpu.mem_write(im.native(file),struct.pack('<i',value*32767))
 im.cpu.ctl_remove_cache(im.native(0xb9434),im.native(0xb94d9));im.cpu.ctl_remove_cache(im.native(0xbc3e8),im.native(0xbc497))
 im.cpu.mem_write(code(0x47cda),bytes(im.cpu.mem_read(code(0x47cd2),4)))
 im.cpu.mem_write(code(0x47cce),bytes(im.cpu.mem_read(code(0x47cc6),4)))
 colour_calls.clear();vga.reset()
 for plane in vga.planes:plane[:]=bytes([99])*16000
 if a.overflow:im.cpu.mem_write(code(0x47860),struct.pack('<I',im.STACK))
 im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000+50);im.call(0xbb2aa,limit=3000000)
 want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 expected=[len(colour_calls),digest];branches.add(len(colour_calls));assert list(map(int,line.split()))==expected,(case,row,line,expected)
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y];raise AssertionError((case,row,len(differences),differences[:30]))
 if case<128 or case%31==0:fixtures.append(row+expected)
assert len(actual)==len(rows);assert branches==({0,1,2}if a.overflow else{1,2}),branches
if a.overflow:assert im.processor_exceptions,'overflow corpus did not reach an original divide exception'
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete synthetic native model programs agree in branch-controlled draw counts and every VGA pixel: original endian conversion, absolute vertices, camera scaling/translation, projection, both facing paths, {kind}/near raster, normal/wide modes and return dispatch')
