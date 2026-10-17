#!/usr/bin/env python3
"""Compare complete original horizon polygon production before rasterization.

Original horizon branches, matrix setup, signed projection, band strips and
banked edge caps execute. Supplied camera/viewport/ground phase are inputs;
polygon/rectangle delivery is observed before its independent raster consumer.
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
p.add_argument('--cases',type=int,default=8192)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0xcaf84);surfaces=[]
def polygon(im):
 pointer=struct.unpack('<I',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,4))[0]
 colour,count=struct.unpack('<2H',im.cpu.mem_read(pointer,4));assert 3<=count<=5
 vertices=list(struct.unpack('<'+str(count*2)+'h',im.cpu.mem_read(pointer+4,count*4)))
 surfaces.append([colour,0,count,*vertices]);im.return_from(stack_bytes=4)
def rectangle(im):
 maximum_y,maximum_x,minimum_y,minimum_x,colour=struct.unpack('<5i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,20))
 surfaces.append([colour,1,4,minimum_x,minimum_y,maximum_x,minimum_y,maximum_x,maximum_y,minimum_x,maximum_y]);im.return_from(stack_bytes=20)
im.intercept(0xb9ec9,'Observe original horizon polygon vertices and palette index before clipped rasterization.',polygon)
im.intercept(0xc98d8,'Observe the steep-pitch solid viewport rectangle before VGA filling.',rectangle)
rows=[];expected=[];fixture=[]
def digest(values):
 value=14695981039346656037
 for v in values:
  for b in struct.pack('<I',v&0xffffffff):value=((value^b)*1099511628211)&0xffffffffffffffff
 return value
angles=(0,1,0x1a9f,0x1aa0,0x1aa1,0x2680,0x2681,0x3000,0x3001,0x3fff,0x4000,0x4001,0x6000,0x7fff,0x8000,0x9fff,0xbfff,0xc000,0xc001,0xd8ef,0xd8f0,0xd8f1,0xffff)
rolls=(0,1,0x1fff,0x2000,0x2001,0x5fff,0x6000,0x6001,0x7fff,0x8000,0x9fff,0xa000,0xa001,0xdfff,0xe000,0xe001,0xffff)
for case in range(a.cases):
 pitch=angles[case%len(angles)] if case<1024 else rng.randrange(65536);roll=rolls[case//len(angles)%len(rolls)] if case<1024 else rng.randrange(65536)
 height=rng.choice((-32768,-10000,-4000,-1000,-399,0,399,32767));phase=rng.choice((-32768,-1375,-1,0,1,1374,1375,2750,32767));minimum=[0,0];maximum=[319,199];origin=rng.choice((28,56,70,99,149))
 if case%9==0:minimum=[rng.randrange(0,30),rng.randrange(0,30)];maximum=[rng.randrange(200,320),rng.randrange(100,200)]
 row=[pitch,roll,height,phase,*minimum,*maximum,origin];rows.append(row)
 im.call(0xb9238,stack=(minimum[0],maximum[0],minimum[1],maximum[1]));im.call(0xb94da,stack=((minimum[0]+maximum[0])//2,origin,*maximum));im.call(0xc84b1,stack=(minimum[0],maximum[0],minimum[1],maximum[1],origin));im.call(0xb9a6c,stack=(0,height&0xffffffff,0));im.write(0xad7c,'<h',phase)
 surfaces.clear();im.call(0xcaf84,eax=pitch,edx=roll,limit=2000000)
 values=[len(surfaces),*[v for surface in surfaces for v in surface]];expected.append(digest(values))
 if case<256 or case%67==0:fixture.append(row+[expected[-1]])
output=subprocess.check_output([str((a.build/'horizon_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
for case,(line,value) in enumerate(zip(output,expected)):
 if int(line)!=value:
  pitch,roll,height,phase,mx,my,hx,hy,origin=rows[case]
  im.call(0xb9238,stack=(mx,hx,my,hy));im.call(0xb94da,stack=((mx+hx)//2,origin,hx,hy));im.call(0xc84b1,stack=(mx,hx,my,hy,origin));im.call(0xb9a6c,stack=(0,height&0xffffffff,0));im.write(0xad7c,'<h',phase)
  surfaces.clear();im.call(0xcaf84,eax=pitch,edx=roll,limit=2000000)
  native=[len(surfaces),*[v for surface in surfaces for v in surface]]
  actual=list(map(int,subprocess.check_output([str((a.build/'horizon_probe').resolve()),'--surfaces'],input=(' '.join(map(str,rows[case]))+'\n').encode()).split()))
  differences=[(i,x,y) for i,(x,y) in enumerate(zip(actual,native)) if x!=y]
  raise AssertionError((case,rows[case],len(actual),len(native),differences[:20],actual,native))
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
print(f'{a.cases} complete original horizon surface cases agree: native matrix/IDIV projection, altitude bands, moving ground phase, upright/banked/inverted strips, edge caps, steep-pitch rectangle and viewport origins')
