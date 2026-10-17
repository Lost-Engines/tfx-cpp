#!/usr/bin/env python3
"""Compare original persistent keyboard polling and both pan flag producers.

Only the hardware key-state bytes are supplied. Both original polling bodies
execute, including modifier/automatic-landing retention and independent O.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000,4096);im.write(0x1b23c,'<I',0x300000)
for field in (0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260,0x13244):im.write(field,'<H',0)
im.write(0x1358a,'<2B',0,0)
rng=random.Random(0x86458)
rows=list(range(16384));rng.shuffle(rows)
actual=subprocess.check_output([str((a.build/'keyboard_probe').resolve())],input=''.join(f'{mask}\n'for mask in rows).encode()).decode().splitlines()
assert len(actual)==len(rows)
for index,(mask,line)in enumerate(zip(rows,actual)):
 raw=bytearray(128)
 for bit,scan in enumerate((0x48,0x4b,0x50,0x4d,0x47,0x4f,0x49,0x51,0x0d,0x0c,0x18,0x36,0x1d)):
  raw[scan]=(mask>>bit)&1
 im.cpu.mem_write(0x300000,bytes(raw));im.write(0x86cf,'<B',(mask>>13)&1)
 im.call(0x862f4);im.call(0x86458)
 expected=[im.read(field,'<H')[0]for field in (0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260,0x13244)]+list(im.read(0x1358a,'<2B'))
 assert list(map(int,line.split()))==expected,(index,mask,line,expected)
print(f'{len(rows)} original persistent keyboard polls agree: all held combinations, right-Shift/Ctrl pan, suspended manual flags, independent O and automatic landing.')
