#!/usr/bin/env python3
"""Compare native VGA pattern consumers with explicitly supplied span stacks.

This isolates the painter boundary, rather than using polygon-edge construction
as a second source of span restrictions. Includes empty/inverted pixel and byte
widths, selected/skipped sparse rows, edge masks, patterned backgrounds and final
procedural state. Original factories, span loops, IO and VGA writes execute.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_vga import VgaCapture
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--cases',type=int,default=4096);p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT',data_base=0x100000);vga=VgaCapture(im,aperture=0xa0000);im.call(0xb9238,stack=(0,319,0,199));rng=random.Random(0xe5d5c);rows=[];code=lambda off:im.native(0x70aa4+off)
for case in range(a.cases):
 mode=(0,1,2,3,4,7,10,11,12,-1)[case%10];count=rng.randrange(1,19);bottom=rng.randrange(count-1,200);left=rng.randrange(300);pairs=[]
 for row in range(count):
  x=max(0,min(310,left+rng.randrange(-12,13)));right=max(0,min(319,x+rng.choice((-12,-8,-5,-4,-3,-2,-1,0,1,2,3,4,5,8,20,100))));pairs.extend((x,right))
 rows.append([mode,rng.randrange(65536),rng.randrange(256),bottom,count,(case//10)%2,*pairs])
request=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode();command=[str((a.build/'pattern_span_probe').resolve())];actual=subprocess.check_output(command,input=request).decode().splitlines();pixels=subprocess.check_output(command+['--pixels'],input=request);assert len(actual)==len(rows) and len(pixels)==len(rows)*64000;fixtures=[]
planes=[[bytes([99])*16000 for _ in range(4)],[bytes(((x*4+plane)*3+y*5+((x*4+plane)^y))&255 for y in range(200) for x in range(80)) for plane in range(4)]]
for case,(row,line) in enumerate(zip(rows,actual)):
 mode,seed,ink,bottom,count,background=row[:6];pairs=[row[6+i*2:8+i*2] for i in range(count)];callback=struct.unpack('<I',im.cpu.mem_read(code(0x68106),4))[0] if mode==-1 else im.call(0xe5d5c,eax=mode);im.cpu.mem_write(im.native(0xe3a3f),struct.pack('<H',seed));im.cpu.ctl_remove_cache(im.native(0xe3a04),im.native(0xe3a61));vga.reset(99)
 for plane in range(4):vga.planes[plane][:]=planes[background][plane]
 stack=tuple((left<<16)|right for left,right in reversed(pairs))+(0x13f0000,);im.call(callback-im.native(0x70aa4)+0x70aa4,eax=ink,ebx=bottom,stack=stack,limit=3000000);want=bytes(vga.pixels());got=pixels[case*64000:(case+1)*64000];want_seed=struct.unpack('<H',im.cpu.mem_read(im.native(0xe3a3f),2))[0];digest=14695981039346656037
 for byte in want:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 if want!=got:raise AssertionError((case,row,sum(x!=y for x,y in zip(got,want)),[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:20]))
 assert list(map(int,line.split()))==[digest,want_seed],(case,row,'seed',line,[digest,want_seed])
 if case<128 or case%37==0:fixtures.append(row+[digest,want_seed])
 if case and case%512==0:print(f'Checked {case} complete supplied-span frames',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original supplied-span VGA frames and seeds agree: all ten flat/stipple/logical consumers, inverted pixel/byte widths, sparse selected/skipped rows, edge masks and uniform/patterned destinations.')
