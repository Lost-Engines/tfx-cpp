#!/usr/bin/env python3
"""Compare native autopilot target selection 0x9adae..0x9b003.

Original startup, route selection, followed-actor decoding, bearing and square
root helpers execute without intercepted dependencies. The enclosing synthetic
frame supplies scratch space; decoded route cells and actor records are inputs.
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,0x2000);rng=random.Random(0x9adae)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
cases=[]
for i in range(8192):
    mode=i%5;count=rng.randrange(1,25) if i%13 else 0
    cells=[(rng.randrange(256),rng.randrange(256)) for _ in range(count)]
    index=rng.choice([-32768,-1,0,1,count,count+1,32767])
    position=[rng.uniform(-1000000,1000000),rng.uniform(-1000000,1000000),rng.uniform(-30000,0)]
    if cells and i%4==0:
        index=rng.randrange(1,count+1);x,z=cells[index-1]
        position[:2]=[(z*2048+1024)*2.4384+rng.uniform(-3000,3000),(x*2048+1024)*2.4384+rng.uniform(-3000,3000)]
    if i%127==0:position=[1e12,-1e12,1e12]
    values=[rng.uniform(0,1000),rng.uniform(-10,10),rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(0,1000),rng.uniform(-20000,0),*position,rng.uniform(-.2,.2)]
    cases.append([mode,rng.randrange(65536),index,rng.randrange(65536),(i//5)%2,count,*[rng.randrange(-1000000,1000000) for _ in range(6)],*[rng.randrange(-2147483648,2147483648) for _ in range(3)],rng.randrange(-2147483648,2147483648),*map(bits,values),*[v for cell in cells for v in cell]])
output=subprocess.check_output([str((a.build/'aerodynamic_navigation_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];advanced=follows=0
fields=[0x14398,0x14380,0x143a8,0x14318,0x143c8,0x14348]
for i,(row,line) in enumerate(zip(cases,output)):
    mode,heading,index,pitch,followed,count=row[:6];target=row[6:9];player=row[9:12];actor=row[12:15];speed=row[15];values=row[16:26];cells=row[26:]
    for field,value in zip(fields,values[:6]):im.write(field,'<Q',value)
    for field,value,fmt in ((0x14960,mode,'<H'),(0x1493a,heading,'<H'),(0x597c,index,'<h'),(0x14938,pitch,'<H'),(0x11108,0x301000 if followed else 0,'<I'),(0x5978,0x300000,'<I')):im.write(field,fmt,value)
    im.write(0x14920,'<3i',*target);im.write(0x1492c,'<3i',*player);im.write(0x14758,'<3Q',*values[6:9]);im.write(0x14508,'<Q',values[9])
    im.cpu.mem_write(0x300000,struct.pack('<H',count)+bytes(cells));im.cpu.mem_write(0x301000,struct.pack('<3i',*actor));im.cpu.mem_write(0x30100e,struct.pack('<H',12345));im.cpu.mem_write(0x301012,struct.pack('<i',speed))
    im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    im.cpu.emu_start(im.native(0x9adae),im.native(0x9b003),count=1000000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x9b003)
    expected=[im.read(0x597c,'<H')[0],im.read(0x1493a,'<H')[0],im.read(0x14938,'<H')[0]]+[v&0xffffffff for field in (0x14920,0x1492c) for v in im.read(field,'<3i')]+[im.read(field,'<Q')[0] for field in fields]
    actual=list(map(int,line.split()));assert actual==expected,(i,row,[(j,x,y) for j,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    advanced+=im.read(0x597c,'<h')[0]!=index;follows+=mode==2 and followed
    if i%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert advanced>100 and follows>100
print(f'{len(cases)} original autopilot navigation updates agree: {advanced} route changes and {follows} followed-aircraft targets; no intercepted dependencies')
