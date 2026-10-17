#!/usr/bin/env python3
"""Compare complete original Alt+J inventory/selection/fuel behaviour and launch geometry.

The original key handler, pylon selectors and mount transform execute. The
projectile constructor is an observed output boundary; jettison stage programs
are checked separately by the complete projectile-population comparison.
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
p.add_argument('--save-fixture',type=Path)
a=p.parse_args();rng=random.Random(0x85118)
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
im.write(0xa3f4,'<h',-1)
im.write(0x1b23c,'<I',0x300400)
im.write(0xac74,'<I',im.native(0x75954))
for address in (0xa4f10,0xa6068):
 im.intercept(address,'Any launch sound is a jettison regression.',lambda current:(_ for _ in ()).throw(AssertionError('jettison called launch sound')))
im.intercept(0xb52d4,'Observe native bay model event without drawing the SSD.',lambda current:current.return_from())
im.intercept(0xb1334,'Supply Arcade/unlimited configuration values; inventory arithmetic executes.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,0x300100 if current.cpu.reg_read(r.UC_X86_REG_EAX)==current.data+0x2148 else 0x300104),current.return_from()))
shots=[]
def launch(current):
 sp=current.cpu.reg_read(r.UC_X86_REG_ESP)
 heading,roll,speed,weapon,target,owner=struct.unpack('<6I',current.cpu.mem_read(sp+4,24))
 assert owner==current.data+0x10f28 and target in (0,0x300600)
 assert current.read(0x9170,'<H')[0]==1
 xyz=[struct.unpack('<i',struct.pack('<I',current.cpu.reg_read(reg)))[0]for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]
 shots.extend([*xyz,current.cpu.reg_read(r.UC_X86_REG_ECX)&65535,heading&65535,roll&65535,struct.unpack('<i',struct.pack('<I',speed))[0],weapon,int(bool(target)),1])
 current.return_from(stack_bytes=24)
im.intercept(0xa2f84,'Observe released geometry, order, target and jettison mode before population construction.',launch)
model_base=im.native(0x70aa4+0x47c94)
im.write(0x809c+255*48+20,'<B',6);im.write(0x809c+255*48+29,'<B',7)
for index in range(27):
 im.write(0x809c+index*48+20,'<B',6 if index%3==2 else index%2)
 im.write(0x809c+index*48+29,'<B',(index*7)%15)
for plane,base in enumerate((0x8654,0x8618,0x85dc)):
 for slot in range(10):im.write(base+slot*6,'<3h',-800+slot*200,200+plane*128,slot*64)
rows=[];expected=[]
for case in range(4096):
 plane=case%3;flags=rng.choice((16,16,16,24,rng.randrange(32)));selected=rng.randrange(-1,11);guns=rng.randrange(2)
 inventory=[(rng.randrange(27) if rng.randrange(5) else 255,rng.randrange(3))for _ in range(10)]+[(0,0)]
 inventory=[(weapon,0 if weapon==255 else count)for weapon,count in inventory]
 position=[rng.randrange(-20000000,20000001)for _ in range(3)];angles=[rng.randrange(65536)for _ in range(3)];speed=rng.randrange(-32768,32768);fuel=rng.randrange(16000)*.25;capacity=rng.randrange(16000)*.25
 row=[plane,flags,selected,guns,*[v for pair in inventory for v in pair],*position,*angles,speed,fuel,capacity]
 for address,fmt,value in ((0x11b2a,'<H',plane),(0x93b0,'<h',selected),(0x7140,'<B',not guns),(0x16e98,'<h',-1),(0x12c04,'<H',bool(flags&1)),(0x86ce,'<B',bool(flags&2)),(0xabe9,'<B',bool(flags&4)),(0x14858,'<d',fuel),(0x14850,'<d',capacity),(0x9170,'<H',0)):
  im.write(address,fmt,value)
 im.cpu.mem_write(0x300438,bytes([bool(flags&16)]));im.cpu.mem_write(0x300100,struct.pack('<2I',bool(flags&8),0))
 for slot,(weapon,count) in enumerate(inventory):im.write(0x13374+slot*2,'<2B',weapon,count)
 im.cpu.mem_write(model_base,struct.pack('<10H',*[100+i for i in range(10)]))
 for address,value in zip((0x13424,0x13430,0x1343c),position):im.write(address,'<i',value)
 im.write(0x86c8,'<3H',*angles);im.write(0x13444,'<i',speed)
 for address,value in ((0x11108,111),(0x8840,222),(0x135c8,333),(0x135d0,0x300600)):im.write(address,'<I',value)
 # Cannon role is mutable selector state; each independent probe starts it at air.
 im.write(0x809c+20,'<B',0)
 shots.clear();im.call(0x85118)
 assert im.read(0x9170,'<H')[0]==0
 values=[len(shots)//10,*shots,im.read(0x93b0,'<h')[0],int(not im.read(0x7140,'<B')[0]),im.read(0x16e98,'<h')[0],int(not im.read(0x11108,'<I')[0]),int(not im.read(0x135d0,'<I')[0])]
 for slot in range(10):values.extend([*im.read(0x13374+slot*2,'<2B'),int(struct.unpack('<H',im.cpu.mem_read(model_base+slot*2,2))[0]!=65535)])
 values.extend(im.read(0x14858,'<2I'))
 rows.append(row);expected.append(values)
request=''.join(' '.join(map(str,row))+'\n'for row in rows)
actual=subprocess.check_output([str((a.build/'jettison_probe').resolve())],input=request.encode()).decode().splitlines()
assert len(actual)==len(expected)
for source,want,line in zip(rows,expected,actual):
 got=list(map(int,line.split()))
 assert got==want,(source,got,want)
if a.save_fixture:
 fixture=[]
 for i in range(0,len(rows),17):
  digest=14695981039346656037
  for value in expected[i]:
   for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
  fixture.append(' '.join(map(str,rows[i]+[digest]))+'\n')
 a.save_fixture.write_text(''.join(fixture));subprocess.run([str((a.build/'jettison_probe').resolve()),str(a.save_fixture)],check=True)
print(f'{len(rows)} complete original Alt+J cases agree: eligibility, ordered geometry, selection, inventory, unlimited stores, launch suppression and fuel clamp')
