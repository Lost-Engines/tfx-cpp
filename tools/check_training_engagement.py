#!/usr/bin/env python3
"""Complete the first FWS engagement using normal controls on a private display.

GDB observes owners, targeting and results; all controls arrive through X11.
--campaign restores a disposable pilot immediately before Hop 1, then checks
arming, combat, debrief and the original next-hop handoff. The supplied save
sets no combat outcome. No original installation is modified.
"""
import argparse
import os
from pathlib import Path
import select
import struct
import subprocess
import tempfile
import time

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--campaign',action='store_true')
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--flight-model',choices=('arcade','simple','military-spec','realistic'),default='arcade')
a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='tfx-training-engagement-') as temporary:
 root=Path(temporary);install=root/'TFX';install.mkdir()
 for name in ('TFX.DAT','DID.DAT'):(install/name).symlink_to((a.data_dir/name).resolve())
 model={'arcade':0,'simple':1,'realistic':2,'military-spec':3}[a.flight_model]
 (install/'TFX.CFG').write_text(f'CONTROL=0\nMODEL={model}\nSOUNDFX=0\nMUSIC=0\nREALISM=0,0,1,1,0,0,0\n')
 if a.campaign:
  import json
  program=next(p for p in json.loads((a.research/'analysis/presentations/programs.json').read_text())if p['name']=='tfx')
  function=next(i for i,f in enumerate(program['functions'])if f['name']=='fws')
  values={'pilotname':'TEST','firstname':'TRAINING','callsign':'SUCCESS','rank':1,'mission':501,'training':1}
  pilot=bytearray()
  for variable in program['variables']:
   value=values.get(variable['name'],'' if variable['string_value']else 0)
   pilot.extend(str(value).encode().ljust(21,b'\0')if variable['string_value']else struct.pack('<I',value))
  pilot.extend(bytes((30-len(program['variables']))*4));pilot.extend(struct.pack('<3H',0,function,5))
  (install/'TFXSAV.0').write_bytes(pilot)
 observer=root/'timing.gdb'
 observer.write_text('''set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
break tfx::platform::fly_mission
commands
silent
python
import json
options=gdb.parse_and_eval('options')
values=gdb.parse_and_eval('campaign')
if values.type.code==gdb.TYPE_CODE_REF:values=values.referenced_value()
printer=gdb.default_visualizer(values)
if printer is None:raise RuntimeError('GNU std::map printer is required for read-only campaign observation')
children=list(printer.children())
numbers={children[i][1]['_M_dataplus']['_M_p'].string():int(children[i+1][1]) for i in range(0,len(children),2)}
print('ENTRY '+json.dumps({'mission':options['mission']['_M_dataplus']['_M_p'].string(),'values':numbers}))
end
continue
end
set $seeker = 0
set $armament = 0
set $progress = 0
break tfx::sensors::air_lock::begin_mission
commands
silent
set $seeker = this
continue
end
break tfx::weapons::armament::select
commands
silent
set $armament = this
continue
end
break tfx::missions::progress::begin_frame
commands
silent
set $progress = this
continue
end
break tfx::missions::progress::finish_frame
commands
silent
python
import json
progress=gdb.parse_and_eval('$progress').dereference()
seeker=gdb.parse_and_eval('$seeker').dereference()
armament=gdb.parse_and_eval('$armament').dereference()
slot=int(armament['selected'])
weapon=int(armament['pylons']['_M_elems'][slot]['weapon']) if 0<=slot<10 else -1
print('COMBAT '+json.dumps([int(progress['results']['enemy_aircraft_down']),int(progress['results']['completed']),int(seeker['guidance']['_M_payload']['_M_engaged']),int(seeker['lock_ticks']),weapon]))
end
continue
end
run
''')
 read,write=os.pipe()
 display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 os.close(write);game=None
 try:
  if not select.select([read],[],[],5)[0]:raise RuntimeError('private X11 display did not start')
  number=os.read(read,64).decode().strip();os.close(read)
  env=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=temporary,XMODIFIERS='@im=none')
  env['ASAN_OPTIONS']=env.get('ASAN_OPTIONS','')+':detect_leaks=0'
  for name in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):env.pop(name,None)
  def host(*command):return subprocess.run(command,env=env,timeout=5,check=True,capture_output=True,text=True)
  checked=0
  for mission in (501,):
   with (root/f'{mission}.log').open('w+') as log:
    game=subprocess.Popen(['gdb','--quiet','--batch','--return-child-result','-x',str(observer),'--args',str((a.build/'tfx').resolve()),'--data-dir',str(install),*(['--skip-intro']if a.campaign else ['--mission',str(mission)]),'--control','keyboard','--flight-model',a.flight_model,'--scale','2'],env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT)
    window=None;deadline=time.monotonic()+30
    while time.monotonic()<deadline and game.poll() is None:
     found=subprocess.run(['xdotool','search','--onlyvisible','--name','TFX C'],env=env,capture_output=True,text=True)
     if found.stdout.strip():window=found.stdout.splitlines()[0];break
     time.sleep(.05)
    if window is None:
     log.seek(0);raise RuntimeError('flight window did not appear:\n'+log.read()[-4000:])
    host('xdotool','windowfocus','--sync',window)
    def records():
     import json
     log.seek(0)
     return [json.loads(line[len('COMBAT '):]) for line in log.read().splitlines() if line.startswith('COMBAT ')]
    def wait_for(predicate,label,timeout=30):
     deadline=time.monotonic()+timeout
     while time.monotonic()<deadline and game.poll() is None:
      current=records()
      if current and predicate(current[-1]):return current[-1]
      time.sleep(.05)
     log.seek(0);raise RuntimeError(label+': '+str(current[-4:])+'\n'+log.read()[-4000:])
    def tap(key):
     host('xdotool','keydown',key);time.sleep(.15);host('xdotool','keyup',key)
    if a.campaign:
     time.sleep(1)
     tap('Down');tap('Return');tap('Return')
     deadline=time.monotonic()+30
     while time.monotonic()<deadline and game.poll() is None:
      title=host('xdotool','getwindowname',window).stdout
      if 'Arming' in title:break
      time.sleep(.05)
     assert 'Arming' in title,title
     time.sleep(1)
     for x in (202,394):
      host('xdotool','mousemove','--window',window,str(x),'477');time.sleep(.15)
      host('xdotool','mousedown','1');time.sleep(.15);host('xdotool','mouseup','1');time.sleep(.2)
    wait_for(lambda row:True,'initial flight')
    tap('Return')
    tap('t')
    lock=wait_for(lambda row:row[2] and row[3]==0 and row[4]==4,'AMRAAM lock')
    print('LOCK',lock,flush=True)
    tap('space')
    kill=wait_for(lambda row:row[0]>=1,'enemy loss')
    print('KILL',kill,flush=True)
    complete=wait_for(lambda row:row[1],'objective complete')
    print('COMPLETE',complete,flush=True)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
     log.seek(0)
     if 'Mission result:' in log.read():break
     time.sleep(.05)
    log.seek(0);text=log.read()
    assert 'Mission result:' in text and 'outcome 0' in text,text[-4000:]
    checked=len(records())
    if a.campaign:
     deadline=time.monotonic()+30
     while time.monotonic()<deadline and game.poll() is None:
      title=host('xdotool','getwindowname',window).stdout
      if 'Arming' in title:break
      tap('space');time.sleep(.1)
     assert 'Arming' in title,('following mission not reached',title)
     import json
     log.seek(0)
     entries=[json.loads(line[len('ENTRY '):])for line in log.read().splitlines()if line.startswith('ENTRY ')]
     assert len(entries)==2 and entries[0]['mission']=='miss501' and entries[1]['mission']=='miss502',entries
     continued=entries[1]['values']
     assert continued['a2akills']>=1 and continued['num_miss']>=1 and continued['score']>0 and continued['mission']==502,continued
     # FWS's SPOS belongs to training graduation, not each hop. Do not invent
     # a per-hop autosave merely to satisfy this integration check.
     assert (install/'TFXSAV.0').read_bytes()==pilot,'unexpected per-hop save rewrite'
     time.sleep(1);tap('Escape')
     wait_for(lambda row:row[0]==0,'next hop enters flight')
    host('xdotool','keydown','Shift_L');host('xdotool','keydown','q');time.sleep(.15)
    host('xdotool','keyup','q');host('xdotool','keyup','Shift_L')
    game.wait(timeout=15)
    if game.returncode:
     log.seek(0);raise RuntimeError('flight failed:\n'+log.read()[-4000:])
  print(f'Private X11 training engagement passed: {checked} real frames, AMRAAM lock/release, enemy loss, objective completion, successful FINISH'+('; original pilot/arming/debrief and next-hop campaign values'if a.campaign else ''))
 finally:
  for process in (game,display):
   if process is not None and process.poll() is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait()
