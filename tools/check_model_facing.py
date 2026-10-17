#!/usr/bin/env python3
"""Compare the complete original model-facing bytecode branch in both paths.

Native BB81C executes with supplied Q16 camera vertices, projection flags and
screen words. Near cases exercise its entire 3D fallback. Projected cases use
original B9434 projection and the real normal/wide mode and origin setters.
The branch destination is observed before the next bytecode dispatch.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xbb81c);answers=[]
code=lambda off:im.native(0x70aa4+off)
def capture(value):
 def callback(image):answers.append(value);image.return_from()
 return callback
for address,value in [(0xbb574,1),(0xbb882,0),(0xbba43,0)]:im.intercept(address,'Observe the completed native model-facing branch before bytecode dispatch.',capture(value))
for file in (0xb9447,0xb944d,0xb9452):im.cpu.mem_write(im.native(file),bytes(4))
rows=[];expected=[];fixtures=[]
for case in range(16384):
 wide=(case//2)%2;scale=(1,.5,.025,.0025,1/7)[case%5];origin=[159,99] if case<4096 else [rng.randrange(-32768,32768),rng.randrange(-32768,32768)]
 points=[]
 for vertex in range(3):
  if case%2==0:
   point=[rng.randrange(-2100*65536,2100*65536),rng.randrange(-2100*65536,2100*65536),rng.randrange(17*65536,3000*65536)]
  else:
   point=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
   if vertex==0:point[2]=rng.randrange(-32768*65536,17*65536)
  points.append(point)
 if case%13==0:points[2]=list(points[1])
 row=[wide,scale,*origin,*[value for point in points for value in point]];rows.append(row)
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb94da,stack=(*[v&0xffffffff for v in origin],319,199))
 for i,point in enumerate(points):
  im.cpu.mem_write(code(0x6814c+i*32),struct.pack('<3iH',*point,65535 if point[2]>>16<=16 else 0)+bytes(6)+struct.pack('<3i',*point))
 if case%2==0:
  im.cpu.reg_write(r.UC_X86_REG_EDI,code(0x6814c));im.call(0xb9434,ecx=3)
 im.cpu.mem_write(0x300000,struct.pack('<3H',0,32,64));im.cpu.reg_write(r.UC_X86_REG_ESI,0x300000);answers.clear();im.call(0xbb81c,limit=10000)
 assert len(answers)==1;value=answers[0];expected.append(value)
 if case<128 or case%97==0:fixtures.append(row+[value])
actual=subprocess.check_output([str((a.build/'model_facing_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,want) in enumerate(zip(actual,expected)):assert int(line)==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('16384 complete native model-facing branches agree: signed screen-word/dword determinant, near-vertex 3D plane normal, shared normalization shifts, negated second-vertex WORD wrap, wrapped dot product, degeneracies and normal/wide camera units')
