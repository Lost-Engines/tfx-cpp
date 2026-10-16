#!/usr/bin/env python3
"""Compare the complete original player tail, including native movement norm.

0x8f98c..0x8fac4 executes without intercepted dependencies. Only the input
callback outputs, previous position and saved fuel gauge are supplied.
"""
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x8f98c)
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
cases=[]
for i in range(8192):
 before,burn,after=[rng.randrange(-32768,32768) for _ in range(3)]
 old=[rng.uniform(-100000,100000) for _ in range(3)];new=[v+rng.uniform(-100,100) for v in old]
 row=[rng.choice([0,1,2,4,18,65535]),i%2,(i//2)%2,rng.randrange(-32768,32768),rng.randrange(-32768,32768),rng.randrange(3),before,burn,after,*map(fbits,old+new),*[bits(rng.choice([0.,-0.,.5,1.,float('nan')])) for _ in range(2)]]
 cases.append(row)
output=subprocess.check_output([str((a.build/'player_frame_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
 elapsed,terrain,landed,height,down,collision,before,burn,after=row[:9]
 for f,v,fmt in ((0x1347a,6,'<B'),(0x1347b,255,'<B'),(0x13476,elapsed,'<H'),(0xabea,terrain,'<B'),(0x8d3a,landed,'<H'),(0xabf2,height,'<h'),(0x13466,down,'<h'),(0x12c04,collision,'<h'),(0x6c3a,burn,'<h'),(0x6c3c,after,'<h')):im.write(f,fmt,v)
 for f,v in zip((0x133e0,0x133e4,0x133dc,0x1341c,0x13428,0x13434),row[9:15]):im.write(f,'<I',v)
 im.write(0x14880,'<2Q',*row[15:17]);im.cpu.reg_write(r.UC_X86_REG_EBX,before&65535);im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x8f98c),im.native(0x8fac4),count=10000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8fac4)
 expected=[im.read(f,fmt)[0] for f,fmt in ((0x13428,'<I'),(0x12c04,'<h'),(0x7d72,'<B'),(0x7d75,'<B'),(0x6c3c,'<h'),(0x6c3a,'<h'),(0x133f0,'<i'))]+[int(im.read(0x1347b,'<B')[0]!=6)]
 actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
 if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(cases)} complete original player-frame tails agree: collision clamp, engine indicators, signed fuel smoothing, measured speed and model acknowledgement; no numerical dependencies intercepted')
