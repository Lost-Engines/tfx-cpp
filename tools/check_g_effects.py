#!/usr/bin/env python3
"""Compare complete native persistent G-strain/redout/blackout production."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x73654)
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
rows=[]
for i in range(8192):
 load=rng.choice([-12,-5.000001,-5,-4.000001,-4,0,9,9.000001,10,10.000001,15,rng.uniform(-12,15),float('nan'),float('inf'),-float('inf')])
 strain=rng.choice([-55,-50,-49.99999,0,-0.,49,50,55,rng.uniform(-50,50),float('nan'),float('inf'),-float('inf')])
 rows.append([fbits(load),i%4,rng.choice([0,1,2,4,18,65535]),int(i%32==0),fbits(strain),i%3,rng.randrange(-32768,32768),rng.randrange(-32768,32768)])
output=subprocess.check_output([str((a.build/'g_effects_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
fixtures=[];counts={}
for index,(row,line) in enumerate(zip(rows,output)):
 load,realism,elapsed,reset,strain,mode,black,red=row
 im.write(0x133f4,'<I',load);im.write(0x5954,'<B',realism);im.write(0x13476,'<H',elapsed)
 if reset:im.write(0x5960,'<I',strain);im.write(0x10bea,'<B',mode);im.write(0x10bda,'<2h',black,red)
 im.call(0x73654)
 expected=[im.read(f,fmt)[0] for f,fmt in ((0x5960,'<I'),(0x10bea,'<B'),(0x10bda,'<h'),(0x10bdc,'<h'))];actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
 counts[expected[1]]=counts.get(expected[1],0)+1
 if index<256:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert len(counts)==3,counts
print(f'{len(rows)} complete original G-effect updates agree without intercepted dependencies: reduced/realistic thresholds, persistent strain/recovery, palette levels, retained zero-state levels and unordered inputs; modes {counts}')
