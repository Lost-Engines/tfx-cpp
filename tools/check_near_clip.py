#!/usr/bin/env python3
"""Compare complete original near-plane midpoint search and clipped projection.

D7D22 and D7C90 execute without arithmetic interception. Q16 endpoint records,
viewport origin and normal/missile mode are supplied. The first call binds the
same endpoint-offset operands as its real D7C90 caller; that caller then runs
in full and supplies its own bindings for the projected-coordinate capture.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xd7d22)
code=lambda off:im.native(0x70aa4+off)
rows=[];expected=[];fixtures=[]
for case in range(16384):
 za=rng.choice((-32768,-30000,-1,0,1,15,16)) if case<2048 else rng.randrange(-32768,17)
 zb=rng.choice((17,18,100,1000,16000,30000,32767)) if case<2048 else rng.randrange(17,32768)
 outside=[rng.randrange(-2147483648,2147483648),rng.randrange(-2147483648,2147483648),za*65536+rng.randrange(65536)]
 inside=[rng.randrange(-2147483648,2147483648),rng.randrange(-2147483648,2147483648),zb*65536+rng.randrange(65536)]
 wide=case%2;origin=[rng.randrange(-32768,32768),rng.randrange(-32768,32768)]
 if case<128:
  limit=(4060 if wide else 2030)*65536
  outside[0]=rng.choice((-limit-1,-limit,-limit+1,-1,0,1,limit-1,limit,limit+1));outside[2]=16*65536+case
 row=[*outside,*inside,wide,*origin];rows.append(row)
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb94da,stack=(*[v&0xffffffff for v in origin],319,199))
 im.cpu.mem_write(code(0x6814c),struct.pack('<3i',*outside));im.cpu.mem_write(code(0x6814c+32),struct.pack('<3i',*inside))
 im.cpu.mem_write(im.native(0xd8033),struct.pack('<I',0));im.cpu.mem_write(im.native(0xd8044),struct.pack('<I',32))
 im.call(0xd7d22,eax=0,ebx=32,limit=10000)
 raw=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(register)))[0] for register in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX)]
 im.cpu.reg_write(r.UC_X86_REG_EDI,0x300000);im.call(0xd7c90,eax=0,ebx=32,limit=10000)
 screen=list(struct.unpack('<2h',im.cpu.mem_read(0x300000,4)));want=raw+screen;expected.append(want)
 if case<128 or case%97==0:fixtures.append(row+want)
actual=subprocess.check_output([str((a.build/'near_clip_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,want) in enumerate(zip(actual,expected)):assert list(map(int,line.split()))==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('16384 complete original near-plane edge intersections and projections agree: signed-word midpoint search, sentinel/equality path, wrapped Q16 midpoint replay, normal/wide shifts, saturation without origin addition and screen-word wrapping')
