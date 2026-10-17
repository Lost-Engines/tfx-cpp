#!/usr/bin/env python3
"""Compare complete original horizon frames through actual clipping and VGA writes.

Original band production, integer polygon clipping, edge construction, solid
scan conversion and VGA writes execute. The capture supplies camera, viewport,
retained ground phase and video aperture. No drawing callback is replaced.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--wide',action='store_true')
p.add_argument('--cases',type=int,default=192)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);rng=random.Random(0xcaf842)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
if a.wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
rows=[]
angles=(0,1,0x1aa0,0x1aa1,0x3000,0x3001,0x4000,0x6000,0x8000,0xc000,0xffff)
rolls=(0,0x2000,0x4000,0x6000,0x8000,0xa000,0xc000,0xe000)
for case in range(a.cases):
 pitch=angles[case%len(angles)] if case<88 else rng.randrange(65536);roll=rolls[case//len(angles)] if case<88 else rng.randrange(65536)
 height=rng.choice((-32768,-4000,-1000,-32,0));phase=rng.choice((0,1,1374,1375));minimum=[0,0];maximum=[319,rng.choice((112,140,199))];origin=rng.choice((56,70,99))
 if case%9==0:minimum=[32,24];maximum=[287,175]
 rows.append([pitch,roll,height,phase,*minimum,*maximum,origin])
output=subprocess.check_output([str((a.build/'horizon_probe').resolve()),'--pixels-wide' if a.wide else '--pixels'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode());assert len(output)==len(rows)*64000
fixtures=[]
for case,row in enumerate(rows):
 pitch,roll,height,phase,mx,my,hx,hy,origin=row
 im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=((mx+hx)//2,origin,hx,hy));im.call(0xc84b1,stack=(mx,hx,my,hy,origin));im.call(0xb9a6c,stack=(0,height&0xffffffff,0));im.write(0xad7c,'<h',phase)
 video.reset()
 for plane in video.planes:plane[:]=bytes([77])*16000
 im.call(0xcaf84,eax=pitch,edx=roll,limit=10000000)
 want=bytes(video.pixels());got=output[case*64000:(case+1)*64000]
 if want!=got:
  differences=[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y]
  raise AssertionError((case,row,len(differences),differences[:50]))
 if case<64 or case%47==0:
  digest=14695981039346656037
  for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixtures.append([int(a.wide),*row,digest])
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete native horizon VGA frames agree pixel for pixel: original band projection, signed clipping, reciprocal/half-step edges, inclusive spans, bank/inversion, cockpit and partial viewports')
