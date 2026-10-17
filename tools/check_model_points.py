#!/usr/bin/env python3
"""Compare complete native one/two-pixel distant-model frames."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=1024);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,4096);rng=random.Random(0xbb021)
code=lambda off:im.native(0x70aa4+off)
im.cpu.mem_write(im.data+0x24c9c,bytes(range(256)));rows=[]
word=lambda v:((v+32768)&65535)-32768
wrap=lambda v:((v+2147483648)&4294967295)-2147483648
for case in range(a.cases):
 wide=case%2;size=1+(case//2)%2;colour=rng.randrange(256);ox,oy=(160,100) if case<128 else (rng.randrange(-32768,32768),rng.randrange(-32768,32768));minimum=[0,0];maximum=[319,199]
 if case%5==0:minimum=[30,40];maximum=[110,120]
 x=rng.choice((-1,0,1,30,110,318,319,320));y=rng.choice((-1,0,1,40,120,198,199,200));depth=rng.choice((-32768,-1,0,15,16,17,18,31,256,1000,16384,32767));shift=9 if wide else 8
 point=[wrap(word(x-ox)*depth*(1<<shift)+rng.randrange(256)),wrap(word(y-oy)*depth*(1<<shift)+rng.randrange(256)),wrap(depth*65536+rng.randrange(65536))]
 # Exclude the original IDIV trap domain; it has no defined VGA result.
 if depth>16 and any(abs(v>>8)//depth>32767 for v in point[:2]):continue
 rows.append([wide,size,colour,ox,oy,*minimum,*maximum,*point])
output=subprocess.check_output([str((a.build/'model_point_probe').resolve()),'--pixels'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode());assert len(output)==64000*len(rows);fixtures=[]
for case,row in enumerate(rows):
 wide,size,colour,ox,oy,mx,my,hx,hy,*point=row
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=(ox&0xffffffff,oy&0xffffffff,hx,hy))
 for off,value in zip((0x5212e,0x5269e,0x52c0e),point):im.cpu.mem_write(code(off),struct.pack('<i',value))
 im.cpu.mem_write(code(0x51396),bytes([0]));im.cpu.mem_write(0x300000,bytes([colour,0]));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000);im.cpu.reg_write(r.UC_X86_REG_EDI,0);vga.reset()
 for plane in vga.planes:plane[:]=bytes([99])*16000
 im.call(0xbb021 if size==2 else 0xbb094,limit=100000);want=bytes(vga.pixels());got=output[case*64000:(case+1)*64000]
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y];raise AssertionError((case,row,differences[:20]))
 if case<128 or case%31==0:
  digest=14695981039346656037
  for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append(row+[digest])
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original distant-model frames agree: one/two-pixel representations, normal/wide projection, anchor clipping, origin-word wrap, near exclusion and VGA edge writes')
