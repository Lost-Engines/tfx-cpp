#!/usr/bin/env python3
"""Compare complete original Gouraud polygon frames, including clipped edges.

Original BD95C screen clipping, reciprocal edge/colour stepping and VGA writes
execute. Supplied screen-word vertices, 8.8 palette attributes, viewport and
identity/reversed lookup rows are explicit inputs; projection and near clipping
remain separate consumers.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--wide-colours',action='store_true',help='also exercise differences across the entire 8.8 colour word')
p.add_argument('--cases',type=int,default=1024)
p.add_argument('--thin',action='store_true',help='exercise thin faces with empty scanlines in all four VGA plane phases')
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);rng=random.Random(0xbd95c)
code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x300400))
def hull(points):
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 points=sorted(set(points));lo=[];hi=[]
 for point in points:
  while len(lo)>1 and cross(lo[-2],lo[-1],point)<=0:lo.pop()
  lo.append(point)
 for point in reversed(points):
  while len(hi)>1 and cross(hi[-2],hi[-1],point)<=0:hi.pop()
  hi.append(point)
 return lo[:-1]+hi[:-1]
rows=[]
for case in range(a.cases):
 points=hull([(rng.randrange(-300,600),rng.randrange(-300,500)) for _ in range(rng.randrange(3,12))])
 if case<32:
  x,y=20+case%4,20+case//4;w,h=(1,2,7,80)[case%4],(1,2,7,80)[(case//4)%4];points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h)]
 if case%19==0:points.reverse()
 if case%23==0:points=[(20,20),(20,20),(20,20)]
 if case%29==0:points=[(20,20),(100,100),(180,180)]
 if a.thin:
  if case<16:
   x,y=20+case%4,20+case//4;points=[(x+3,y),(x+8,y+9),(x,y+1)]
  else:
   while True:
    x,y=rng.randrange(-16,320),rng.randrange(-32,200)
    width,height=rng.randrange(1,17),rng.randrange(1,65)
    points=hull([(x+rng.randrange(width+1),y+rng.randrange(height+1))for _ in range(rng.randrange(3,12))])
    if len(points)>=3:break
   if case%19==0:points.reverse()
 bank=case%2;base=rng.randrange(16)*4096;shades=[base+rng.randrange(4096) for _ in points]
 if a.wide_colours and case>=32 and case%7==0:shades=[rng.randrange(65536) for _ in points]
 if case%11==0:shades=[base]*len(points)
 minimum=[0,0];maximum=[319,199]
 if case%3==0:maximum[1]=172
 if case%5==0:minimum=[30,40];maximum=[110,120]
 rows.append([len(points),bank,*minimum,*maximum,*[v for (x,y),shade in zip(points,shades) for v in (x,y,shade)]])
output=subprocess.check_output([str((a.build/'gouraud_polygon_probe').resolve()),'--pixels'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode());assert len(output)==64000*len(rows);fixtures=[]
for case,row in enumerate(rows):
 count,bank,mx,my,hx,hy=row[:6];points=[row[6+i*3:9+i*3] for i in range(count)]
 im.call(0xb9238,stack=(mx,hx,my,hy));im.cpu.mem_write(0x300400,bytes(255-i if bank else i for i in range(256)))
 for i,(x,y,shade) in enumerate(points):
  im.cpu.mem_write(code(0x6815a+i*32),struct.pack('<2h',x,y));im.cpu.mem_write(code(0x47fac+i*4),struct.pack('<I',shade))
 im.cpu.mem_write(0x300000,struct.pack('<'+str(count)+'H',*[i*32 for i in range(count)]));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000);vga.reset()
 for plane in vga.planes:plane[:]=bytes([99])*16000
 im.call(0xbd95c,ecx=count,limit=3000000);want=bytes(vga.pixels());got=output[case*64000:(case+1)*64000]
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y]
  raise AssertionError((case,row,len(differences),differences[:30]))
 if case<32 or case%31==0 or (a.wide_colours and case%7==0) or (a.thin and case<128):
  digest=14695981039346656037
  for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(row+[digest])
 if case and case%256==0:print(f'Checked {case} complete native Gouraud frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original Gouraud polygon frames agree: reciprocal edges, word clipping, fractional palette indices, lookup rows, viewport bounds, degenerate and reversed faces')
