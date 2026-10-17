#!/usr/bin/env python3
"""Compare persistent original cockpit positioning with interrupted flak shake.

All positioning callbacks and original key/setup helpers execute. No numerical
or state changes are intercepted. The probe loads its tables from TFX.DAT;
complete panel painting and projection have separate native comparisons.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();im=NativeReference(a.data_dir/'TFX.DAT');rng=random.Random(0x7d94c)
im.write(0x10be8,'<h',0);im.write(0x10be6,'<h',28);im.write(0x12bf8,'<H',0)
im.write(0x6056,'<H',0);im.write(0x6058,'<2h',-1,-1);im.write(0xe70c,'<I',im.native(0x70b44))
callbacks={im.native(0x70b44):(0,None),im.native(0x7d82c):(1,0x7d82c),im.native(0x7d8bc):(2,0x7d8bc),im.native(0x7d94c):(3,0x7d94c)}
rows=[];expected=[]
for case in range(8192):
 if case<64:
  action=3 if case in (0,3,8,10,17,24,32,38,52) else 1 if case==20 else 2 if case==42 else 0
  view=4 if case==12 else 0
 else:
  action=rng.choice((0,0,0,0,1,2,3,3,4));view=rng.choice((0,0,0,0,0,0,1,3,4,9,12,27,28))
 x=rng.choice((-32768,-1,0,4,32767)) if action==4 else 0
 y=rng.choice((-32768,-1,0,28,100,32767)) if action==4 else 0
 rows.append([action,view,x,y]);im.write(0x87b6,'<H',view)
 if action in (1,2):im.call(0x84540 if action==1 else 0x8456c)
 elif action==3:im.write(0xe70c,'<I',im.native(0x7d94c));im.call(0x7d7e0)
 elif action==4:im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
 callback=callbacks[im.read(0xe70c,'<I')[0]][1]
 if callback:im.call(callback)
 expected.append([im.read(0x10be8,'<h')[0],im.read(0x10be6,'<h')[0],im.read(0x12bf8,'<H')[0],callbacks[im.read(0xe70c,'<I')[0]][0]])
result=subprocess.check_output([str((a.build/'cockpit_frame_probe').resolve()),str(a.data_dir),'position-shake'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
print('8192 original cockpit position/shake updates agree: complete callbacks, flak restart, saved offsets, raise/lower interruption, view cancellation, native word wrapping and sentinel behaviour')
