#!/usr/bin/env python3
"""Compare the original PLOP dispatcher, including consumed makes and notices."""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000,4096);im.write(0x1b238,'<I',0x300000);im.write(0x1b23c,'<I',0x300100)
im.write(0x777e,'<H',0);im.write(0x13250,'<H',0)
notices=[]
im.intercept(0x81198,'Observe the radio notice without replacing the cheat dispatcher.',lambda current:(notices.append(current.cpu.reg_read(r.UC_X86_REG_EAX)-current.data),current.return_from()))
rng=random.Random(0x838dc);rows=[]
for sequence in range(256):
 rows.extend([[key,1]for key in (1,2,3,1)])
 rows.extend([[rng.randrange(5),rng.randrange(2)]for _ in range(12)])
actual=subprocess.check_output([str((a.build/'cheat_probe').resolve())],input=''.join(f'{key} {shift}\n'for key,shift in rows).encode()).decode().splitlines()
assert len(actual)==len(rows)
scans=(0,0x19,0x26,0x18,0x10);changes=0
for index,((key,shift),line)in enumerate(zip(rows,actual)):
 prior=im.read(0x13250,'<H')[0];notices.clear()
 im.cpu.mem_write(0x300000,bytes([scans[key]]));im.cpu.mem_write(0x300100+0x36,bytes([shift]));im.call(0x838dc)
 enabled=im.read(0x13250,'<H')[0];matched=im.read(0x777e,'<H')[0]
 expected=[int(key!=0 and im.cpu.mem_read(0x300000,1)[0]==0),enabled,matched]
 assert list(map(int,line.split()))==expected,(index,rows[max(0,index-4):index+1],line,expected)
 assert notices==([0x18ac if enabled else 0x18bc]if prior!=enabled else []),(index,notices)
 changes+=prior!=enabled
assert changes>200
print(f'{len(rows)} original cheat inputs agree: consumed makes, partial progress, right-Shift gating, {changes} toggles and exact notice requests.')
