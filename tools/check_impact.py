#!/usr/bin/env python3
"""Compare original screen-palette impact classes and complete crash selection.

Projection/pixel access are supplied boundaries for 0x7da20. The 0x7d270 crash
chooser runs with supplied terrain type and classified pixel; its remaining
loss/audio/camera effects are separate comparisons. No classification or model
selection branch is intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0x7da20)
pixel_image=NativeReference(a.data_dir/'TFX.DAT');projected=[1,160,100,0]
def projection(im):
 sp=im.cpu.reg_read(r.UC_X86_REG_ESP);output=struct.unpack('<I',im.cpu.mem_read(sp+16,4))[0]
 im.cpu.mem_write(output,struct.pack('<2h',*projected[1:3]));im.cpu.reg_write(r.UC_X86_REG_EAX,projected[0]);im.return_from(stack_bytes=16)
def pixel(im):
 sp=im.cpu.reg_read(r.UC_X86_REG_ESP);y,x=struct.unpack('<2I',im.cpu.mem_read(sp+4,8));assert (x,y)==tuple(projected[1:3])
 im.cpu.reg_write(r.UC_X86_REG_EAX,projected[3]);im.return_from(stack_bytes=8)
pixel_image.intercept(0xc5759,'Supply a projected point; fixed point projection has its own native comparison.',projection)
pixel_image.intercept(0xc707c,'Supply the sampled indexed-framebuffer byte; all band classification executes.',pixel)
crash_image=NativeReference(a.data_dir/'TFX.DAT');crash_image.cpu.mem_map(0x300000,4096)
terrain=[0,-1];surface=[-1]
crash_image.intercept(0xb6e88,'Supply an intact aircraft before a physical collision.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
crash_image.intercept(0xb1334,'Supply writable parser outcome variables; this does not affect crash choice.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
for address in (0x75030,0xb52d4,0x8fd84,0xcccc4,0xccf4c,0xa4f2c,0xa5a9c):
 crash_image.intercept(address,'Omit independently compared loss model/camera/audio outputs; crash handle and angles remain native.',lambda im:im.return_from())
crash_image.intercept(0xb0d80,'Supply the current terrain handle or the original no-definition sentinel.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,5 if terrain[0] else 1),im.return_from()))
crash_image.intercept(0xb7a3c,'Supply the terrain definition type independently of resource-handle allocation.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,terrain[1]&0xffffffff),im.return_from()))
crash_image.intercept(0x7da20,'Supply the already compared screen-palette classification to the crash chooser.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,surface[0]&0xffffffff),im.return_from()))
rows=[];expected=[];fixtures=[]
for index in range(4096):
 valid=1 if index<512 else rng.randrange(2)
 x,y=(160,100) if index<512 else (rng.choice([-32768,-1,0,1,319,320,321,32767]),rng.choice([-32768,-1,0,1,199,200,201,32767]))
 byte=index%256;water=(index//256)%2;projected[:]=[valid,x,y,byte]
 pixel_image.write(0xe774,'<B',64 if water else 0)
 result=pixel_image.call(0x7da20,eax=1000,edx=(-100)&0xffffffff,ebx=2000,ecx=1)
 result=struct.unpack('<i',struct.pack('<I',result))[0]
 row=['P',valid,x,y,byte,water];rows.append(row);expected.append(result)
 if index<512 or index%31==0:fixtures.append(row+[result])
 cannon=1
 result=pixel_image.call(0x7da20,eax=1000,edx=(-100)&0xffffffff,ebx=2000,ecx=0 if cannon else 1)
 result=struct.unpack('<i',struct.pack('<I',result))[0]
 row=['W',valid,x,y,byte,water,cannon];rows.append(row);expected.append(result)
 if index<512 or index%31==0:fixtures.append(row+[result])
for index in range(4096):
 collision=rng.choice([1,2,-1,32767]);present=rng.randrange(2);kind=rng.choice([-1,0,1,2,50,56]);sample=rng.choice([-1,0,1,2]);water=rng.randrange(2)
 terrain[:]=[present,kind];surface[0]=sample
 for at,fmt,value in [(0xe76c,'<H',1),(0x12bfc,'<H',2),(0x12bfa,'<H',4),(0x12c00,'<H',3),(0x12c02,'<h',0),(0x12c04,'<h',collision),(0x86ce,'<B',0),(0x13250,'<H',0),(0xe784,'<B',0),(0xe774,'<B',64 if water else 0),(0x13476,'<H',0),(0x593a,'<h',0),(0x13430,'<i',-1000)]:crash_image.write(at,fmt,value)
 crash_image.write(0x86c8,'<3H',1000,2000,3000);crash_image.call(0x7d270)
 handle=crash_image.read(0xe76c,'<H')[0];assert handle in (2,4)
 assert crash_image.read(0x86c8,'<3H')==(0,0,0)
 assert crash_image.read(0x12c02,'<h')[0]==200
 row=['C',collision,present,kind,sample,water];result=int(handle==4);rows.append(row);expected.append(result)
 if index<128:fixtures.append(row+[result])
result=subprocess.check_output([str((a.build/'impact_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for index,(line,value) in enumerate(zip(result,expected)):assert int(line)==value,(index,rows[index],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
print('8192 complete original impact classifiers agree: ordinary/cannon mapping, all palette bytes, strict screen bounds, projection failure and water-world override')
print('4096 complete original crash selectors agree: terrain sentinel/type, sampled appearance, forced water, collision-2 override, cleared Euler angles and 200-tick start')
