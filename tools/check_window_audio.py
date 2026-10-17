#!/usr/bin/env python3
"""Check real PCM output and live sound switches using a private Pulse/X11 sink.

No user's installation or audible output is used. This checks the live gear
request, stereo callback output, menu disabling/enabling and device shutdown.
Original sample bytes and clock/controller details have separate native checks.
"""
import argparse
import array
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--data-dir',type=Path,required=True)
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='tfx-audio-') as temporary:
 directory=Path(temporary);install=directory/'TFX';install.mkdir()
 for name in ('DID.DAT','TFX.DAT'):(install/name).symlink_to((a.data_dir/name).resolve())
 (install/'TFX.CFG').write_bytes(b'CONTROL=0\r\nMODEL=0\r\nSOUNDFX=1\r\nMUSIC=1\r\nREALISM=0,0,1,1,0,0,0\r\nDETAIL=2\r\n')
 sink='tfx_check_'+str(os.getpid());module=None;display=None;game=None;capture=None
 try:
  module=subprocess.check_output(['pactl','load-module','module-null-sink','sink_name='+sink,'rate=48000','channels=2'],text=True).strip()
  read,write=os.pipe();display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(write)
  if not select.select([read],[],[],5)[0]:raise RuntimeError('private display did not start')
  number=os.read(read,64).decode().strip();os.close(read)
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=temporary,XMODIFIERS='@im=none',PULSE_SINK=sink)
  # Keep the user's Pulse socket discovery; its only test stream goes to the
  # explicitly selected null sink. X11 must not inherit a Wayland selection.
  if 'XDG_RUNTIME_DIR' in os.environ:env['XDG_RUNTIME_DIR']=os.environ['XDG_RUNTIME_DIR']
  else:env.pop('XDG_RUNTIME_DIR',None)
  for key in ('WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
  env['XDG_SESSION_TYPE']='x11'
  pcm=directory/'capture.f32';log=directory/'game.log'
  def run(*args):return subprocess.run(args,env=env,check=True,capture_output=True,text=True,timeout=5)
  with pcm.open('wb') as recording, log.open('w') as output:
   capture=subprocess.Popen(['parec','--device='+sink+'.monitor','--format=float32le','--rate=48000','--channels=2'],stdout=recording,stderr=subprocess.DEVNULL,env=env)
   game=subprocess.Popen([str((a.build/'tfx').resolve()),'--data-dir',str(install),'--mission','513','--scale','2'],stdout=output,stderr=subprocess.STDOUT,env=env)
   deadline=time.monotonic()+30;window=None
   while time.monotonic()<deadline and game.poll() is None:
    windows=subprocess.run(['xdotool','search','--onlyvisible','--name','TFX C'],env=env,capture_output=True,text=True).stdout.splitlines()
    if windows and 'PCM output:' in log.read_text():window=windows[0];break
    time.sleep(.1)
   assert window,log.read_text()
   streams=json.loads(run('pactl','-f','json','list','sink-inputs').stdout)
   owned=[stream for stream in streams if stream.get('properties',{}).get('application.process.id')==str(game.pid)]
   assert len(owned)==1,('cannot isolate game PCM stream',owned,log.read_text())
   run('pactl','move-sink-input',str(owned[0]['index']),sink)
   run('xdotool','windowfocus','--sync',window)
   def tap(key):run('xdotool','keydown',key);time.sleep(.12);run('xdotool','keyup',key);time.sleep(.15)
   def click(x,y):
    run('xdotool','mousemove','--window',window,str(round(x*2)),str(round(y*2.4)))
    run('xdotool','mousedown','1');time.sleep(.12);run('xdotool','mouseup','1');time.sleep(.2)
   def samples(start):
    data=pcm.read_bytes()[start:];data=data[:len(data)//8*8];values=array.array('f');values.frombytes(data)
    assert values and all(abs(x)<1.1 for x in values),(len(data),capture.poll(),log.read_text())
    assert all(values[i]==values[i+1] for i in range(0,len(values),2)),'dual mono changed'
    return values
   time.sleep(1);start=pcm.stat().st_size;tap('g');time.sleep(2.8)
   first=samples(start);assert max(map(abs,first))>.1,'gear sound did not reach the PCM device'
   tap('grave');click(104,124);click(152,172);time.sleep(2.5)
   start=pcm.stat().st_size;tap('g');time.sleep(2.5)
   muted=samples(start);assert max(map(abs,muted))<1e-7,'sound-off still played a new request'
   tap('grave');click(128,124);click(152,172);time.sleep(.4)
   start=pcm.stat().st_size;tap('g');time.sleep(2.8)
   resumed=samples(start);assert max(map(abs,resumed))>.1,'sound-on did not restore playback'
   tap('Shift_L+q');game.wait(timeout=10)
   assert game.returncode==0 and 'ERROR:' not in log.read_text(),log.read_text()
   assert b'SOUNDFX=1\r\nMUSIC=1' in (install/'TFX.CFG').read_bytes()
   print('Private Pulse/X11 audio passed: live gear requests, continuous stereo output, sound off/on, original config retained and clean device shutdown')
 finally:
  for process in (game,capture,display):
   if process is not None and process.poll() is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait()
  if module is not None:subprocess.run(['pactl','unload-module',module],check=True)
