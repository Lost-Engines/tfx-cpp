#!/usr/bin/env python3
"""Compare complete model-face frames through native projection and VGA.

Original B9434 projection and BD3A8 clipping/scan conversion execute. Synthetic
Q16 faces exercise the ordinary path or, with --near, the complete native
near-crossing dispatcher. --gouraud checks shade attributes; --pattern checks
all nine patterned/logical painters and their procedural state. Textures and
whole-scene ordering remain separate gates. Camera/actor translation,
colour/remap, viewport and input vertices are supplied boundaries.
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
p.add_argument('--cases',type=int,default=1024)
p.add_argument('--gouraud',action='store_true',help='exercise projected Gouraud faces rather than flat ink')
p.add_argument('--pattern',action='store_true',help='exercise all nine original stipple/logical face painters and procedural seeds')
p.add_argument('--near',action='store_true',help='exercise original near-plane clipping on signed Q16 triangles')
a=p.parse_args();kind='patterned' if a.pattern else 'Gouraud' if a.gouraud else 'flat';im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);rng=random.Random(0xbd3a8)
code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
for file in (0xb9447,0xb944d,0xb9452):im.cpu.mem_write(im.native(file),bytes(4))
im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)))
im.cpu.mem_write(im.data+0x24c9c,bytes(range(256)))
im.cpu.mem_write(code(0x4787e),struct.pack('<I',im.data+0x24c9c));im.cpu.mem_write(code(0x47ca8),bytes([17]))
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
 wide=case%2;scale=(1,.5,.025,.005,.0025,1/7,1/23)[case%7];z=rng.randrange(18,2000)*65536
 if case<128:
  points=[(rng.randrange(-1000,0)*65536,rng.randrange(-700,0)*65536,z),(rng.randrange(1,1000)*65536,rng.randrange(-700,0)*65536,z),(rng.randrange(-300,300)*65536,rng.randrange(1,700)*65536,z)]
 else:
  xy=hull([(rng.randrange(-1600,1600)*65536+rng.randrange(65536),rng.randrange(-1000,1000)*65536+rng.randrange(65536)) for _ in range(rng.randrange(4,14))]);assert len(xy)>=3
  points=[(x,y,z) for x,y in xy]
  if case%11==0:points.reverse()
 if case%23==0:points=[(-30*65536,0,z),(0,0,z),(30*65536,0,z)]
 if case%31==0:points=[(0,-30*65536,z),(0,0,z),(0,30*65536,z)]
 minimum=[0,0];maximum=[319,199]
 if case%3==0:maximum[1]=172
 if case%5==0:minimum=[30,40];maximum=[110,120]
 rows.append([wide,len(points),scale,*minimum,*maximum,*[v for point in points for v in point]])
if a.near:
 for case,row in enumerate(rows):
  row[1]=3;row[7:]=row[7:16]
  for vertex in range(3):row[9+vertex*3]=rng.choice((-32768,-1000,-100,-1,0,15,16,17,18,100,1000,32767))*65536+rng.randrange(65536)
if a.pattern:
 assert not a.gouraud
 for case,row in enumerate(rows):row.extend(((0,1,2,3,4,7,10,11,12)[case%9],rng.randrange(65536)))
text='\n'.join(' '.join(map(str,row)) for row in rows)+'\n'
output=subprocess.check_output([str((a.build/'world_polygon_probe').resolve()),'--pixels']+(['--shaded'] if a.gouraud else [])+(['--pattern'] if a.pattern else []),input=text.encode());stride=64004 if a.pattern else 64000;assert len(output)==stride*len(rows)
fixtures=[]
for case,row in enumerate(rows):
 wide,count,scale,mx,my,hx,hy=row[:7];flat=row[7:-2] if a.pattern else row[7:];points=[flat[i:i+3] for i in range(0,len(flat),3)]
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=(160,100,hx,hy))
 for i,point in enumerate(points):im.cpu.mem_write(code(0x6814c+i*32),bytes(20)+struct.pack('<3i',*point))
 im.cpu.reg_write(r.UC_X86_REG_EDI,code(0x6814c));im.call(0xb9434,ecx=count)
 if a.gouraud:
  for i in range(count):im.cpu.mem_write(code(0x47fac+i*4),struct.pack('<I',(192+i%16)<<8))
 im.cpu.mem_write(0x300000,struct.pack('<'+str(count)+'H',*[i*32 for i in range(count)]));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000);vga.reset(99)
 if a.pattern:
  mode,seed=row[-2:];callback=im.call(0xe5d5c,eax=mode)
  im.cpu.mem_write(code(0x47cea),struct.pack('<I',callback));im.cpu.mem_write(im.native(0xe3a3f),struct.pack('<H',seed));im.cpu.ctl_remove_cache(im.native(0xe3a04),im.native(0xe3a61))
 im.call(0xd8074 if a.near and a.gouraud else 0xd7998 if a.near else 0xbd95c if a.gouraud else 0xbd3a8,ecx=count,limit=3000000)
 want=bytes(vga.pixels());got=output[case*stride+(4 if a.pattern else 0):(case+1)*stride]
 if a.pattern:
  got_seed=struct.unpack_from('<I',output,case*stride)[0];want_seed=struct.unpack('<H',im.cpu.mem_read(im.native(0xe3a3f),2))[0]
  assert got_seed==want_seed,(case,'procedural state',row,got_seed,want_seed)
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y]
  raise AssertionError((case,row,len(differences),differences[:30]))
 if case<128 or case%31==0:
  digest=14695981039346656037
  for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(row+[digest]+([want_seed] if a.pattern else []))
 if case and case%256==0:print(f'Checked {case} complete {kind} model-face frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete {kind} model-face VGA frames agree pixel for pixel: native Q16 normal/wide projection, scaled coordinates, winding, bottom/top/right/left clipping, reciprocal integer edges and inclusive spans; partial cockpit/MFD viewports included')

if a.near:print(('Original D8074/D809B/D824E Gouraud near clipping' if a.gouraud else 'Original D7998/D7BE5/D7C90 near clipping')+' also executes, including exact/fractional near depths, both crossing directions, all-behind faces, midpoint wraps, projection saturation and winding after clipping')
