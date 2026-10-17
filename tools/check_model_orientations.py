#!/usr/bin/env python3
"""Compare native SSD constructor angle/size metadata through all six origin/anchor paths.

The actual quarter-turn callback and immediate/queued SSD constructors execute.
The supplied definition/part/actor angles and camera cache are declared inputs;
geometry submission and instance-handle resolution are observed boundaries.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off)
im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(code(0x47c4a),struct.pack('<9h',32767,0,0,0,32767,0,0,0,32767));im.cpu.reg_write(r.UC_X86_REG_ESI,code(0x47c4a));im.call(0xb959f);im.call(0xb9ab9,stack=(0,0,0));im.cpu.mem_write(0x300f00,b'\xc3');im.write(0xac08,'<I',0x300f00)
rng=random.Random(0xb65b0);turns=im.read(0xac1c,'<4I');calls=[]
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==1
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300100);image.return_from()
im.intercept(0xc8568,'Resolve the supplied instance after native part construction.',resolve)
def draw(image):
 sp=image.cpu.reg_read(r.UC_X86_REG_ESP);size,pointer=struct.unpack('<2I',image.cpu.mem_read(sp+4,8));calls.append([*struct.unpack('<3H',image.cpu.mem_read(pointer,6)),size]);image.return_from(20)
for file in (0xcc164,0xcbfec):im.intercept(file,'Observe submitted angle words and signed size byte after the original SSD constructor.',draw)
rows=[];expected=[];fixtures=[]
for case in range(8192):
 actor=[rng.randrange(65536) for _ in range(3)];part=[rng.randrange(65536) for _ in range(3)];mode=(0,1,2,254,255,128,127)[case%7];heading=(case%4)*16384;row=[*actor,*part,mode,heading,int(case%6<4)]
 im.cpu.mem_write(0x300000,bytes(256));im.cpu.mem_write(0x300002,struct.pack('<h',32767));im.cpu.mem_write(0x300100,bytes(64));im.cpu.mem_write(0x30003c,struct.pack('<3H',*part));im.cpu.mem_write(0x300118,bytes([mode]));im.cpu.mem_write(0x300119,struct.pack('<H',77));im.cpu.mem_write(0x30012b,struct.pack('<H',30))
 im.write(0x20bb0,'<3h',0,0,0);im.write(0x20b74,'<3i',0,0,0);im.write(0x20b98,'<I',0x300000);im.write(0x20b9c,'<I',0x300100);im.write(0x20c4a,'<H',1);im.write(0x20baa,'<3H',*actor);im.write(0x20b60,'<3i',0,0,100<<16);im.write(0xac18,'<I',turns[heading//16384]);calls.clear()
 im.call((0xb635c,0xb6438,0xb65b0,0xb668c,0xb6810,0xb68dc)[case%6],eax=0)
 assert len(calls)==1,(case,calls)
 rows.append(row);expected.append(calls[0])
 if case<128 or case%97==0:fixtures.append(row+calls[0])
actual=subprocess.check_output([str((a.build/'model_orientation_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,want) in enumerate(zip(actual,expected)):assert list(map(int,line.split()))==want,(case,rows[case],line,want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 native SSD orientations agree: all six immediate, queued and special origin/anchor constructors, additive actor/component Euler words, all quarter turns, ignored unrotated metadata and signed size flags')
