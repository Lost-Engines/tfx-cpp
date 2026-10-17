#!/usr/bin/env python3
"""Compare the complete original sunlight/flak-flash producer and point projector.

Synthetic camera matrices, anchors, viewport bounds and pending flak/cloud/view
state are supplied. Original matrix/translation/viewport setters, projection,
cloud/view gates, signed-word distance arithmetic and flash selection execute
without interception. No installation is modified.
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
a=p.parse_args();im=NativeReference(a.data_dir/'TFX.DAT');rng=random.Random(0x73838)
rows=[];expected=[];fixture=[]
matrix_at=im.native(0x70aa4+0x47c4a)
for case in range(8192):
 if case<512:
  flak=0;cloud=0;layer=0;view=0;anchor=[0,0,0];minimum=[0,0];maximum=[319,199];origin=[159,56];camera=[0,0,0]
  # Exercise every glare-distance level around a visible, centred sun, then
  # perturb vertical displacement; arbitrary matrix rows are legal setter input.
  matrix=[32767,0,(case%128-64)*256,0,-32767,32767+(case//128)*-2000,0,-32767,-32767]
 else:
  flak=int(case%11==0);cloud=int(case%3==0);layer=rng.choice((-32768,-2400,-500,0,32767));view=rng.choice((0,0,3,4,9,19,28,28))
  anchor=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
  if case%2:anchor=[rng.randrange(-30000,30000),rng.randrange(-3000,1),rng.randrange(-30000,30000)]
  minimum=[0,0];maximum=[319,rng.choice((56,112,140,198,199))];origin=[159,rng.choice((28,56,70,99))]
  if case%13==0:minimum=[-32768,-32768];maximum=[32767,32767];origin=[rng.randrange(-32768,32768),rng.randrange(-32768,32768)]
  matrix=[rng.randrange(-32768,32768) for _ in range(9)]
  camera=[struct.unpack('<i',struct.pack('<I',(v<<16)&0xffffffff))[0] for v in anchor]
  if case%7==0:camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 row=[flak,cloud,layer,view,*anchor,*minimum,*maximum,*matrix,*camera,*origin];rows.append(row)
 im.cpu.mem_write(matrix_at,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_at);im.call(0xb959f)
 im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)))
 im.call(0xb9238,stack=tuple(v&0xffffffff for v in (minimum[0],maximum[0],minimum[1],maximum[1])))
 im.call(0xb94da,stack=tuple(v&0xffffffff for v in (*origin,*maximum)))
 for at,value in zip((0x134f0,0x134f8,0x13500),anchor):im.write(at,'<i',value)
 im.write(0x5d8c,'<B',flak);im.write(0xe762,'<H',cloud);im.write(0xe75a,'<h',layer);im.write(0x87b6,'<H',view)
 im.call(0x73838);assert im.read(0x5d8c,'<B')[0]==0
 level=im.read(0x10beb,'<B')[0];expected.append(level)
 if case<256 or (case>=512 and case%97==0):fixture.append(row+[level])
result=subprocess.check_output([str((a.build/'glare_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,level) in enumerate(zip(result,expected)):assert int(line)==level,(case,rows[case],line,level)
assert set(range(1,51))<=set(expected)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
print('8192 complete original sunlight/flak-flash cases agree: all 50 glare levels, real word-coordinate projection, clouds, target view, viewport edges, pending-flak precedence and wrapped signed-distance quirks')
