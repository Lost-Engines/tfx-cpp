#!/usr/bin/env python3
"""Exercise weapon selection, store/cannon firing and Escape on a private X11 display.

Requires Xvfb, xdotool, ImageMagick import and Pillow. The private runtime
prevents GLFW from discovering an unrelated desktop Wayland socket.
"""
import argparse
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time
from PIL import Image

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--data-dir',type=Path,required=True)
args=parser.parse_args()
executable=(args.build/'tfx').resolve();data=args.data_dir.resolve()
with tempfile.TemporaryDirectory(prefix='tfx-x11-input-') as temporary:
    directory=Path(temporary)
    read,write=os.pipe()
    display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write);game=None
    try:
        if not select.select([read],[],[],5)[0]:raise RuntimeError('private X11 display did not start')
        number=os.read(read,64).decode().strip();os.close(read)
        environment=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=temporary,XMODIFIERS='@im=none')
        for name in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):environment.pop(name,None)
        def run(*command,**options):return subprocess.run(command,env=environment,timeout=5,**options)
        with (directory/'game.log').open('w+') as log:
            game=subprocess.Popen([str(executable),'--data-dir',str(data),'--scale','2'],env=environment,stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+10;window=None
            while time.monotonic()<deadline and game.poll() is None:
                found=run('xdotool','search','--onlyvisible','--name','TFX C',capture_output=True,text=True)
                if found.stdout.strip():window=found.stdout.splitlines()[0];break
                time.sleep(.05)
            if window is None:
                log.seek(0);raise RuntimeError('game window did not appear:\n'+log.read()[-4000:])
            run('xdotool','windowfocus','--sync',window,check=True);time.sleep(.5)
            before_path=directory/'before.png';after_path=directory/'after.png'
            run('import','-window',window,str(before_path),check=True)
            run('xdotool','key','Return',check=True);time.sleep(.3)
            store_before=directory/'store-before.png';store_after=directory/'store-after.png'
            run('import','-window',window,str(store_before),check=True)
            run('xdotool','key','space',check=True);time.sleep(.3)
            run('import','-window',window,str(store_after),check=True)
            def store_readout(path):
                with Image.open(path) as image:return image.convert('RGB').resize((320,200),Image.Resampling.NEAREST).crop((5,41,150,48)).tobytes()
            if store_readout(store_before)==store_readout(store_after):raise RuntimeError('Enter/Space did not change the carried-weapon inventory readout')
            run('xdotool','key','f',check=True);time.sleep(.1)
            run('xdotool','keydown','space',check=True);time.sleep(1.5)
            run('xdotool','keyup','space',check=True);time.sleep(.2)
            run('import','-window',window,str(after_path),check=True)
            def readout(path):
                with Image.open(path) as image:return image.convert('RGB').resize((320,200),Image.Resampling.NEAREST).crop((5,32,65,39)).tobytes()
            if readout(before_path)==readout(after_path):raise RuntimeError('Space did not change the cannon ammunition readout')
            run('xdotool','key','Escape',check=True);game.wait(timeout=10)
            if game.returncode:
                log.seek(0);raise RuntimeError(log.read()[-4000:])
            print('Private X11 controls passed: Enter/Space releases a store; F/Space fires cannon; Escape exits cleanly')
    finally:
        for process in (game,display):
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait()
