#!/usr/bin/env python3
"""Compare mixed allied/enemy combat with the player outside acquisition range.

All data is test-authored. The original aircraft controllers, acquisition and
firing execute; warning/projectile deliveries remain recorded boundaries. This
specifically requires firing notices whose target is another AI aircraft.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from check_air import original

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path,required=True)
a=p.parse_args()
profiles=[]
for side in (0,1):
 raw=bytearray(74);raw[0]=14;raw[1:5]=b'TEST';raw[21:25]=b'test';raw[31]=side
 struct.pack_into('<H',raw,32,42+side)
 struct.pack_into('<2i7H',raw,36,10000,12000,0,18000,80,1000,0,60000,500)
 struct.pack_into('<h',raw,62,180);struct.pack_into('<H',raw,60,4)
 struct.pack_into('<5H',raw,64,2,4,8000,8,40);profiles.append(bytes(raw))
profile_file=struct.pack('<2H',0,2)+b''.join(profiles)+bytes(4)
records=[{'offset':4+i*74,'hex':raw.hex()} for i,raw in enumerate(profiles)]
formation=b''.join(struct.pack('<H3i',i*4096,8192 if i else 0,4096 if i else 0,-800*i)for i in range(10))
manoeuvres=[]
for category in (0,1):
 header=bytearray(16);header[0]=category
 manoeuvres.append(bytes(header)+struct.pack('<BbbbbB',60,-90,20,60,5,3)+struct.pack('<BbbbbB',90,30,-20,-60,-5,4)+bytes(1))
def command(op,*words):return bytes([op])+struct.pack('<'+'H'*len(words),*[v&65535 for v in words])
fixtures=[];updates=0;warnings=0
for scenario in range(4):
 blocks=[]
 for side in (0,1):
  code=command(14,1+scenario%3,10,10+side,42+side,1,12000,450+side*50,0,0,0,0,0)
  loop=len(code);code+=command(13,500)+command(11,12000)
  at=len(code);code+=command(1,at-loop,10,20 if side==0 else 0,at-loop)
  blocks.append(struct.pack('<H',len(code))+code)
 raw=b''.join(blocks)+bytes(2);ticks=512
 combat=[-100000000,-384000,-100000000,0,0,0,400<<16,scenario%3,0,1,0]
 delivered=[];observed,count=original(a.data_dir,raw,records,ticks,0,formation,combat,manoeuvres,warning_log=delivered)
 assert delivered and all(target!=100 and kind==1 for target,kind in delivered),(scenario,delivered[:10])
 digest=14695981039346656037
 for sample,_ in observed:
  for byte in struct.pack('<Q',sample):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
 fixtures.append(f"{ticks} 0 {profile_file.hex()} {raw.hex()} {formation.hex()} {','.join(m.hex()for m in manoeuvres)} {' '.join(map(str,combat))} {digest}")
 updates+=count*ticks;warnings+=len(delivered)
 print(f'Crossfire scenario {scenario}: {count} actors, {len(delivered)} original nonplayer firing notices',flush=True)
a.record.write_text('\n'.join(fixtures)+'\n')
subprocess.run([str((a.build/'air_combat_tests').resolve()),str(a.record)],check=True)
print(f'{updates} original mixed-pool aircraft updates agree, including {warnings} explicit AI-to-AI firing notifications')
