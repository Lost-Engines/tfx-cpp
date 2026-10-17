#!/usr/bin/env python3
"""Compare the native normal/wide model projection loops and scale propagation.

Native driver reset and missile-nose mode patch the actual projection loop.
The complete B9434 loop executes on supplied Q16 vertices. Actor/camera
translation inputs are supplied at the projection boundary; the original
viewport setter supplies the origin.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xca6fc)
im.call(0xb94da,stack=(105,75,200,180))
for file in (0xb9447,0xb944d,0xb9452):im.cpu.mem_write(im.native(file),bytes(4))
rows=[];expected=[];fixtures=[]
for wide in (0,1):
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 assert im.cpu.mem_read(im.native(0xb9472),1)[0]==8+wide
 for case in range(4096):
  point=[rng.randrange(-1000*65536,1000*65536),rng.randrange(-1000*65536,1000*65536),rng.randrange(17*65536,3000*65536)]
  if case<128:point=[(case%5-2)*64*65536+(case%3-1),(case%7-3)*32*65536+(case%3-1),(17+case%16)*65536]
  im.cpu.mem_write(0x300000,bytes(20)+struct.pack('<3i',*point));im.cpu.reg_write(r.UC_X86_REG_EDI,0x300000);im.call(0xb9434,ecx=1)
  want=list(struct.unpack('<2h',im.cpu.mem_read(0x30000e,4)))
  for scale in (1,.5,.025,.005,.0025,1/7,1/23):
   row=[wide,*point,scale];rows.append(row);expected.append(want)
   if case<32 or case%251==0:fixtures.append(row+want)
output=subprocess.check_output([str((a.build/'aperture_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
for case,(line,want) in enumerate(zip(output,expected)):assert list(map(int,line.split()))==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'8192 complete original normal/missile-nose model projections agree, including all {len(rows)} camera-unit scale cases: native mode reset/patch, signed Q16 shifts, depth truncation and IDIV projection')
