#!/usr/bin/env python3
"""Compare the complete original ILBM screenshot encoder byte for byte.

Only DOS file operations and reading the displayed VGA pixel are hosted. The
original palette conversion, bitplane packing, row compression, headers and
size patching execute. Test images and palettes are synthetic, not game assets.
"""
import argparse
import random
import struct
import subprocess
from pathlib import Path
from native_reference import NativeReference,r
from ilbm import decode_ilbm

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
output=bytearray();position=0;pixels=b''
def create(current):
 global output,position
 output=bytearray();position=0
 current.cpu.reg_write(r.UC_X86_REG_EAX,7);current.return_from()
def write(current):
 global position
 size=current.cpu.reg_read(r.UC_X86_REG_EDX)
 raw=bytes(current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_EAX),size))
 if position+size>len(output):output.extend(bytes(position+size-len(output)))
 output[position:position+size]=raw;position+=size
 current.cpu.reg_write(r.UC_X86_REG_EAX,size);current.return_from()
def seek(current):
 global position
 offset=struct.unpack('<i',struct.pack('<I',current.cpu.reg_read(r.UC_X86_REG_EAX)))[0]
 origin=current.cpu.reg_read(r.UC_X86_REG_EDX)
 position=(0,position,len(output))[origin]+offset
 current.cpu.reg_write(r.UC_X86_REG_EAX,position);current.return_from()
def pixel(current):
 stack=current.cpu.reg_read(r.UC_X86_REG_ESP)
 y,x=struct.unpack('<II',current.cpu.mem_read(stack+4,8))
 current.cpu.reg_write(r.UC_X86_REG_EAX,pixels[y*320+x]);current.return_from(8)
im.intercept(0xcc3f8,'Host DOS create in memory; no installation files are written.',create)
im.intercept(0xc8ff0,'Host DOS writes in memory; keep original format writers.',write)
im.intercept(0xcc44c,'Host DOS seek for original header length patching.',seek)
im.intercept(0xcc410,'Host closing the in-memory DOS file.',lambda current:current.return_from())
im.intercept(0xc707c,'Supply the displayed VGA pixel at the hardware read boundary.',pixel)
rng=random.Random(0x544658)
images=[bytes(64000),bytes([255])*64000,bytes(i%256 for i in range(64000)),bytes(i//320%256 for i in range(64000)),bytes((i//8)%2*255 for i in range(64000))]
images += [bytes((i//width)%256 for i in range(64000))for width in (2,3,39,40,41,128)]
images += [rng.randbytes(64000)]
palettes=[bytes(rng.randrange(256)for _ in range(768))for _ in images]
request=b''.join(palette+image for palette,image in zip(palettes,images))
actual=subprocess.check_output([str((a.build/'screenshot_probe').resolve())],input=request)
cursor=0
for index,(palette,image)in enumerate(zip(palettes,images)):
 pixels=image;im.cpu.mem_write(im.data+0x21000,palette)
 im.call(0xdfe64,eax=im.data+0xae02,edx=im.data+0x21000,ebx=1,limit=30000000)
 size,=struct.unpack_from('<I',actual,cursor);cursor+=4
 got=actual[cursor:cursor+size];cursor+=size
 assert got==output,(index,len(got),len(output),[(i,x,y)for i,(x,y)in enumerate(zip(got,output))if x!=y][:20])
 dimensions,decoded,colours=decode_ilbm(got)
 assert dimensions==(320,200)and decoded==image and colours==bytes((value&63)<<2 for value in palette)
assert cursor==len(actual)
print(f'{len(images)} complete original ILBM files agree byte for byte: headers, six-bit DAC colours, all eight bitplanes, row compression and length patching.')
