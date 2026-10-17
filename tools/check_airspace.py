#!/usr/bin/env python3
"""Compare the complete native airspace boundary, warnings and penalty handler."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--save-fixture',type=Path)
a = p.parse_args()
im = NativeReference(a.data_dir/'TFX.DAT')
notices=[]
def notice(current,kind):
 caller=struct.unpack('<I',current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_ESP),4))[0]
 if kind==1 and caller==current.native(0x8125c):return
 notices.append(kind)
for address,kind in ((0x81198,1),(0x81254,2)):
 im.intercept(address,'Observe public radio warning requests, excluding the persistent wrapper internal call; original builders execute.',lambda current,kind=kind:notice(current,kind))
rng=random.Random(0x71d74)
rows=[];expected=[]
positions=[cell*2048+delta for cell in (-32769,-32768,-3,-2,-1,0,1,2,197,198,199,200,201,202,32767,32768) for delta in (-1,0,1,2047)]
for case in range(4096):
 x=rng.choice(positions) if case<2048 else rng.randrange(-2147483648,2147483648)
 z=rng.choice(positions) if case<2048 else rng.randrange(-2147483648,2147483648)
 outside=case%2;violations=rng.choice((-32768,-1,0,1,32767));exit_ticks=rng.choice((-32768,0,1,540,810,32767));requested=case//2%2;active=requested and case//4%2;idle=case//8%2
 row=[x,z,outside,violations,exit_ticks,requested,active,idle]
 for at,fmt,value in ((0x13424,'<i',x),(0x1343c,'<i',z),(0x5948,'<H',outside),(0xe75c,'<h',violations),(0x5940,'<h',exit_ticks),(0x13248,'<H',requested),(0xe780,'<B',active),(0x7612,'<B',idle)):
  im.write(at,fmt,value)
 notices.clear();im.call(0x71d74)
 assert len(notices)<=1,notices
 result=[im.read(at,fmt)[0] for at,fmt in ((0x5948,'<H'),(0xe75c,'<h'),(0x5940,'<h'),(0x13248,'<H'),(0xe780,'<B'),(0x7612,'<B'))]+[notices[0] if notices else 0]
 rows.append(row);expected.append(result)
request=''.join(' '.join(map(str,row))+'\n' for row in rows)
output=subprocess.check_output([str((a.build/'airspace_probe').resolve())],input=request.encode()).decode().splitlines()
assert len(output)==len(expected)
for source,want,line in zip(rows,expected,output):
 got=list(map(int,line.split()))
 assert got==want,(source,got,want)
if a.save_fixture:
 # Retain threshold and wrap neighbours without duplicating the full random corpus.
 indices=list(range(0,len(rows),17))
 a.save_fixture.write_text(''.join(' '.join(map(str,rows[i]+expected[i]))+'\n' for i in indices))
 subprocess.run([str((a.build/'airspace_probe').resolve()),str(a.save_fixture)],check=True)
print(f'{len(rows)} complete original airspace checks agree: signed cell limits, warnings, retained departure, penalties and acceleration cancellation')
