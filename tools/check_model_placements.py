#!/usr/bin/env python3
"""Compare all six normal origin/anchor-query submission paths.

Original matrix/camera setters, word/fixed sphere transforms, quarter-turn
placement and part constructors execute. One declared instance/definition is
supplied; CBFEC is observed at the independent geometry consumer, and the
post-query notification is a supplied no-op callback.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);rng=random.Random(0xb6438);quarter=im.read(0xac1c,'<4I');code=lambda off:im.native(0x70aa4+off)
word=lambda value:((value+32768)&65535)-32768
im.write(0x20b98,'<I',0x300000);im.write(0x20b9c,'<I',0x300100);im.write(0x20c4a,'<H',1);im.write(0xac08,'<I',0x300f00);im.cpu.mem_write(0x300f00,b'\xc3');im.cpu.mem_write(0x300100,bytes(64));im.cpu.mem_write(0x300100+16+9,struct.pack('<H',77));im.cpu.mem_write(0x300100+16+27,struct.pack('<H',30));calls=[]
def resolve(image):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==1
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300100);image.return_from()
im.intercept(0xc8568,'Resolve the one supplied SSD instance after native part submission.',resolve)
def draw(image):
 stack=image.cpu.reg_read(r.UC_X86_REG_ESP);pointer,=struct.unpack('<I',image.cpu.mem_read(stack+12,4));calls.append(struct.unpack('<3i',image.cpu.mem_read(pointer,12)));image.return_from(20)
im.intercept(0xcc164,'Observe the queued constructor after native placement and visibility.',draw)
im.intercept(0xcbfec,'Observe the admitted model camera cache at the geometry/render consumer; native part placement and visibility have executed.',draw)
rows=[];expected=[];fixtures=[]
for case in range(8192):
 family=(case//4)%3;anchored=case%2;placement=(2 if family==1 else 1) if anchored else 0;wide=(case//2)%2;matrix=[32767,0,0,0,32767,0,0,0,32767] if case<128 else [rng.randrange(-32768,32768) for _ in range(9)];camera=[rng.randrange(-2147483648,2147483648) for _ in range(3)];origin=[rng.randrange(-2147483648,2147483648) for _ in range(3)];anchor=[rng.randrange(-32768,32768) for _ in range(3)];heading=rng.randrange(4)*16384;radius=rng.choice((-32768,-1,0,1,32767,rng.randrange(-32768,32768)));ox,oy=159,99;maximum=[319,199] if case%5 else [110,120];row=[placement,wide,*matrix,*camera,ox,oy,*maximum,*origin,*anchor,heading,radius];rows.append(row)
 im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb94da,stack=(ox,oy,*maximum));matrix_at=code(0x47c4a);im.cpu.mem_write(matrix_at,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,matrix_at);im.call(0xb959f);im.call(0xb9ab9,stack=tuple(v&0xffffffff for v in reversed(camera)))
 im.cpu.mem_write(0x300000,bytes(64));im.cpu.mem_write(0x300000+2,struct.pack('<h',radius));im.cpu.mem_write(0x300000+10,struct.pack('<3h',*anchor));im.write(0x20b98,'<I',0x300000);im.write(0x20b9c,'<I',0x300100);im.write(0x20bb0,'<3h',*[v>>16 for v in origin]);im.write(0x20baa,'<3H',0,0,0);im.write(0xac18,'<I',quarter[heading//16384]);cache=im.data+0x20b60
 im.call(0xcbf24,stack=tuple(v&0xffffffff for v in (radius,*reversed(origin),cache)));calls.clear();im.call(((0xb635c,0xb6438),(0xb65b0,0xb668c),(0xb6810,0xb68dc))[family][anchored],eax=0,edx=0)
 assert len(calls)<=1
 if anchored:position=list(im.read(0x20c40,'<3h'));raw=list(struct.unpack('<3i',im.cpu.mem_read(im.STACK-32,12)))
 else:position=[v>>16 for v in origin];raw=list(im.read(0x20b60,'<3i'))
 if calls:assert tuple(raw)==calls[0]
 value=[*position,*raw,int(bool(calls))];expected.append(value)
 if case<128 or case%97==0:fixtures.append(row+value)
actual=subprocess.check_output([str((a.build/'model_placement_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,value) in enumerate(zip(actual,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 complete native model part placements agree: all six constructors, retained fixed assembly cache, integer/fixed anchored caches, all quarter turns, word wrapping, native sphere admission and normal/wide partial viewports')
