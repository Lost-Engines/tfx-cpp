#!/usr/bin/env python3
"""Compare original rain initialization, complete VGA pixels and wind advection.

The original shared random generator, matrix helpers, projection, clipping,
point raster and x87 drift execute. Camera/viewport/wind/seed are supplied inputs.
No numerical or drawing routine is intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--cases',type=int,default=2048)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.call(0xde851);rng=random.Random(0x78d8c)
def digest(data):
 value=14695981039346656037
 for byte in data:value=((value^byte)*1099511628211)&0xffffffffffffffff
 return value
rows=[]
for case in range(a.cases):
 low,high=rng.randrange(65536),rng.randrange(65536)
 drift=[rng.randrange(-32768,32768) for _ in range(3)]
 count=rng.choice((-32768,-1,0,1,2,199,200,299,300,301,32767)) if case<256 else rng.randrange(-20,320)
 wind=[rng.choice((-100000.,-30.,-2.5,-.1,0.,.1,2.5,30.,100000.)) if case<256 else rng.uniform(-100,100) for _ in range(2)]
 wind_bits=[struct.unpack('<I',struct.pack('<f',v))[0] for v in wind]
 matrix=[32767,0,0,0,32767,0,0,0,32767] if case%4==0 else [rng.randrange(-32768,32768) for _ in range(9)]
 camera=[rng.choice((-32768,-1,0,1,32767)) if case<256 else rng.randrange(-32768,32768) for _ in range(3)]
 origin=[rng.choice((0,159,160,319)),rng.choice((0,56,70,99,100,199))]
 minimum=[0,0];maximum=[319,rng.choice((112,140,199))]
 if case%7==0:minimum=[32,24];maximum=[287,175]
 rows.append([low,high,*drift,count,*wind_bits,*matrix,*camera,*origin,*minimum,*maximum])
text='\n'.join(' '.join(map(str,row)) for row in rows)+'\n'
actual=subprocess.check_output([str((a.build/'precipitation_probe').resolve())],input=text.encode()).decode().splitlines()
pixels=subprocess.check_output([str((a.build/'precipitation_probe').resolve()),'--pixels'],input=text.encode());assert len(pixels)==64000*len(rows)
fixtures=[];painted=0
for case,(row,line) in enumerate(zip(rows,actual)):
 low,high,*_=row;dx,dy,dz,count=row[2:6];wx,wz=row[6:8];matrix=row[8:17];camera=row[17:20];ox,oy,mx,my,hx,hy=row[20:]
 im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high));im.write(0x5a4c,'<3h',dx,dy,dz);im.call(0x78af8,limit=100000)
 want_random=struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4));field=bytes(im.cpu.mem_read(im.data+0x1111c,1800))
 # These camera globals live in the executable's writable CODE object.
 code=lambda offset:im.native(0x70aa4+offset)
 im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',*matrix));im.cpu.mem_write(code(0x47c06),struct.pack('<3h',*camera))
 im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=(ox,oy,hx,hy))
 im.write(0x13400,'<I',wx);im.write(0x133fc,'<I',wz)
 video.reset()
 for plane in video.planes:plane[:]=bytes([77])*16000
 im.call(0x78d8c,eax=count&0xffffffff,limit=500000)
 expected_pixels=bytes(video.pixels());expected=[*want_random,digest(field),*im.read(0x5a4c,'<3H'),digest(expected_pixels)]
 values=list(map(int,line.split()));assert values==expected,(case,row,values,expected)
 got=pixels[case*64000:(case+1)*64000]
 if got!=expected_pixels:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,expected_pixels)) if x!=y]
  raise AssertionError((case,row,len(differences),differences[:30]))
 painted+=sum(v==241 for v in expected_pixels)
 if case<64 or case%67==0:fixtures.append(row+expected)
 if case and case%512==0:print(f'Checked {case} complete rain frames',flush=True)
assert len(actual)==len(rows)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original precipitation frames agree pixel for pixel: 300-particle initialization and shared RNG, transposed look-ahead, word-box wrapping, Q15 transforms, depth bias/IDIV projection, viewport clipping and x87 wind drift; {painted} visible rain pixels')
