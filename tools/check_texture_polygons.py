#!/usr/bin/env python3
"""Compare complete original affine textured polygons through VGA.

Original BDC38 executes screen-word winding/clipping, Q7 UV clipping,
DB3C8/DB4DC edges, DBFA0 scanline storage and E5DD8 texel loops. Screen/UV words,
viewport, a supplied 256x256 diagnostic atlas and lookup row are inputs. The
atlas deliberately defines all wrapped byte coordinates, including its final
64 rows; retail 256x192 assets remain separate. No raster helper is replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path);p.add_argument('--crossed',action='store_true',help='permute authored corners to exercise crossed and concave projections');a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x20000);code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000);im.cpu.mem_write(0x300000,bytes((u*3+v*5+(u^v))&255 for v in range(256) for u in range(256)));im.cpu.mem_write(code(0x4787a),struct.pack('<I',0x300000));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x310000));rng=random.Random(0xbdc38)
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
 points=hull([(rng.randrange(-100,420),rng.randrange(-100,300)) for _ in range(rng.randrange(4,12))]);assert len(points)>=3
 if case%11==0:points.reverse()
 if case%23==0:points=[(20,50),(50,50),(80,50)]
 if case%31==0:points=[(100,20),(100,50),(100,80)]
 if a.crossed:rng.shuffle(points)
 minimum=[30,40] if case%5==0 else [0,0];maximum=[110,120] if case%5==0 else [319,172 if case%3==0 else 199]
 uv=[[rng.randrange(2*128,250*128),rng.randrange(2*128,185*128)] for _ in points];rows.append([len(points),rng.randrange(256),*minimum,*maximum,*[v for p,t in zip(points,uv) for v in (*p,*t)]])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'texture_polygon_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();output=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(output)==len(rows)*64000;fixtures=[]
for case,(row,line) in enumerate(zip(rows,actual)):
 count,offset,mx,my,hx,hy=row[:6];im.call(0xb9238,stack=(mx,hx,my,hy));im.cpu.mem_write(0x310000,bytes((i*5+offset)&255 for i in range(256)))
 for i in range(count):
  x,y,u,v=row[6+i*4:10+i*4];im.cpu.mem_write(code(0x6815a+i*32),struct.pack('<2h',x,y));im.cpu.mem_write(code(0x481ac+i*4),struct.pack('<2H',u,v))
 im.cpu.mem_write(0x311000,struct.pack('<'+str(count)+'H',*[i*32 for i in range(count)]));im.cpu.reg_write(r.UC_X86_REG_ESI,0x311000);vga.reset(99);im.call(0xbdc38,ecx=count,limit=3000000);want=bytes(vga.pixels());got=output[case*64000:(case+1)*64000];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert int(line)==digest
 if case<128 or case%31==0:fixtures.append(row+[digest])
 if case and case%256==0:print(f'Checked {case} complete textured-polygon frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original textured-polygon VGA frames agree: clipping, fractional Q7 UVs, integer edges, Q24 texel stepping, palette lookup and transparent texels. Screen-space kernel only; model near-plane dispatch and retail atlas integration remain separate.')
