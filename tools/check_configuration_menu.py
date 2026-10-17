#!/usr/bin/env python3
"""Compare complete native option-dialog construction, selections and pixels.

The original dialogs, widget painters and selection helpers execute. Device
input/cursor, physical page switching and allocation are explicit boundaries.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_configuration_menu import menu_image
from native_reference import r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args()
path=a.research/'installs/cd_1994_09/TFX/TFX.DAT'
rng=random.Random(0x94448)
fbits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
rows=[]
for index in range(72):
 model=[0,1,2,6][index%4]
 page=(index//4)%3
 fields=[model,(index//12)%3,(index//36)%3,fbits([0,512,999][index%3]),125,index%3,1,1,1,0,1,index%2]
 rows.append(fields+[page,999])
for page,count in [(0,19),(1,13)]:
 for action in range(count):
  for repeat in range(4):
   model=[0,1,2,6][repeat]
   fields=[model,rng.randrange(3),rng.randrange(3),fbits(rng.choice([0.,5.,512.,995.,999.])),96,rng.randrange(3),rng.randrange(2),rng.randrange(2),rng.randrange(2),rng.randrange(2),rng.randrange(2),rng.randrange(2)]
   rows.append(fields+[page,action])
output=subprocess.check_output([str((a.build/'configuration_menu_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode())
position=0
for index,row in enumerate(rows):
 values,page,action=row[:12],row[12],row[13]
 end=output.index(b'\n',position)
 state=list(map(int,output[position:end].split()))
 pixels=output[end+1:end+1+64000]
 position=end+1+64000
 im,vga,pointers=menu_image(path,values,page)
 if action!=999:
  # These cases exercise individual preference controls, without completing a
  # dialog or replacing a page. Their native widget activation is the input.
  im.cpu.mem_write(pointers[action]+16,b'\1')
  start,stop=(0x942ef,0x943a4) if page else (0x947fc,0x94a07)
  im.cpu.emu_start(im.native(start),im.native(stop),count=3000000)
  assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(stop)
 offsets=[(0x1347a,'<B'),(0x13478,'<B'),(0x8864,'<B'),(0xac68,'<I')]+[(f,'<B') for f in (0x5954,0x8f31,0x8e22,0x8e23,0x8e25,0x8f30,0x8867)]
 expected=[im.read(offset,fmt)[0] for offset,fmt in offsets]+[page,0]
 assert state==expected,(index,row,state,expected)
 native=vga.pixels()
 assert pixels==native,(index,row,[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(pixels,native)) if x!=y][:30],sum(x!=y for x,y in zip(pixels,native)))
assert position==len(output)
print(f'{len(rows)} complete native dialog states and 64000-pixel frames agree: all three pages, four models, input selection/restoration, sensitivity limits, detail, recovery and every realism selection')
