#!/usr/bin/env python3
"""Compare the original text-reveal timing prefix and Space consumption.

The supplied fast counter replaces the external clock reader. The complete
original prefix executes up to, but not including, the already compared VGA
text draw. Only inputs and compact state hashes are saved as replay fixtures.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--save-fixture',type=Path)
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096);image.write(0x1b238,'<I',0x300000)
now=0
image.intercept(0xa6134,'Supply the fast counter value; native delta clamp and reveal arithmetic execute.',lambda im:(im.write(0x16f2c,'<I',now),im.return_from()))
image.intercept(0xb1c64,'Stop after the complete timing/Space prefix before VGA text drawing, which has a separate native comparison.',lambda im:im.return_from())
rng=random.Random(0xb1c16);rows=[];expected=[];updates=0
for case in range(2048):
    total=rng.choice((0,1,2,79,80,512,1600));initial=rng.choice((0,0x7fffffff,0xffffffff,rng.randrange(2**32)));frames=64;now=initial;row=[total,initial,frames]
    image.write(0x1acf8,'<I',initial);image.write(0x1afde,'<H',total);image.write(0x241b6,'<H',0);image.write(0x1afd8,'<H',0);digest=14695981039346656037
    for frame in range(frames):
        elapsed=rng.choice((0,1,2,3,49,50,51,55,32767,32768,65535,65536,0xffffffff));skip=rng.randrange(32)==0;row.extend((elapsed,int(skip)));now=(now+elapsed)&0xffffffff
        image.cpu.mem_write(0x300000,bytes([0x39 if skip else 0]));image.call(0xb1c16)
        values=[image.read(0x1acf8,'<I')[0],image.read(0x241b6,'<H')[0],image.read(0x1afd8,'<H')[0],int(skip and image.cpu.mem_read(0x300000,1)[0]==0)]
        for value in values:
            for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        updates+=1
    rows.append(row);expected.append(digest)
result=subprocess.run([str(args.build/'text_clock_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
actual=[int(v) for v in result.stdout.split()];assert len(actual)==len(expected)
for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i][:12],a,b)
if args.save_fixture:
    args.save_fixture.write_text(''.join(' '.join(map(str,row+[value]))+'\n' for i,(row,value) in enumerate(zip(rows,expected)) if i%8==0))
    subprocess.run([str(args.build/'text_clock_probe'),str(args.save_fixture)],check=True)
print(len(rows),'text reveal sequences;',updates,'native clock/Space transitions agree, including low-word and full counter wrap')
