#!/usr/bin/env python3
"""Compare original scoped face-depth palettes and vertex-selected conditions.

The resource converter, projection, opcode 74/118 helpers, conditional branch,
colour reuse, nested returns, palette lookup and VGA raster all execute.
Declared model bytes, camera state and distinct palette rows are supplied.
The corpus covers triangle/quad consumers used by both retained opcode-118
models; the original variable-polygon count-word quirk is a separate boundary.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x20000);code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
for f in (0xb9447,0xb944d,0xb9452,0xbc3ef,0xbc3fd,0xbc40b):im.cpu.mem_write(im.native(f),bytes(4))
im.cpu.mem_write(code(0x47c6e),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767));im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.cpu.mem_write(code(0x54a50),struct.pack('<H',9))
def program(row):
 wide,nested,fixed,threshold,object_offset,fixed_offset=row[:6];colours=row[6:9];depths=row[9:];source=bytearray(50)
 def store(at,value):struct.pack_into('>H',source,at,value&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 def link(field):store(field,len(source)-field)
 for at,value in ((2,32767),(34,14),(48,65535)):store(at,value)
 emit([48,1])
 for face in range(7):
  x=(face%3)*3000-4000;y=(face//3)*2400-3000
  for vertex in range(4):emit([98,face*4+vertex,x+(2200 if vertex in (1,2) else 0),y+(1800 if vertex>=2 else 0),depths[face*4+vertex]])
 emit([97,28,0,74,0,38,threshold,0]);branch=len(source)-2;emit([2,colours[0],0,1,2,7,0]);join=len(source)-2;link(branch);emit([2,colours[2],0,1,2]);link(join)
 emit([118,0]);helper=len(source)-2;emit([113,20,21,22,2,colours[0],24,25,26,0]);link(helper);emit([2,colours[1],4,5,6,113,8,9,10])
 if nested:emit([8,0]);child=len(source)-2;emit([114,16,17,18,19,0]);link(child)
 if fixed:emit([84])
 emit([3,colours[2],12,13,14,15])
 if not nested:emit([114,16,17,18,19])
 emit([0,65535]);return bytes(source)
rng=random.Random(0xbd264);rows=[]
for case in range(a.cases):
 depths=[rng.randrange(1000,32768) for _ in range(28)]
 if case%5==0:depths=[rng.choice((-1000,-1,31,32,33,34,35,100,1000,8192,16384,32767)) for _ in range(28)]
 rows.append([case%2,(case//2)%2,(case//4)%2,rng.randrange(32768),rng.randrange(256),rng.randrange(256),*[rng.randrange(256) for _ in range(3)],*depths])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_depth_palette_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[];painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,nested,fixed,threshold,object_offset,fixed_offset=row[:6];im.cpu.mem_write(0x300000,program(row));im.call(0xb9f3f,stack=(0x300000,));im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(im.data+0x24c9c,bytes((i*3+fixed_offset+row*17)&255 for row in range(16) for i in range(256)));im.cpu.mem_write(0x310000,bytes((i*5+object_offset)&255 for i in range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x310000));im.cpu.mem_write(code(0x47cce),bytes(im.cpu.mem_read(code(0x47cc6),4)));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300032);vga.reset(99);im.call(0xbb2aa,limit=3000000)
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined original frame',row);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[0]==digest;painted+=any(v!=99 for v in want)
 if case<96 or case%31==0:fixtures.append(row+[digest])
 if case and case%256==0:print(f'Checked {case} complete face-depth palette frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original face-depth palette frames agree; {painted} nonempty: signed high-word depth averages, per-face ink reuse, scoped/nested returns, fixed-palette persistence, vertex-selected distance conditions and every VGA pixel.')
