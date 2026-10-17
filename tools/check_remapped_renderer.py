#!/usr/bin/env python3
"""Compare remapped flat/circle frames and shaded/textured interior samples.

Original colour lookup, integer flat/circle raster, Gouraud and texture painters
execute through VGA writes. Real coltab rows, synthetic constant textures and
supplied screen vertices are inputs. General shaded/texture edges remain a
separate gate; their interiors test lookup ordering independently of coverage.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x50000)
code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000);im.call(0xb9238,stack=(0,319,0,199))
im.cpu.mem_write(code(0x47cea),bytes(im.cpu.mem_read(code(0x68106),4)));im.cpu.mem_write(code(0x4787a),struct.pack('<I',0x300000));im.cpu.mem_write(code(0x4787e),struct.pack('<I',0x330000));im.cpu.mem_write(0x340000,struct.pack('<4H',0,32,64,96))
root=(a.research/'extracted/cd_1994_09/resources/_unknown/7764422a-3311.bin').read_bytes();assert len(root)==4096
rows=[]
for row in range(16):
 for kind in (0,1,3):
  for colour in (0,1,15,17,19,112,224,255):rows.append([kind,row,colour,0,0])
 for gradient in range(4):rows.append([2,row,0,0,gradient])
 rows.extend(([3,row,0,1,0],[3,row,19,2,0]))
output=subprocess.check_output([str((a.build/'remap_renderer_probe').resolve()),str(a.research/'installs/cd_1994_09/TFX')],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode());assert len(output)==len(rows)*64000
shades=([192]*4,[192,207,207,192],[192,192,207,207],[192,207,200,197]);whole=interiors=0
for case,row in enumerate(rows):
 kind,bank,colour,override,gradient=row;remap=bytearray(root[bank*256:(bank+1)*256])
 if override==1:remap[0]=77
 if override==2:remap[19]=0
 im.cpu.mem_write(0x330000,bytes(remap));vga.reset()
 for plane in vga.planes:plane[:]=bytes([199])*16000
 if kind in (0,1):
  im.cpu.mem_write(0x340100,struct.pack('<H',colour));im.cpu.reg_write(r.UC_X86_REG_ESI,0x340100);im.call(0xbbbb0)
 if kind==1:
  im.cpu.mem_write(im.STACK,struct.pack('<I3H',im.RETURN,80,80,40));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.emu_start(im.native(0xbfd0e),im.RETURN,count=1000000)
 else:
  left,top,right,bottom=(32,32,128,128) if kind==0 else (20,20,100,100)
  for i,(x,y) in enumerate(((left,top),(right,top),(right,bottom),(left,bottom))):im.cpu.mem_write(code(0x6815a+i*32),struct.pack('<2h',x,y))
  if kind==2:im.cpu.mem_write(code(0x47fac),struct.pack('<4I',*[value<<8 for value in shades[gradient]]))
  if kind==3:
   im.cpu.mem_write(0x300000,bytes([colour])*49152);im.cpu.mem_write(code(0x481ac),bytes(20))
  im.cpu.reg_write(r.UC_X86_REG_ESI,0x340000);im.call(0xbd3a8 if kind==0 else 0xbd95c if kind==2 else 0xbdc38,ecx=4,limit=1000000)
 want=bytes(vga.pixels());got=output[case*64000:(case+1)*64000]
 if kind in (0,1):positions=range(64000);whole+=1
 else:positions=[y*320+x for y in range(25,96) for x in range(25,96)];interiors+=len(positions)
 differences=[(i%320,i//320,got[i],want[i]) for i in positions if got[i]!=want[i]]
 assert not differences,(case,row,len(differences),differences[:25])
print(f'{whole} complete remapped native flat/circle frames and {interiors} Gouraud/texture interior pixels agree across all sixteen actual coltab rows, including raw-zero-to-visible and nonzero-to-transparent texture overrides')
