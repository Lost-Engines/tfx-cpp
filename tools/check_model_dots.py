#!/usr/bin/env python3
"""Compare complete original authored-point and particle-disc model programs.

The original resource converter, vertex construction, projection, palette and
material state, viewport clipping and VGA callbacks execute unchanged. Explicit
camera/viewport/parameter inputs and synthetic models are supplied; this is not
a complete session capture. Retained fixtures contain no original model bytes.
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
p.add_argument('--cases',type=int,default=1024)
p.add_argument('--record',type=Path)
p.add_argument('--circles',action='store_true',help='92/93/95/96 sized discs rather than fixed 51/52 dots')
a=p.parse_args()

def initialise():
 image=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000)
 video=VgaCapture(image,aperture=0xa0000)
 image.cpu.mem_map(0x300000,0x30000)
 image.cpu.emu_start(image.native(0xb9110),image.native(0xb9133),count=10000)
 return image,video

im,vga=initialise()
code=lambda off:im.native(0x70aa4+off)
modes=(-1,0,1,2,3,4,7,10,11,12)
rows=[]
for case in range(a.cases):
 rng=random.Random(0xbc540+case)
 wide=case%2
 minimum=[0,0] if case%4<2 else [rng.randrange(10,100),rng.randrange(10,60)]
 maximum=[319,199] if case%4<2 else [rng.randrange(220,310),rng.randrange(140,190)]
 centre=[160,100]
 target=[rng.randrange(-100,420),rng.randrange(-100,300)]
 depth=rng.choice([16,17,18,63,127,128,1000,4096])
 if a.circles:
  radius=case+1 if case<100 else rng.choice([0,1,2,10,50,98,99,100,101,255,32767,32768,65535,rng.randrange(256)])
  depth=128
  if case<100:target=[160,100]
  if case>=512:depth=rng.choice([16,17,18,63,127,128,255,4096])
  kind=0 if case<100 else case%4
 else:
  if case<64:
   target=[minimum[0]+((case//4)%8)-3,100] if case<32 else [maximum[0]+((case//4)%8)-3,100]
  elif case<128:
   target=[160,minimum[1]+((case//4)%8)-3] if case<96 else [160,maximum[1]+((case//4)%8)-3]
  elif case<192:
   centre=[32760,-32760];target=[rng.randrange(20,300),rng.randrange(20,180)];depth=32
  kind=(case//2)%2
 def signed32(value):return (value+2**31)%2**32-2**31
 shift=9 if wide else 8
 origin=[signed32(((target[i]-centre[i]+32768)%65536-32768)*depth*(1<<shift)) for i in range(2)]+[signed32(depth*65536+rng.randrange(65536))]
 params=[case%2,rng.randrange(256),modes[(case//4)%len(modes)],0,0,0,0,0]
 params=[x&255 for x in params]
 source=bytearray(50)
 def store(at,value):struct.pack_into('>H',source,at,value&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[x&65535 for x in words]))
 for at,value in ((2,32767),(34,14),(48,65535)):store(at,value)
 emit([48,1,98,0,0,0,0])
 if case%3==0:emit([84])
 if case%5==0:emit([86,257])
 if case%2==0 and params[2]!=255 and not(a.circles and case<100):emit([87,2])
 emit([97,1,0])
 ink=rng.randrange(256)
 if a.circles:
  mode=modes[1:][(case//11)%(len(modes)-1)]
  emit(([92,ink,0,radius],[93,mode,ink,0,radius],[95,1,ink,0,radius],[96,1,mode,ink,0,radius])[kind])
 else:emit([51+kind,ink,0])
 emit([0,65535])
 rows.append([wide,rng.randrange(65536),rng.randrange(256),rng.randrange(256),1000,0,32767,0,0,0,32767,0,0,0,32767,*origin,*params,*centre,*minimum,*maximum,source.hex()])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()
command=[str((a.build/'model_frame_probe').resolve()),'--viewport']
actual=subprocess.check_output(command,input=request).decode().splitlines()
pixels=subprocess.check_output(command+['--pixels'],input=request)
assert len(actual)==len(rows) and len(pixels)==len(rows)*64000
fixtures=[];painted=undefined=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,seed,object_offset,fixed_offset,distance,status=row[:6]
 basis=row[6:15];origin=row[15:18];params=row[18:26];centre=row[26:28];minimum=row[28:30];maximum=row[30:32]
 source=bytes.fromhex(row[32]);im.cpu.mem_write(0x300000,source)
 im.call(0xb9f3f,stack=(0x300000,));im.call(0xb930f);im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(minimum[0],maximum[0],minimum[1],maximum[1]))
 im.call(0xb94da,stack=(*(x&0xffffffff for x in centre),319,199))
 im.cpu.mem_write(code(0x47c6e),struct.pack('<9h',*basis));im.cpu.mem_write(code(0x47c80),struct.pack('<hH',distance,status));im.cpu.mem_write(code(0x47cb0),bytes(params))
 for f,value in zip((0xb9447,0xb944d,0xb9452),origin):im.cpu.mem_write(im.native(f),struct.pack('<i',value))
 for f,value in zip((0xbc3ef,0xbc3fd,0xbc40b),origin):im.cpu.mem_write(im.native(f),struct.pack('<i',value))
 im.cpu.ctl_remove_cache(im.native(0xb9434),im.native(0xb94d9));im.cpu.ctl_remove_cache(im.native(0xbc3e8),im.native(0xbc497))
 im.cpu.mem_write(im.data+0x24c9c,bytes((i*3+fixed_offset+row*17)&255 for row in range(16) for i in range(256)))
 im.cpu.mem_write(0x320000,bytes((i*5+object_offset)&255 for i in range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x320000))
 for current,base in ((0x47cce,0x47cc6),(0x47cda,0x47cd2),(0x47ce6,0x47cde)):im.cpu.mem_write(code(current),bytes(im.cpu.mem_read(code(base),4)))
 im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.cpu.mem_write(code(0x47ca8),bytes([(112*5+object_offset)&255]));im.cpu.mem_write(code(0x47cac),bytes([112]))
 im.cpu.mem_write(im.native(0xe3a3f),struct.pack('<H',seed));im.cpu.ctl_remove_cache(im.native(0xe3a04),im.native(0xe3a61));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300032);vga.reset(99)
 try:im.call(0xbb2aa,limit=5000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':print('Native point case',case,row[:32],flush=True);raise
  undefined+=1;im,vga=initialise();continue
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined a completed original model',row[:32])
 want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];want_seed=struct.unpack('<H',im.cpu.mem_read(im.native(0xe3a3f),2))[0]
 digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:
  print("source",source.hex(),"paint counts",sum(v!=99 for v in got),sum(v!=99 for v in want),"bounds",[(min([(i%320,i//320) for i,v in enumerate(frame) if v!=99],default=None),max([(i%320,i//320) for i,v in enumerate(frame) if v!=99],default=None)) for frame in (got,want)])
  raise AssertionError((case,row[:32],sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[:2]==[digest,want_seed],(case,'procedural state',values,[digest,want_seed])
 painted+=any(v!=99 for v in want)
 if case<192 or case%31==0:fixtures.append(row+[digest,want_seed])
 if case and case%128==0:print(f'Checked {case} complete point-model frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete original {"disc" if a.circles else "dot"} model frames agree; {painted} nonempty, {undefined} native division faults excluded: projection, apertures, viewport boundaries, palette/material state, circle extents, procedural seeds and every VGA pixel.')
