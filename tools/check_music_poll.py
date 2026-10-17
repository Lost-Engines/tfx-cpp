#!/usr/bin/env python3
"""Compare complete native per-frame flight music polling and retained state.

The original 0xa5374/0xa5210 frame controller and both LA/FM-SCC selectors execute, including
x87 throttle thresholds and engine-order calculation. Resource replacement (0xa54f4) and the protected to
real-mode OSL bridge are declared output boundaries. No selector branches,
transient gates, retained-cue or hardware-mode rules are replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0xa5374)
bits=lambda x:struct.unpack('<I',struct.pack('<f',x))[0]
cases=[]
for index in range(8192):
 mode=index%6;sound=rng.randrange(5)
 row=[mode,sound,*[int(rng.randrange(3)!=0)for _ in range(2)],*[int(rng.randrange(12)==0)for _ in range(5)],rng.randrange(2),bits(rng.choice([0,.59,.6,.7,.8,.9,1,1.1,rng.uniform(0,1.5)])),bits(rng.choice([-1,0,.5,.6,.7,.8,1,rng.uniform(0,1.5)])),rng.randrange(14),rng.choice([0,0,rng.randrange(-32768,32768)]),rng.randrange(2),rng.randrange(2)]
 row += [rng.randrange(128)for _ in range(12)];cases.append(row)
output=subprocess.check_output([str((a.build/'music_poll_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851)
profile=0x300000;bridge=0x320000;im.cpu.mem_map(0x300000,0x30000);im.cpu.mem_write(bridge,b'\xc3');im.write(0xa3f8,'<I',bridge);im.write(0xa3d4,'<I',profile)
events=[];active=False
def replace(image):
 # The independently checked replacement path clears pending and last cue,
 # selects this filename and sets the order request for the subsequent play.
 index=image.cpu.reg_read(r.UC_X86_REG_EAX)&255;order=image.cpu.reg_read(r.UC_X86_REG_EDX)&255
 global active
 active=False
 events.append(('replace',index,order));image.write(0xa3e0,'<h',0);image.write(0x16f68,'<B',0)
 image.write(0xa3e4,'<I',0);image.write(0x16f44,'<I',order<<8);image.cpu.reg_write(r.UC_X86_REG_EAX,0);image.return_from()
im.intercept(0xa54f4,'Resource replacement and filename I/O are supplied; compare its selected index/order',replace)
def device(cpu,address,size,user):
 global active
 command=im.read(0x16f50,'<I')[0]>>8&255
 if command==6:events.append(('stop',));active=False
 elif command==3:events.append(('release',))
 elif command==7:
  if active:im.write(0x16f48,'<I',0)
 elif command==4:events.append(('play',im.read(0x16f44,'<I')[0]>>8&255));active=True
 else:raise AssertionError(('unexpected bridge command',command))
 im.return_from()
im.cpu.hook_add(UC_HOOK_CODE,device,begin=bridge,end=bridge)
fixtures=[];accepted=0
for index,(row,line) in enumerate(zip(cases,output)):
 mode,sound,enabled,music,cd,pending,inhibited,collision,disabled,engines,throttle,previous,last,resume,engine,playing=row[:16]
 for at,fmt,value in [(0xa4e9,'<B',mode),(0xa4e8,'<B',sound),(0x8866,'<B',enabled),(0xa3d8,'<B',music),(0xab4c,'<h',cd),(0x16f66,'<h',10 if pending else 0),(0xabe9,'<B',inhibited),(0x12c04,'<h',collision),(0x86ce,'<B',disabled),(0x133f8,'<I',throttle),(0xa3fc,'<I',previous),(0x16f68,'<B',last),(0xa3e0,'<h',resume),(0xa3f6,'<h',engine),(0xa3e4,'<I',0),(0x16f44,'<I',0),(0xa400,'<h',0),(0x13476,'<H',0)]:im.write(at,fmt,value)
 im.write(0x14880,'<2d',float(bool(engines)),0)
 im.cpu.mem_write(profile,bytes(row[16:]));events.clear();active=bool(playing);im.call(0xa5374)
 expected=[im.read(0x16f68,'<B')[0],im.read(0xa3e0,'<h')[0],int(im.read(0xa3f6,'<h')[0]!=0),im.read(0xa3fc,'<I')[0]]
 play=[e for e in events if e[0]=='play'];replacement=[e for e in events if e[0]=='replace'];stop=[e for e in events if e[0]=='stop'];release=[e for e in events if e[0]=='release']
 assert len(play)<=1 and len(replacement)<=1 and len(stop)<=2 and len(release)<=1,(index,events)
 expected += [int(bool(release)),int(bool(play))]
 if play:expected += [int(bool(replacement)),replacement[0][1] if replacement else 0,play[0][1],int(len(stop)>len(release))];accepted+=1
 actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected,events)
 if index<256:fixtures.append(' '.join(map(str,row))+' '+' '.join(map(str,expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(cases)} complete original flight music frame updates agree, including {accepted} selected plays, engine shutdown, throttle cache/thresholds and sequencer-driven transient returns; CD timing remains an explicit deferred boundary')
