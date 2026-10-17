#!/usr/bin/env python3
"""Seed one aircraft ground impact and observe its live effect consumers.

A private silent process receives an explicitly controlled falling-aircraft
state through GDB. The original pool/SSD arithmetic has separate comparisons;
this check establishes the actor-to-pool-to-scene handoff and clean rendering.
"""
import argparse
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--data-dir',type=Path,required=True)
p.add_argument('--mission',default='602')
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='tfx-effects-') as temporary:
 directory=Path(temporary);install=directory/'TFX';install.mkdir()
 for name in ('DID.DAT','TFX.DAT'):(install/name).symlink_to((a.data_dir/name).resolve())
 (install/'TFX.CFG').write_bytes(b'CONTROL=0\r\nMODEL=0\r\nSOUNDFX=0\r\nMUSIC=0\r\nREALISM=0,0,1,1,0,0,0\r\n')
 read,write=os.pipe();display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);os.close(write);game=None
 try:
  if not select.select([read],[],[],5)[0]:raise RuntimeError('private display did not start')
  number=os.read(read,64).decode().strip();os.close(read)
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=temporary,XMODIFIERS='@im=none')
  for key in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
  env['ASAN_OPTIONS']=env.get('ASAN_OPTIONS','')+':detect_leaks=0'
  def run(*args):return subprocess.run(args,env=env,check=True,capture_output=True,text=True,timeout=5)
  script=['set pagination off','set confirm off','set startup-with-shell off','set print thread-events off','set $spawned = 0',
   'break tfx::actors::air_runtime::advance_actor if index == 0','commands','silent',
   'set this->actors._M_elems[index]._M_payload._M_payload._M_value.actions = 3',
   'set this->actors._M_elems[index]._M_payload._M_payload._M_value.flight.input_ticks = 0',
   'set this->actors._M_elems[index]._M_payload._M_payload._M_value.flight.pose.position.y = 0',
   'printf "TFX_EFFECTS_SEEDED\\n"','disable 1','continue','end',
   'break tfx::world::effect_pool::spawn','commands','silent','set $spawned = 1',
   'printf "TFX_EFFECTS_SPAWNED\\n"','disable 2','continue','end',
   'break tfx::world::effect_position if $spawned','commands','silent',
   'printf "TFX_EFFECTS_POSITIONED\\n"','disable 3','continue','end',
   'break tfx::world::scene::draw if $spawned','commands','silent',
   'printf "TFX_EFFECTS_DRAWN\\n"','disable 4','continue','end']
  debugger=directory/'observe.gdb';debugger.write_text('\n'.join(script+['run'])+'\n');log=directory/'game.log'
  with log.open('w') as output:
   game=subprocess.Popen(['gdb','--quiet','--batch','-x',str(debugger),'--args',str((a.build/'tfx').resolve()),'--data-dir',str(install),'--mission',a.mission,'--scale','2'],env=env,stdout=output,stderr=subprocess.STDOUT)
   def await_text(label,timeout=45):
    marker='TFX_EFFECTS_'+label;deadline=time.monotonic()+timeout
    while time.monotonic()<deadline and game.poll() is None:
     if marker in log.read_text():return
     time.sleep(.05)
    raise RuntimeError('missing '+marker+':\n'+log.read_text()[-6000:])
   deadline=time.monotonic()+30;window=None
   while time.monotonic()<deadline and game.poll() is None:
    windows=subprocess.run(['xdotool','search','--onlyvisible','--name','TFX C'],env=env,capture_output=True,text=True).stdout.splitlines()
    if windows:window=windows[0];break
    time.sleep(.05)
   if not window:raise RuntimeError(log.read_text()[-6000:])
   run('xdotool','windowfocus','--sync',window)
   for label in ('SEEDED','SPAWNED','POSITIONED','DRAWN'):await_text(label)
   run('xdotool','keydown','Shift_L+q');time.sleep(.15);run('xdotool','keyup','Shift_L+q');game.wait(timeout=15)
   text=log.read_text();assert game.returncode==0 and 'exited normally' in text and 'ERROR:' not in text and 'Sanitizer' not in text,text[-6000:]
   print('Private silent effect handoff passes: explicitly seeded aircraft impact, real actor effect request, pool spawn, word placement, world drawing and clean exit')
 finally:
  for process in (game,display):
   if process is not None and process.poll() is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait()
