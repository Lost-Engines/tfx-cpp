#!/usr/bin/env python3
"""Compare native virtual-stick range constraint and relative mouse updates."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0x7459c);deltas=[0,0]
im.intercept(0xc733e,'Supply host mouse buttons; range and accumulation execute',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
def sample(image):
 x,y=struct.unpack('<2I',image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_ESP)+4,8))
 image.cpu.mem_write(x,struct.pack('<h',deltas[0]));image.cpu.mem_write(y,struct.pack('<h',deltas[1]));image.return_from()
im.intercept(0xc7326,'Supply relative host mouse samples',sample)
im.call(0x7457c,eax=0xfffffe00,edx=0xfffffe00,ebx=512,ecx=512)
rows=[[rng.randrange(-32768,32768),rng.randrange(-32768,32768),int(i%64==0),rng.randrange(-32768,32768),rng.randrange(-32768,32768)] for i in range(8192)]
output=subprocess.check_output([str((a.build/'mouse_input_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
fixtures=[]
for index,(row,line) in enumerate(zip(rows,output)):
 x,y,reset,initial_x,initial_y=row
 if reset:im.write(0x5964,'<2h',initial_x,initial_y)
 deltas[:]=[x,y];im.call(0x7459c);im.call(0x74508)
 expected=list(im.read(0x5964,'<2h'));actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
 if index<256:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(rows)} original relative mouse updates agree, including virtual-stick bounds, asymmetric axis clamping and signed-word wrap; only host mouse/button sampling is supplied')
