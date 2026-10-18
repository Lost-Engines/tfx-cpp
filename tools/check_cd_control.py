#!/usr/bin/env python3
"""Compare CD flight selection, polling and mute/restart against original 2.05 code.

MSCDEX/PCM transport is an explicit boundary. The actual launch music block,
CD polling arithmetic, cue gate and music enable/disable handlers execute.
"""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
import wave
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
a=p.parse_args();reference=a.research/'installs/cd_1994_09/TFX'
operations=[]
for pending in (0,10,11,12,13,14,15,16):
 operations += [('begin',pending),('cue',9),('drain',0)]
 for ticks in (0,1,298,1,1,299,1,1,600,601,65535,1,300,301):operations += [('advance',ticks),('drain',0)]
 operations += [('enable',0),('enable',1),('end',0)]
operations += [('play',2),('stop',0)]
with tempfile.TemporaryDirectory(prefix='tfx-cd-control-') as temporary:
 source=Path(temporary)
 for number in range(2,26):
  with wave.open(str(source/f'track{number:02}.wav'),'wb') as file:
   file.setparams((2,2,44100,0,'NONE','not compressed'));file.writeframes(struct.pack('<hh',number*1000,-number*1000)*588)
 tape=''.join(f'{name} {value}\n' for name,value in operations)
 result=subprocess.run([str((a.build/'cd_probe').resolve()),'control',str(source),str(reference/'START.EXE')],input=tape,text=True,capture_output=True,timeout=45)
 assert result.returncode==0,(result.stdout,result.stderr)
 actual=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
 image=NativeReference(reference/'TFX.DAT');image.call(0xde851)
 image.write(0xa4e9,'<B',1);image.write(0xa4e8,'<B',1);image.write(0x8866,'<B',1)
 image.write(0xab4c,'<h',1);image.write(0xa400,'<h',0)
 playing=False;last=0
 def play(im):
  global playing,last
  last=im.cpu.reg_read(r.UC_X86_REG_EAX)&65535;playing=True
  im.write(0x1b192,'<h',last);im.write(0x1b194,'<h',1);im.return_from()
 def stop(im):
  global playing
  playing=False;im.write(0x1b194,'<h',0);im.return_from()
 image.intercept(0xb4000,'CD transport: observe requested index; a separate check verifies MSCDEX sector requests',play)
 image.intercept(0xb40c8,'CD transport: stop PCM playback',stop)
 def status(im):im.cpu.reg_write(r.UC_X86_REG_EAX,int(playing));im.return_from()
 image.intercept(0xb3d34,'CD transport: supply physical playback status',status)
 image.intercept(0xa5be8,'Synthesised stop has no effect on the independent CD transport',lambda im:im.return_from())
 image.intercept(0xa5210,'Synth status outside CD mode is outside this comparison',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
 image.intercept(0x729b8,'Stop after original launch music selection, before ordinary flight setup',lambda im:im.return_from())
 expected=[]
 for action,value in operations:
  if action=='begin':
   image.write(0x16f66,'<h',value);image.call(0x728e5)
  elif action=='cue':image.call(0xa5a9c,eax=value)
  elif action=='drain':playing=False
  elif action=='advance':
   image.write(0x13476,'<H',value);image.call(0xa5374)
  elif action=='enable':
   if value:image.call(0xa5c4c)
   else:image.call(0xa5ce0)
  elif action in ('end','stop'):image.call(0xb40c8)
  elif action=='play':image.call(0xb4000,eax=value)
  expected.append((last+1 if playing else 0,int(playing)))
 assert actual==expected,next((i,operations[i],x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y)
 print(f'{len(operations)} original CD control steps agree: all flight themes, default track, cue suppression, signed timer wrap/backlog, end/restart, mute and return')
