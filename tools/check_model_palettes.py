#!/usr/bin/env python3
"""Compare original fixed-palette switching through complete model programs.

The native resource converter, absolute/projected vertices, helper calls,
colour reuse, opcode 84, packed Gouraud colours, clipping and VGA raster execute.
Model bytes, identity basis, zero translation, two lookup rows and aperture are
supplied inputs. No bytecode or drawing helper is intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
for file in (0xb9447,0xb944d,0xb9452,0xbc3ef,0xbc3fd,0xbc40b):im.cpu.mem_write(im.native(file),bytes(4))
im.cpu.mem_write(code(0x47c6e),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767));im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)))
def program(row):
 transition,nested,wide,object_offset,fixed_offset=row[:5];colours=row[5:8];depths=row[8:14];source=bytearray(50)
 def store(at,value):struct.pack_into('>H',source,at,value&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 for at,value in ((2,32767),(34,14),(48,65535)):store(at,value)
 emit([48,1])
 for face in range(6):
  x=(face%3)*400-500;y=(face//3)*400-300
  for vertex in range(3):emit([98,face*3+vertex,x+(280 if vertex==1 else 0),y+(280 if vertex==2 else 0),depths[face]])
 emit([97,18,0])
 def face(index):
  if index==transition:emit([84])
  first=index*3
  if index in (1,3):emit([113,first,first+1,first+2])
  elif index==4:emit([76,0xc0cf,0xc700,77,first,first+1,first+2])
  else:emit([2,colours[0 if index==0 else 1 if index==2 else 2],first,first+1,first+2])
 face(0);face(1)
 if nested:
  emit([8,0]);target=len(source)-2;face(5);emit([0]);store(target,len(source)-target);face(2);face(3);face(4);emit([0,65535])
 else:
  for i in range(2,6):face(i)
  emit([0,65535])
 return bytes(source)
rng=random.Random(0xbc9ac);rows=[[case%7,(case//7)%2,case%2,rng.randrange(256),rng.randrange(256),*[rng.randrange(256) for _ in range(3)],*[rng.randrange(200,1600) for _ in range(6)]] for case in range(a.cases)];request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_palette_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[]
for case,(row,line) in enumerate(zip(rows,actual)):
 transition,nested,wide,object_offset,fixed_offset=row[:5];im.cpu.mem_write(0x300000,program(row));im.call(0xb9f3f,stack=(0x300000,));im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(im.data+0x24c9c,bytes((255-i+fixed_offset)&255 for i in range(256)));im.cpu.mem_write(im.data+0x24d9c,bytes((i*5+object_offset)&255 for i in range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',im.data+0x24d9c));im.cpu.mem_write(code(0x47cda),bytes(im.cpu.mem_read(code(0x47cd2),4)));im.cpu.mem_write(code(0x47cce),bytes(im.cpu.mem_read(code(0x47cc6),4)));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300032);vga.reset(99);im.call(0xbb2aa,limit=3000000)
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined original frame',row);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,'pixels',sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[0]==digest
 if case<128 or case%31==0:fixtures.append(row+[digest])
 if case and case%256==0:print(f'Checked {case} complete model palette frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original model palette frames agree: fixed/distance lookup rows, colour reuse across a palette switch, nested helper persistence, packed Gouraud shades and normal/wide clipping.')
