#!/usr/bin/env python3
"""Compare complete original rounded-quad frames and procedural state.

B9434 projects supplied Q16 camera vertices. Actual BC660, camera-space
midpoint projection, DAF50 corner fans, winding bypass, clipping, edge walking
and VGA callbacks execute. Inputs are vertices, viewport, mode and seed.
No geometry or raster helper is intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=1024);p.add_argument('--record',type=Path);a=p.parse_args()
def initialise():
 image=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(image,aperture=0xa0000);image.cpu.mem_map(0x300000,4096);code=lambda off:image.native(0x70aa4+off)
 image.cpu.emu_start(image.native(0xb9110),image.native(0xb9133),count=10000)
 for file in (0xb9447,0xb944d,0xb9452):image.cpu.mem_write(image.native(file),bytes(4))
 image.cpu.mem_write(image.data+0x24c9c,bytes(range(256)));image.cpu.mem_write(code(0x4787e),struct.pack('<I',image.data+0x24c9c));return image,video
im,vga=initialise();code=lambda off:im.native(0x70aa4+off);rng=random.Random(0xbc660);rows=[]
for case in range(a.cases):
 wide=case%2;mode=(-1,0,1,2,3,4,7,10,11,12)[case%10];minimum=[0,0];maximum=[319,199]
 if case%5==0:minimum=[30,40];maximum=[110,120]
 elif case%3==0:maximum[1]=172
 cx,cy=rng.randrange(-100,420),rng.randrange(-100,300);dx,dy=rng.randrange(1,200),rng.randrange(1,150);skew=rng.randrange(-80,80);screen=[(cx-dx,cy-dy),(cx+dx,cy-dy+skew),(cx+dx,cy+dy),(cx-dx,cy+dy-skew)];points=[]
 for x,y in screen:
  depth=rng.randrange(18,2000);z=depth*65536+rng.randrange(65536);points.extend([(x-160)*depth*(1<<(9 if wide else 8))+rng.randrange(256),(y-100)*depth*(1<<(9 if wide else 8))+rng.randrange(256),z])
 if case%7==0:points[2]=rng.choice((-1000,-1,0,15,16))*65536+rng.randrange(65536)
 if case%11==0:points=points[9:12]+points[6:9]+points[3:6]+points[:3]
 rows.append([wide,mode,rng.randrange(65536),*minimum,*maximum,*points])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'rounded_model_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();output=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(output)==len(rows)*64004;fixtures=[];undefined=painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,mode,seed,mx,my,hx,hy=row[:7];points=[row[i:i+3] for i in range(7,19,3)];im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=(160,100,hx,hy))
 try:
  for i,point in enumerate(points):im.cpu.mem_write(code(0x6814c+i*32),bytes(20)+struct.pack('<3i',*point))
  im.cpu.reg_write(r.UC_X86_REG_EDI,code(0x6814c));im.call(0xb9434,ecx=4)
  callback=struct.unpack('<I',im.cpu.mem_read(code(0x68106),4))[0] if mode==-1 else im.call(0xe5d5c,eax=mode);im.cpu.mem_write(code(0x47cea),struct.pack('<I',callback));im.cpu.mem_write(im.native(0xe3a3f),struct.pack('<H',seed));im.cpu.ctl_remove_cache(im.native(0xe3a04),im.native(0xe3a61));im.cpu.mem_write(0x300000,struct.pack('<5H',17,0,32,64,96));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000);vga.reset(99);im.call(0xbc660,limit=3000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':raise
  undefined+=1;im,vga=initialise();continue
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined a completed original frame',row)
 want=bytes(vga.pixels());got=output[case*64004+4:(case+1)*64004];want_seed=struct.unpack('<H',im.cpu.mem_read(im.native(0xe3a3f),2))[0];got_seed=struct.unpack_from('<I',output,case*64004)[0];assert got_seed==want_seed,(case,'seed',row,got_seed,want_seed);digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,'pixels',sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[:2]==[digest,want_seed];painted+=any(v!=99 for v in want)
 if case<128 or case%31==0 or case in (844,985):fixtures.append(row+[digest,want_seed])
 if case and case%256==0:print(f'Checked {case} original rounded-model frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete original rounded-model frames and seeds agree; {painted} nonempty, {undefined} original division faults excluded. Camera-space midpoints, near rejection, normal/wide apertures, all represented patterns/logical painters and clipped corner fans execute.')
