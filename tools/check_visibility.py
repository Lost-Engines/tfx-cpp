#!/usr/bin/env python3
"""Compare complete native integer sphere visibility and world transformation.

Original camera matrix/translation setters and 0xcbef0/0xb9c00 execute without
interception. Synthetic poses, centres and radii exercise viewport-patched apertures,
behind-camera overlap, word wrapping, signed ABS and zero-depth guards.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xcbef0);rows=[];expected=[];fixture=[]
identity=[32767,0,0,0,32767,0,0,0,32767];matrix_at=im.native(0x70aa4+0x47c4a)
for case in range(16384):
 if case<512:
  radius=(0,1,16,32,100,4000,32767,-32768)[case%8];matrix=identity;camera=[0,0,0];point=[(-10000,-100,-1,0,1,100,10000)[case//8%7],(-1000,-1,0,1,1000)[case//56%5],(-32768,-100,-17,-16,-15,-1,0,1,15,16,17,100,20000,32767)[case//40%14]];origin=[159,99]
 else:
  radius=rng.choice((-32768,-32767,-100,-1,0,1,16,32,100,1000,4000,32767,rng.randrange(-32768,32768)))
  matrix=identity if case%7==0 else [rng.randrange(-32768,32768) for _ in range(9)]
  camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)];point=[rng.randrange(-2147483648,2147483648) for _ in range(3)];origin=[rng.randrange(-32768,32768),rng.randrange(-32768,32768)]
 maximum=[319,199] if case<512 or case%3 else [rng.randrange(-32768,32768),rng.randrange(-32768,32768)]
 row=[radius,*matrix,*camera,*point,*origin,*maximum];rows.append(row)
 im.cpu.mem_write(matrix_at,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_at);im.call(0xb959f)
 im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)));im.call(0xb94da,stack=tuple(v&0xffffffff for v in (*origin,*maximum)))
 visible=int(bool(im.call(0xcbef0,stack=tuple(v&0xffffffff for v in (radius,*reversed(point),0x300000)))));expected.append(visible)
 if case<256 or case>=512 and case%97==0:fixture.append(row+[visible])
result=subprocess.check_output([str((a.build/'visibility_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert int(line)==value,(case,rows[case],line,value)
assert set(expected)=={0,1}
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
print('16384 complete original sphere visibility cases agree: world transform, viewport-patched aperture, signed radius/ABS quirks, near/far and behind-camera overlap, wrapped centres and zero-depth division guards')
