#!/usr/bin/env python3
"""Compare complete native position->camera cache->queued colour-row delivery.

Original word/fixed sphere transform, matrix/translation setup, CC0BF/CC164 cached
model queue and C4930 sort submission execute. Model-handle resolution supplies
one synthetic header; camera/point/viewport/parameters are declared inputs.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xcbf58)
code=lambda off:im.native(0x70aa4+off)
def header(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==77
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300200);image.return_from()
im.intercept(0xc8568,'Resolve the supplied model handle to a synthetic zero-bias header; original queue arithmetic and sort insertion still execute.',header)
im.cpu.mem_write(0x300200,bytes(32));im.cpu.mem_write(0x300100,bytes(16));im.call(0xc54f6,stack=(9,));im.call(0xb94da,stack=(159,99,319,199));rows=[];expected=[];fixtures=[]
for case in range(8192):
 fixed=case%2;matrix=[32767,0,0,0,32767,0,0,0,32767] if case<128 else [rng.randrange(-32768,32768) for _ in range(9)]
 camera=[0,0,0] if case<128 else [rng.randrange(-2147483648,2147483648) for _ in range(3)]
 point=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 if case<128:
  point=[0,0,(case//2-32)*1024]
  if fixed:point=[v*65536 for v in point]
 row=[fixed,*matrix,*camera,*point];rows.append(row)
 matrix_at=code(0x47c4a);im.cpu.mem_write(matrix_at,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_at);im.call(0xb959f)
 im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)))
 im.call(0xcbf24 if fixed else 0xcbef0,stack=tuple(v&0xffffffff for v in (32767,*reversed(point),0x300000)))
 raw=list(struct.unpack('<3i',im.cpu.mem_read(0x300000,12)))
 im.call(0xc488d)
 if fixed:im.call(0xcc164,stack=(1,0x300300,0x300000,0x300100,77))
 else:im.call(0xcc0bf,stack=(0x300000,0x300100,77))
 value=im.cpu.mem_read(code(0x51396),1)[0];want=raw+[value];expected.append(want)
 if case<128 or case%97==0:fixtures.append(row+want)
actual=subprocess.check_output([str((a.build/'colour_remap_probe').resolve()),'--placement'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,want) in enumerate(zip(actual,expected)):assert list(map(int,line.split()))==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 complete native placed-model colour deliveries agree: word/fixed camera transforms, retained camera cache, actual model queue and depth-row selection; the shared camera adapter round-trips signed Q16 poses and Q15 rows')
