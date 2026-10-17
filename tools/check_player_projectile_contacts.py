#!/usr/bin/env python3
"""Compare the original projectile-to-player dispatch gates, including ejection.

The original source-query setup and parent/helper gates execute unchanged.
Only the source SSD handle lookup and final collision geometry are supplied;
the capture stops before the later aircraft/terrain phases.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference,r
from check_projectiles import CALLBACKS

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
head,tail,shot,source=0x300000,0x300100,0x300200,0x300300
im.write(0x16e80,'<I',head);im.write(0x16e7c,'<I',tail)
im.cpu.mem_write(head+52,struct.pack('<I',shot));im.cpu.mem_write(shot+52,struct.pack('<I',tail))
im.cpu.mem_write(shot+46,struct.pack('<H',9));im.write(0xe76c,'<H',7)
im.cpu.mem_write(source+3,struct.pack('<H',51));queries=[]
def lookup(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EAX)==9
 im.cpu.reg_write(r.UC_X86_REG_EAX,source);im.return_from()
im.intercept(0xc8568,'Resolve the supplied source SSD; original query setup and damage-word copy execute.',lookup)
def contact(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EAX)==7
 assert im.read(0x20c46,'<H')[0]==51
 queries.append(1);im.return_from()
im.intercept(0xb76a8,'Observe the final player collision dispatch; SSD geometry has separate comparisons.',contact)
for address in (0xa3810,0xa384f):
 im.intercept(address,'Stop after all player-dispatch branches, before the separate actor and terrain phases.',lambda im:im.cpu.reg_write(r.UC_X86_REG_EIP,im.RETURN))
rows=[];expected=[];fixture=[]
for weapon in range(27):
 for motion,callback in enumerate(CALLBACKS):
  for flags in range(32):
   owned,invulnerable,ejected,pilot,destroyed=[(flags>>bit)&1 for bit in range(5)]
   row=[weapon,motion,owned,invulnerable,ejected,pilot,destroyed];rows.append(row)
   im.cpu.mem_write(shot+6,bytes([weapon]));im.cpu.mem_write(shot+60,struct.pack('<I',im.native(callback) if callback else 0))
   im.cpu.mem_write(shot+75,struct.pack('<I',im.data+0x10f28 if owned else 0))
   im.cpu.mem_write(source+2,bytes([destroyed<<4]));im.write(0x13250,'<H',invulnerable);im.write(0xabe9,'<B',ejected);im.write(0xe784,'<B',pilot)
   queries.clear();im.call(0xa373c);value=int(bool(queries));expected.append(value)
   if weapon==0:fixture.append(row+[value])
result=subprocess.check_output([str((a.build/'projectile_impact_probe').resolve()),'--player-contacts'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(value,line) in enumerate(zip(expected,result)):assert value==int(line),(case,rows[case],value,line)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
print(f'{len(rows)} original player projectile-contact gates agree: all 27 weapons, 13 motion callbacks, ownership and invulnerability; ejection, pilot phase and already-destroyed source do not suppress dispatch')
