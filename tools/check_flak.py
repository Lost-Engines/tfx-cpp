#!/usr/bin/env python3
"""Compare complete original area-flak controller, 20-slot pool and draw gate.

Resource handles, SSD/audio/radio/palette outputs and final model drawing are
observed boundaries. All region/height/cooldown decisions, dedicated PRNG, sine
rotation, placement, linked-list allocation/reuse and distance gates execute.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0x7cc30)
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
handles={};loaded=[];events=[];draws=[];night=[False]
names=['snake_1','snake_2','snake_3','snake_4','snake_5']
def resource(im):
 name=bytes(im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),32)).split(b'\0')[0].decode();index=len(loaded);loaded.append(name);handle=index+1;handles[handle]=(index//(5 if night[0] else 1),names.index(name)if night[0]else 0);im.cpu.reg_write(r.UC_X86_REG_EAX,handle);im.return_from()
im.intercept(0xb4d98,'Allocate independent symbolic SSDs for all day/night flak slots.',resource)
def model(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EDX)==0
 slot,model=handles[im.cpu.reg_read(r.UC_X86_REG_EAX)];events.extend([3,slot,model]);im.return_from()
im.intercept(0xb52d4,'Record selected SSD reset; its own bytecode/animation is separately compared.',model)
def sample(im):
 priority,descriptor,end=struct.unpack('<3I',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_ESP)+4,12));assert end==0 and descriptor==im.data+0x9860+16*26
 events.extend([0,priority,16]);im.return_from()
im.write(0xac74,'<I',im.native(0x75954));im.intercept(0x75954,'Observe exact normal flak sample descriptor and priority.',sample)
def radio(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EAX)==im.data+0x1388
 events.append(1);im.return_from()
im.intercept(0x81198,'Observe the original climb-to-avoid-flak radio request.',radio)
im.intercept(0x7d7e0,'Observe cockpit-shake setup; its persistent positioning callbacks are separately compared.',lambda im:(events.append(2),im.return_from()))
def draw(im):
 slot,model=handles[im.cpu.reg_read(r.UC_X86_REG_EAX)];xyz=[struct.unpack('<h',struct.pack('<H',im.cpu.reg_read(reg)&65535))[0]for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]
 draws.extend([slot,model,*xyz]);im.return_from()
im.intercept(0xb4fd0,'Observe queued flak model/word position; world projection is independently compared.',draw)
rows=[];expected=[];fixtures=[];spawns=0;flashes=0
wrap=lambda v:struct.unpack('<i',struct.pack('<I',v&0xffffffff))[0]
for scenario in range(16):
 night[0]=bool(scenario%2);delay=[0,1,5,0,-1,-32768,32767,0][scenario%8];phase=rng.randrange(65536);scatter=rng.randrange(65536);variant=scenario%5;cx=0;cz=0
 row=['I',delay,phase,scatter,variant,cx,cz,int(night[0])];rows.append(row);loaded.clear();handles.clear();events.clear();draws.clear();im.write(0xe774,'<H',1);im.cpu.mem_write(im.native(0x70aa4+0x47c82),struct.pack('<H',128 if night[0]else 0));preserved=im.read(0x5d98,'<h2HB');im.call(0x7ce60);assert im.read(0x5d98,'<h2HB')==preserved
 assert loaded==(names*20 if night[0]else ['burst']*20)
 im.write(0x5d98,'<h2HB',delay,phase,scatter,variant);im.write(0x5d90,'<2i',cx,cz);im.write(0x5d8c,'<B',0);im.write(0xe70c,'<I',im.native(0x70b44))
 for frame in range(513):
  if frame:
   tick=frame-1;x=100000+tick*23;z=200000+tick*17;y=rng.choice((-1501,-1500,-1499,-900,-700,-151,-150,-149));cloud=int(tick%5==0);layer=rng.choice((-1000,-700,-150));radio_idle=tick%3!=0
   count=0 if tick%11==0 else rng.randrange(1,6);regions=[]
   for index in range(count):
    if index==count-1:regions.append((x-(tick%4),z-(tick%4),x+(tick%4),z+(tick%4)))
    else:regions.append((x+100,z+100,x+200,z+200))
   if tick%17==0:x+=40000
   if tick%127==126:
    x=wrap(im.read(0x5d90,'<i')[0]-2147483648);z=im.read(0x5d94,'<i')[0];regions=[]
   row=['F',x,y,z,cloud,layer,int(radio_idle),len(regions),*[v for area in regions for v in area]];rows.append(row)
   im.write(0x13424,'<i',x);im.write(0x13430,'<i',y);im.write(0x1343c,'<i',z);im.write(0xe762,'<H',cloud);im.write(0xe75a,'<h',layer);im.write(0x7612,'<B',radio_idle);im.write(0x11b41,'<B',len(regions));im.write(0x5d8c,'<B',0);im.write(0xe70c,'<I',im.native(0x70b44))
   for index,area in enumerate(regions):im.write(0x11824+index*16,'<4i',*area)
   events.clear();draws.clear();im.call(0x7cc30);im.call(0x7cf34);spawns+=int(3 in events);flashes+=im.read(0x5d8c,'<B')[0]
  values=[im.read(0x5d98,'<h')[0],*im.read(0x5d9a,'<2H'),im.read(0x5d9e,'<B')[0],*im.read(0x5d90,'<2i'),im.read(0x5d8c,'<B')[0],int(im.read(0xe70c,'<I')[0]==im.native(0x7d94c)),len(events),*events,len(draws)//5,*draws]
  digest=14695981039346656037
  for value in values:
   for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  expected.append(digest)
  if scenario<2 or frame<17:fixtures.append(row+[digest])
result=subprocess.check_output([str((a.build/'flak_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert int(line)==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
print(f'8192 complete original flak frames agree across 16 persistent day/night scenarios: {spawns} spawns, {flashes} palette-flash requests, dedicated RNG, height/region/cloud gates, cooldown wrapping, model/sample/radio order, 20-slot reuse and draw-distance/absolute-value quirks')
