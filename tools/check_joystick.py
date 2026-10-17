#!/usr/bin/env python3
"""Compare post-calibration joystick response and original button dispatch.

Full 0xc4ac0 executes with supplied DOS port samples and calibration constants;
the modern adapter enters after resistance calibration. Full 0x86530 executes
both repeat tables and selects observed command callbacks. Additional legacy
analogue hat/throttle axes are absent. Command effects have separate consumers.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x86530);actions=[]
im.intercept(0xd0d7c,'Supply normalized digital-device axes in place of DOS resistance-port polling',lambda image:image.return_from())
for file,kind in ((0x864fc,0),(0x83fa8,1),(0x84a78,2),(0x84598,3),(0x85bb0,4),(0x85348,5),(0x85498,6),(0x85528,7),(0x855b8,8)):
 im.intercept(file,'Observe selected joystick command; its game effects are outside this input-only comparison',lambda image,kind=kind:(actions.append(kind),image.return_from()))
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
rows=[]
for i in range(8192):rows.append([rng.randrange(-8192,8193),rng.randrange(-8192,8193),fbits(rng.choice([0,.5,128,512,1024,-512,40000,1e30])),(i//4)%16,(i//64)%3,rng.choice([0,1,2,4,10,18,25,26,65535]),int(i%64==0)])
output=subprocess.check_output([str((a.build/'joystick_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
fixtures=[];counts={}
for index,(row,line) in enumerate(zip(rows,output)):
 x,y,scale,mask,kind,ticks,reset=row
 im.write(0xae14,'<i',20000+x);im.write(0xae28,'<i',20000+y)
 for f,value in ((0x20c6a,20000),(0x20c60,20000),(0x20c68,4096),(0x20c66,4096)):im.write(f,'<h',value)
 im.write(0xac68,'<I',scale);im.call(0xc4ac0)
 for bit,f in enumerate((0x1323a,0x13238,0x13236,0x13234)):im.write(f,'<H',255 if mask&(1<<bit) else 0)
 im.write(0x13267,'<B',kind);im.write(0x13476,'<H',ticks)
 if reset:
  for base in (0x7788,0x7808):
   for slot in range(16):im.write(base+slot*8+6,'<h',0)
 actions.clear();im.call(0x86530)
 assert len(actions)<=1
 action=actions[0] if actions else 0
 expected=list(im.read(0xac60,'<2h'))+[action]+[im.read(base+slot*8+6,'<h')[0] for base in (0x7808,0x7788) for slot in range(16)]
 actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
 counts[action]=counts.get(action,0)+1
 if index<256:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert all(counts.get(k,0)>0 for k in range(9)),counts
print(f'{len(rows)} original joystick axis/button updates agree, including signed-square JOYSCALE response, all button combinations, both repeat tables and word wrap; actions {counts}')
