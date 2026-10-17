#!/usr/bin/env python3
"""Compare original sun/lightning production, flash consumption and grid selection.

Resource handles, frame-active input, player/camera state and viewport are
supplied. Original controllers, countdown/RNG, rotation, placement and point
projection execute. Model submission is observed before its renderer consumer.
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
a=p.parse_args();data=a.research/'installs/cd_1994_09/TFX';rng=random.Random(0xa26cc)
word=lambda x:struct.unpack('<h',struct.pack('<H',x&65535))[0]
wrap=lambda x:struct.unpack('<i',struct.pack('<I',x&0xffffffff))[0]
def digest(values):
 result=14695981039346656037
 for v in values:
  for byte in struct.pack('<I',v&0xffffffff):result=((result^byte)*1099511628211)&0xffffffffffffffff
 return result
rows=[];expected=[]
im=NativeReference(data/'TFX.DAT');requests=[]
im.write(0x14eb2,'<H',101);im.write(0x14eb8,'<H',102);im.write(0x11b41,'<B',0)
def submit(im):
 radius,z,y,x,parameter,handle,kind=struct.unpack('<7i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,28))
 assert radius==4000 and parameter==0 and kind==0 and handle in (101,102)
 requests.extend([handle-101,x,y,z]);im.return_from(stack_bytes=28)
im.intercept(0xc5507,'Observe native shape submission, before separately checked visibility and shape/raster consumers.',submit)
strikes=0
for case in range(8192):
 suppressed=case%13==0;cloud=case%7!=0;storm=case%5!=0;active=case%3!=0
 height=rng.choice((-32768,-2400,-1400,0,32767));player=[rng.randrange(-2147483648,2147483648),rng.choice((height-1,height,height+1,-700)),rng.randrange(-2147483648,2147483648)]
 camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 if case%2:delay=rng.choice((-32768,-1,0,1,1,2,5,127,32767));phase=rng.randrange(65536);scatter=rng.randrange(65536);last=[rng.randrange(-2147483648,2147483648) for _ in range(2)];pending=case%4
 else:delay,phase,scatter=im.read(0x9168,'<HHh')[2],im.read(0x9168,'<H')[0],im.read(0x916a,'<H')[0];last=[im.read(at,'<i')[0] for at in (0x14eac,0x14ea8)];pending=im.read(0x5952,'<B')[0]
 rows.append(['S',delay,phase,scatter,*last,pending,int(suppressed),int(cloud),int(storm),int(active),height,*player,*camera])
 im.write(0x9168,'<HHh',phase,scatter,delay);im.write(0x14eac,'<i',last[0]);im.write(0x14ea8,'<i',last[1]);im.write(0x5952,'<B',pending)
 im.write(0xe774,'<H',1|int(suppressed)*0x200|int(storm)*0x80);im.write(0xe762,'<H',int(cloud));im.write(0xe75a,'<h',height);im.write(0xac90,'<B',int(active))
 for at,v in zip((0x13424,0x13430,0x1343c,0x134f0,0x134f8,0x13500),player+camera):im.write(at,'<i',v)
 requests.clear();im.call(0xa26cc)
 values=[im.read(0x916c,'<h')[0],*im.read(0x9168,'<2H'),im.read(0x14eac,'<i')[0],im.read(0x14ea8,'<i')[0],im.read(0x5952,'<B')[0],int(bool(requests)),*requests]
 strikes+=bool(requests) and requests[0]==1;expected.append(digest(values))
# Complete palette-side visibility/one-shot portion, ending before palette generation.
im=NativeReference(data/'TFX.DAT');matrix_at=im.native(0x70aa4+0x47c4a)
im.intercept(0x73ef3,'Stop after the complete pending-strike consumer, before separately checked palette generation.',lambda im:im.cpu.reg_write(r.UC_X86_REG_EIP,im.RETURN))
flashes=0
for case in range(4096):
 pending=case%4;last=[rng.randrange(-10000,10001) for _ in range(2)];origin=[rng.choice((159,0,319)),rng.choice((56,99,199))]
 matrix=[rng.randrange(-32768,32768) for _ in range(9)];camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 if case%3==0:matrix=[32767,0,0,0,32767,0,0,0,32767];camera=[last[0]*65536,0,(last[1]-1000)*65536];camera=[wrap(v) for v in camera]
 rows.append(['F',pending,*last,*matrix,*camera,*origin]);im.write(0x5952,'<B',pending);im.write(0x10beb,'<B',50)
 im.write(0x14eac,'<i',last[0]);im.write(0x14ea8,'<i',last[1]);im.cpu.mem_write(matrix_at,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_at);im.call(0xb959f)
 im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)));im.call(0xb94da,stack=(*origin,319,199));im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x100);im.call(0x73e9a)
 flash=im.read(0x10beb,'<B')[0]==12;flashes+=flash;expected.append(digest([im.read(0x5952,'<B')[0],int(flash)]))
# Execute the actual main-frame branch and observe its selected grid/height.
im=NativeReference(data/'TFX.DAT');selected=[];im.write(0xe766,'<H',2);im.write(0xe768,'<H',1)
def grid(im):
 selected.extend([int(im.cpu.reg_read(r.UC_X86_REG_EAX)==2),word(struct.unpack('<i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,4))[0])]);im.cpu.reg_write(r.UC_X86_REG_EIP,im.RETURN)
im.intercept(0xb0ba8,'Observe the selected base/upper terrain handle and signed-word drawing height, before grid traversal.',grid)
for case in range(4096):
 cloud=case%3!=0;height=rng.randrange(-32768,32768);offset=rng.randrange(-32768,32768);camera=rng.choice((height-1,height,height+1,rng.randrange(-2147483648,2147483648)))
 rows.append(['L',int(cloud),height,offset,camera]);im.write(0xe762,'<H',int(cloud));im.write(0xe75a,'<h',height);im.write(0xe760,'<h',offset);im.write(0x134f8,'<i',camera)
 selected.clear();im.call(0x72149);assert len(selected)==2;expected.append(digest(selected))
output=subprocess.check_output([str((a.build/'sky_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
for case,(line,value) in enumerate(zip(output,expected)):assert int(line)==value,(case,rows[case],line,value)
assert strikes and flashes
if a.record:
 selected=[i for i in range(len(rows)) if i%61==0 or i%4096<128]
 a.record.write_text('\n'.join(' '.join(map(str,[*rows[i],expected[i]])) for i in selected)+'\n')
print(f'8192 original sun/lightning requests, 4096 pending-flash projections and 4096 terrain-layer selections agree: {strikes} strikes, {flashes} visible flashes, independent player/camera gates, countdown/RNG/word placement, viewport edges and cloud-height equality')
