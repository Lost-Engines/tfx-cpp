#!/usr/bin/env python3
"""Join original 32-bit flight music control to original 16-bit OSL playback.

Only filenames/resource I/O, protected/real-mode register transfer and physical
MPU I/O/settling are supplied. Controller, resource replacement, sequencing,
patch uploads, mute/restart and shared IRQ code all execute. MIDI delivery is
compared at sample-frame boundaries; instruction-level serial latency is outside
this check, as it is for the hardware adapter. No synthesiser ROMs are required.
"""
import argparse
from pathlib import Path
import subprocess
import sys
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_osl import NativeOSL
from unicorn import x86_const as r16

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--mode',choices=('lapc','scc','fm'),default='lapc')
a=p.parse_args();directory=a.research/'installs/cd_1994_09/TFX';launcher=(directory/'START.EXE').read_bytes()
sys.path.insert(0,str(a.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={e.identifier:e for e in archive.entries}
n=NativeOSL(launcher,'scc' if a.mode=='scc' else 'adl' if a.mode=='fm' else 'rld');im=NativeReference(directory/'TFX.DAT');im.call(0xde851)
now=0;events=[];status=0;pending=[];system=[]
def byte(value):
 global status,pending,system
 if value>=248:events.append([now,3,value,0,0]);return
 if system:
  if value==247:system.append(value);events.append([now,len(system),*system]);system=[];status=0;pending=[];return
  if value<128:system.append(value);return
  system=[];status=0;pending=[]
 if value>=128:
  pending=[];status=value
  if value==240:system=[value];status=0
  elif value in (246,247):events.append([now,3,value,0,0]);status=0
  elif value in (244,245):status=0
  return
 if not status:return
 pending.append(value);length=1 if status&240 in (192,208) or status in (241,243) else 2
 if len(pending)==length:
  events.append([now,3,status,*pending,*([0]if length==1 else [])]);pending=[]
  if status>=240:status=0

def collect():
 if a.mode=='fm':
  assert len(n.events)%2==0
  for index in range(0,len(n.events),2):events.append([now,2,*n.events[index:index+2]])
 else:
  for value in n.events:byte(value)
 n.events.clear()

names=[];at=0x52a0 if a.mode=='scc' else 0x50f5 if a.mode=='fm' else 0x4f6e
while launcher[at:at+6]==b'tunes\\':
 end=launcher.index(0,at);names.append(launcher[at:end].decode());at=end+1
im.cpu.mem_map(0x1000,0xf000);im.cpu.mem_map(0x300000,0x30000);bridge=0x320000;im.cpu.mem_write(bridge,b'\xc3');im.write(0xa3f8,'<I',bridge)
source=None;loads=[]
def filename(cpu,address,size,user):
 global source
 pointer=cpu.reg_read(r.UC_X86_REG_EAX);name=bytearray()
 while (value:=cpu.mem_read(pointer+len(name),1)[0]):name.append(value)
 name=name.decode();identifier=archive.hash_name(name)
 if identifier in entries:source=archive.unpack(entries[identifier])
 else:
  path=directory
  for part in name.replace('\\','/').split('/'):
   part=part.rstrip(' .');path=next(entry for entry in path.iterdir()if entry.name.lower()==part.lower())
  sys.path.insert(0,str(a.research/'did-unpack'));from did_unpack import decompress_ra
  raw=path.read_bytes();source=decompress_ra(raw)if raw[:2]==b'RA'else raw
 loads.append(name);im.return_from()
im.cpu.hook_add(UC_HOOK_CODE,filename,begin=im.native(0xa51ec),end=im.native(0xa51ec))
def device(cpu,address,size,user):
 command=im.read(0x16f50,'<I')[0]>>8&255
 if command==0x13:
  index=im.read(0x16f44,'<I')[0]&255;assert index<len(names),(index,names)
  im.cpu.mem_write(0x2000,names[index].encode()+b'\0');im.write(0x16f50,'<I',0x2000);im.write(0x16f48,'<I',0)
 elif command==0x1b:im.write(0x16f50,'<I',0x4000);im.write(0x16f48,'<I',0)
 elif command==0x14:
  assert source is not None
  result,carry=n.load(source);assert not carry,(command,result)
  im.write(0x16f50,'<I',result)
 elif command in (3,4,6,7,0x1c,0x1d):
  values={name:im.read(at,'<I')[0]&65535 for name,at in [('AX',0x16f50),('BX',0x16f44),('CX',0x16f4c),('DX',0x16f48)]}
  n.call(0x9b4,'iret',**values)
  for name,at in [('AX',0x16f50),('BX',0x16f44),('CX',0x16f4c),('DX',0x16f48)]:im.write(at,'<I',n.cpu.reg_read(getattr(r16,'UC_X86_REG_'+name)))
 else:raise AssertionError(('unexpected original bridge command',hex(command)))
 collect();im.return_from()
im.cpu.hook_add(UC_HOOK_CODE,device,begin=bridge,end=bridge)
im.write(0xa4e9,'<B',4 if a.mode=='scc'else 3 if a.mode=='fm'else 2);im.write(0xa4e8,'<B',3);im.write(0x8866,'<B',1);im.write(0xa3d8,'<B',1);im.write(0xab4c,'<h',0);im.write(0xa3e4,'<i',-1)
for at,fmt in [(0x16f66,'<H'),(0xa3e0,'<H'),(0x16f68,'<B'),(0xabe9,'<B'),(0x12c04,'<H'),(0x86ce,'<B')]:im.write(at,fmt,0)
n.initialise();collect();n.shared_timer();assert n.pit==[85,85]
settling=48000 if a.mode=='scc'else 4800;now=settling;irq=0
throttle=.8;engines=True
def plane():im.write(0x133f8,'<f',throttle);im.write(0x14880,'<2d',float(engines),0);im.write(0x13476,'<H',1)
def begin():
 if not im.read(0x16f66,'<H')[0]:im.write(0x16f66,'<H',10)
 im.call(0xa5d68,eax=10);im.call(0xa5a9c,eax=0)
im.call(0xa5d68,eax=12);plane();begin();flight=True
for frame in range(1000):
 if frame==100:im.call(0xa5a9c,eax=9)
 if frame==150:im.call(0xa5a9c,eax=10)
 if frame==250:im.write(0x8866,'<B',0);im.call(0xa5ce0)
 if frame==350:throttle=1
 if frame==450:engines=False
 if frame==550:engines=True;throttle=.6
 if frame==600:im.write(0x8866,'<B',1);im.call(0xa5c4c)
 if frame==700:im.call(0xa5a9c,eax=6)
 if frame==800:im.call(0xa5f34);flight=False
 if frame==810:im.call(0xa5d68,eax=1);im.call(0xa5b64,eax=0)
 if frame==900:plane();begin();flight=True
 plane()
 if flight:im.call(0xa5374)
 end=now+480
 while (when:=settling+((irq+1)*48000*21845+1193181)//1193182)<end:
  now=when;n.host_tick();collect();irq+=1
 now=end
im.call(0xa5f34)
actual=[list(map(int,line.split()))for line in subprocess.check_output([str((a.build/'music_session_probe').resolve()),str(directory/'START.EXE'),str(directory/'DID.DAT'),a.mode],text=True).splitlines()]
for index,(left,right)in enumerate(zip(actual,events)):
 assert left==right,(index,'cpp',left[:28],'original',right[:28],'loads',loads)
assert len(actual)==len(events),(len(actual),len(events))
print(f'{a.mode}: {len(events)} complete device events and sample timestamps agree through original 32/16-bit mission start, cue changes, mute/engine state, restart and presentation return; {irq} shared IRQ ticks; {len(loads)} original file loads')
