#!/usr/bin/env python3
"""Compare complete original gear damage, descent stores and ordered audio.

Original 0x8d7ec executes with supplied aircraft limits and touchdown state.
Only sample delivery is intercepted; it does not modify gear or flight state.
"""
import argparse
from collections import Counter
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);sounds=[]
im.intercept(0xa4dfc,'Observe original gear warning/failure sample requests; audio delivery does not change gear state',lambda image:(sounds.append(image.cpu.reg_read(r.UC_X86_REG_EAX)),image.return_from()))
rng=random.Random(0x8d7ec);bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];cases=[]
for index in range(8192):
    air,ground,sink=[(200,87.5,3.1),(205,120,5),(160,110,3.05),(50,60,3.5)][index%4]
    speed=[0,ground-.001,ground,ground+.001,ground*1.4,ground*1.4+.001,air,air+.001,air*1.4,air*1.4+.001][index%10]
    cases.append([int(index%7!=0),[0,1,2,11,14][index%5],bits(rng.uniform(-500,500)),rng.choice([-32768,-32767,-1024,0,1024,32767]),bits(speed),int(index&16!=0),int(index&32!=0),air,ground,sink])
output=subprocess.check_output([str((a.build/'landing_gear_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];counts=Counter()
for index,(row,line) in enumerate(zip(cases,output)):
    down,condition,vertical,forward,speed,landed,previous,air,ground,sink=row
    im.write(0x146d8,'<d',float(down));im.write(0x7d7a,'<B',condition);im.write(0x133ec,'<I',vertical);im.write(0x13468,'<h',forward);im.write(0x133e8,'<I',speed);im.write(0x8d3a,'<H',landed);im.write(0x86b4,'<H',previous);im.write(0x14550,'<d',air);im.write(0x14560,'<d',ground);im.write(0x14568,'<d',sink);sounds.clear()
    im.call(0x8d7ec)
    expected=[int(im.read(0x146d8,'<d')[0]!=0),im.read(0x7d7a,'<B')[0],im.read(0x133ec,'<I')[0],len(sounds),*sounds];actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
    counts[tuple(sounds)]+=1
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Landing gear agrees in {len(cases)} original state/float-bit/audio updates; request sequences: {dict(counts)}')
