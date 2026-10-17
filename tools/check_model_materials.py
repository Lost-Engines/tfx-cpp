#!/usr/bin/env python3
"""Compare parameter-selected drawing state through complete native models.

The original converter, vertex/projection opcodes, 86/87/88/89, ordinary helper
calls, palette/ink state and VGA drawing execute. A supplied model, camera,
parameter bank, atlas, lookup rows and procedural seed are explicit inputs.
Only resolution of diagnostic texture handle 42 is intercepted. This is not a
complete world/session capture. --model checks a retained resource separately;
its original bytes are not written into distributable synthetic fixtures.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=512);p.add_argument('--record',type=Path);p.add_argument('--model',type=Path);p.add_argument('--rounded',action='store_true',help='exercise original 56/62 rounded quads and 90/91 standalone arcs');a=p.parse_args()
assert not(a.model and a.rounded)
assert not(a.model and a.record),'retained game model bytes stay external to source fixtures'
def initialise():
 image=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(image,aperture=0xa0000);image.cpu.mem_map(0x300000,0x30000);image.cpu.emu_start(image.native(0xb9110),image.native(0xb9133),count=10000);image.cpu.mem_write(0x310000,bytes((u*3+v*5+(u^v))&255 for v in range(256) for u in range(256)))
 def resolve(im):
  assert im.cpu.reg_read(r.UC_X86_REG_EAX)&65535==42
  im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000);im.return_from()
 image.intercept(0xc85a0,'Resolve supplied diagnostic texture handle 42; native material, binding, clipping and texel consumers execute.',resolve);return image,video
im,vga=initialise();code=lambda off:im.native(0x70aa4+off);rng=random.Random(0xbc9c0);rows=[]
def program(case):
 phase=case%4;kind=(case//4)%3;fixed=(case//12)%2;source=bytearray(50)
 def store(at,value):struct.pack_into('>H',source,at,value&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 for at,value in ((2,32767),(34,14),(48,65535)):store(at,value)
 emit([48,1])
 for face in range(8):
  x=(face%4)*180-350;y=(face//4)*240-230
  for vertex in range(4):emit([98,face*4+vertex,x+(140 if vertex in (1,2) else 0),y+(170 if vertex>=2 else 0),600+rng.randrange(-50,51)])
 def enable():emit([86,257,87,2])
 def flat(face):emit([3,50+face,face*4,face*4+1,face*4+2,face*4+3])
 if phase==1:enable()
 emit([97,32,0]);flat(0)
 if phase!=1:enable()
 if phase==2:emit([97,32,0])
 flat(1)
 if kind==0:flat(2)
 elif kind==1:emit([78,0xc0cf,0xc7d3,79,8,9,10,11])
 else:emit([71,0,4,2,2,240,2,240,180,2,180,47,4,8,9,10,11])
 emit([88,114,12,13,14,15]);flat(4)
 emit([8,0]);helper=len(source)-2;emit([89]);flat(6);emit([114,28,29,30,31,0]);store(helper,len(source)-helper)
 if fixed:emit([84])
 emit([87,4]);flat(5);emit([0,65535]);return bytes(source)
def rounded_program(case):
 source=bytearray(50)
 def store(at,value):struct.pack_into('>H',source,at,value&65535)
 def emit(words):source.extend(struct.pack('>'+str(len(words))+'H',*[v&65535 for v in words]))
 for at,value in ((2,32767),(34,14),(48,65535)):store(at,value)
 emit([48,1])
 for face in range(8):
  x=(face%4)*180-350;y=(face//4)*240-230
  for vertex in range(4):emit([98,face*4+vertex,x+(140 if vertex in (1,2) else 0),y+(170 if vertex>=2 else 0),600+rng.randrange(-50,51)])
 modes=(0,1,2,3,4,7,10,11,12)
 emit([97,32,0,3,50,0,1,2,3,87,2])
 if case%3==0:emit([86,1])
 emit([56,51,4,5,6,7,114,8,9,10,11,62,modes[case%9],53,12,13,14,15,90,54,16,17,18])
 if case%2:emit([84])
 emit([91,modes[(case//3)%9],55,20,21,22,88,114,24,25,26,27,89,3,57,28,29,30,31,0,65535])
 return bytes(source)
for case in range(a.cases):
 source=a.model.read_bytes() if a.model else rounded_program(case) if a.rounded else program(case);origin=[rng.randrange(-50,51)*65536,rng.randrange(-50,51)*65536,(18 if not a.model and case%4 in (2,3) else 350)*65536]
 if not a.model and case%4 in (2,3):origin[2]-=300*65536
 modes=(0,1,2,3,4,7,10,11,12);params=[case%2,rng.randrange(256),modes[case%len(modes)],rng.randrange(256),modes[(case//7)%len(modes)],0,0,0]
 basis=[32767,0,0,0,32767,0,0,0,32767]
 if a.model and case%3:basis=[0,0,32767,0,32767,0,-32767,0,0] if case%3==1 else [32767,0,0,0,0,32767,0,-32767,0]
 rows.append([case%2,rng.randrange(65536),rng.randrange(256),rng.randrange(256),1000,0,*basis,*origin,*params,source.hex()])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'model_frame_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[];painted=undefined=0
for case,(row,line) in enumerate(zip(rows,actual)):
 wide,seed,object_offset,fixed_offset,distance,status=row[:6];basis=row[6:15];origin=row[15:18];params=row[18:26];source=bytes.fromhex(row[26]);im.cpu.mem_write(0x300000,source);im.call(0xb9f3f,stack=(0x300000,));im.call(0xb930f);im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(code(0x47c6e),struct.pack('<9h',*basis));im.cpu.mem_write(code(0x47c80),struct.pack('<hH',distance,status));im.cpu.mem_write(code(0x47cb0),bytes(params));im.cpu.mem_write(code(0x47c84),struct.pack('<H',42));im.cpu.mem_write(code(0x54a50),struct.pack('<H',9))
 for f,value in zip((0xb9447,0xb944d,0xb9452),origin):im.cpu.mem_write(im.native(f),struct.pack('<i',value))
 for f,value in zip((0xbc3ef,0xbc3fd,0xbc40b),origin):im.cpu.mem_write(im.native(f),struct.pack('<i',value))
 im.cpu.ctl_remove_cache(im.native(0xb9434),im.native(0xb94d9));im.cpu.ctl_remove_cache(im.native(0xbc3e8),im.native(0xbc497));im.cpu.mem_write(im.data+0x24c9c,bytes((i*3+fixed_offset+row*17)&255 for row in range(16) for i in range(256)));im.cpu.mem_write(0x320000,bytes((i*5+object_offset)&255 for i in range(256)));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x320000))
 for current,base in ((0x47cce,0x47cc6),(0x47cda,0x47cd2),(0x47ce6,0x47cde)):im.cpu.mem_write(code(current),bytes(im.cpu.mem_read(code(base),4)))
 im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.cpu.mem_write(code(0x47ca8),bytes([(112*5+object_offset)&255]));im.cpu.mem_write(code(0x47cac),bytes([112]));im.cpu.mem_write(im.native(0xe3a3f),struct.pack('<H',seed));im.cpu.ctl_remove_cache(im.native(0xe3a04),im.native(0xe3a61));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300032);vga.reset(99)
 try:im.call(0xbb2aa,limit=5000000)
 except RuntimeError as error:
  if str(error)!='undeclared native interrupt 0x0':
   print('Native material case',case,row[:26],flush=True);raise
  undefined+=1;im,vga=initialise();continue
 values=list(map(int,line.split()));assert values[-1],(case,'C++ declined a completed original model',row[:26]);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];want_seed=struct.unpack('<H',im.cpu.mem_read(im.native(0xe3a3f),2))[0];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row[:26],sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert values[:2]==[digest,want_seed],(case,'procedural state',values,[digest,want_seed]);painted+=any(v!=99 for v in want)
 if case<64 or case%31==0 or case in (305,333):fixtures.append(row+[digest,want_seed])
 if case and case%128==0:print(f'Checked {case} complete material-model frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)-undefined} complete original material-model frames agree; {painted} nonempty, {undefined} native division faults excluded: constant raw ink, parameter modes, restore/reused ink, helper persistence, projection-selected consumers, palette lookup, procedural seeds and every VGA pixel.')
