#!/usr/bin/env python3
"""Exercise enrolment, pilot loading, training and Tour review on a private X11 display.

Only DID.DAT and TFX.DAT are linked into the private install. No user pilot save,
training marker, desktop display or input device is read or changed.
"""
import argparse
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time
from window_input import confirm_flight_quit

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--data-dir',type=Path,required=True)
args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='tfx-frontend-window-') as temporary:
    directory=Path(temporary)
    install=directory/'TFX';install.mkdir()
    for name in ('DID.DAT','TFX.DAT'):(install/name).symlink_to((args.data_dir/name).resolve())
    read,write=os.pipe()
    display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write);game=None
    try:
        if not select.select([read],[],[],5)[0]:raise RuntimeError('private X11 display did not start')
        number=os.read(read,64).decode().strip();os.close(read)
        environment=dict(os.environ,DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=temporary,XMODIFIERS='@im=none')
        for name in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):environment.pop(name,None)
        def run(*command):return subprocess.run(command,env=environment,timeout=5,capture_output=True,text=True,check=True)
        def tap(key):run('xdotool','key','--clearmodifiers',key);time.sleep(.1)
        with (directory/'game.log').open('w+') as log:
            def start():
                global game
                game=subprocess.Popen([str((args.build/'tfx').resolve()),'--data-dir',str(install),'--skip-intro','--scale','2'],env=environment,stdout=log,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+10
                while time.monotonic()<deadline and game.poll() is None:
                    found=subprocess.run(['xdotool','search','--onlyvisible','--name','TFX C'],env=environment,capture_output=True,text=True,timeout=5)
                    if found.stdout.strip():
                        window=found.stdout.splitlines()[0];run('xdotool','windowfocus','--sync',window);time.sleep(1);return window
                    time.sleep(.05)
                log.seek(0);raise RuntimeError('front-end window did not appear:\n'+log.read()[-4000:])
            def arm_fws(window):
                # Let the original forty-stage fade complete, then use the first
                # weapon row and the dedicated SSD's mount-1 selection volume.
                time.sleep(1)
                def click(x,y,button=1):
                    run('xdotool','mousemove','--window',window,str(x),str(y));time.sleep(.15)
                    run('xdotool','mousedown',str(button));time.sleep(.1);run('xdotool','mouseup',str(button));time.sleep(.15)
                click(500,72)     # Logical pointer (250,30): AIM 9S.
                click(452,370)    # Logical pointer (226,154): paired mounts 1/6.
                click(452,370,3)  # End placement, retaining the selected stores.
                run('import','-window',window,'/tmp/tfx-arming-window.png')
                click(394,475)    # Original DONE button hotspot.
                deadline=time.monotonic()+10
                while time.monotonic()<deadline and game.poll() is None:
                    log.seek(0)
                    if 'TFX miss501 /' in log.read():return
                    time.sleep(.1)
                log.seek(0);raise RuntimeError('arming DONE did not launch flight: '+run('xdotool','getwindowname',window).stdout+'\n'+log.read()[-4000:])
            def enter_fws(window):
                log.seek(0);log.truncate();
                # Original 4:3 viewport mapping: logical (120,76) -> (240,182).
                run('xdotool','mousemove','--window',window,'240','182');run('xdotool','mousedown','1');time.sleep(.1);run('xdotool','mouseup','1');time.sleep(1)
                deadline=time.monotonic()+15
                armed=False
                while time.monotonic()<deadline and game.poll() is None:
                    if not armed and 'Arming' in run('xdotool','getwindowname',window).stdout:
                        arm_fws(window);armed=True
                    else:tap('Escape')
                    log.seek(0)
                    if 'TFX miss501 /' in log.read():
                        if not armed:raise RuntimeError('training skipped its authored arming screen')
                        time.sleep(.3);tap('shift+q');confirm_flight_quit(environment,window);return
                run('import','-window',window,'/tmp/tfx-frontend-failure.png')
                title=run('xdotool','getwindowname',window).stdout
                log.seek(0);raise RuntimeError('authored training path did not reach flight: '+title+'\n'+log.read()[-4000:])
            def enter_tour(window):
                log.seek(0);log.truncate()
                run('xdotool','mousemove','--window',window,'300','250');run('xdotool','mousedown','1');time.sleep(.1);run('xdotool','mouseup','1');time.sleep(1)
                deadline=time.monotonic()+15
                while time.monotonic()<deadline and game.poll() is None:
                    tap('Escape')
                    if 'todselct' in run('xdotool','getwindowname',window).stdout:break
                else:raise RuntimeError('Tour did not reach squadron selection')
                # The same function first plays several briefing scenes before its menu.
                for _ in range(8):tap('Escape')
                time.sleep(1)
                run('xdotool','mousemove','--window',window,'300','360');run('xdotool','mousedown','1');time.sleep(.1);run('xdotool','mouseup','1');time.sleep(1)
                run('xdotool','mousedown','3')
                try:
                    deadline=time.monotonic()+20
                    while time.monotonic()<deadline and game.poll() is None:
                        # --clearmodifiers would release the held mouse button too.
                        run('xdotool','key','Escape');time.sleep(.1);log.seek(0)
                        if 'TFX miss801 /' in log.read():
                            time.sleep(.3);tap('shift+q');confirm_flight_quit(environment,window);return
                    run('import','-window',window,'/tmp/tfx-tour-window-failure.png')
                    log.seek(0);raise RuntimeError('Tour review did not launch flight: '+run('xdotool','getwindowname',window).stdout+'\n'+log.read()[-4000:])
                finally:run('xdotool','mouseup','3')
            window=start();tap('Return')
            run('xdotool','type','--clearmodifiers','--delay','40','Ada');tap('Return')
            run('xdotool','type','--clearmodifiers','--delay','40','Lovelace');tap('Return')
            tap('ctrl+Return');tap('Return');time.sleep(1.5)
            save=install/'TFXSAV.0'
            if not save.exists():raise RuntimeError('enrolment did not save selected pilot')
            data=save.read_bytes()
            if data[:21].split(bytes(1))[0]!=b'LOVELACE' or data[21:42].split(bytes(1))[0]!=b'ADA' or data[42:63].split(bytes(1))[0]!=b'INFERNO':raise RuntimeError('window input did not reach the original pilot fields')
            enter_fws(window)
            game.wait(timeout=10)
            if game.returncode:raise RuntimeError('flight did not exit cleanly')
            # Reopen, select Load and the same slot; reach the original main menu again.
            window=start();tap('Down');tap('Return');tap('Return');time.sleep(1.5)
            if save.read_bytes()!=data:raise RuntimeError('loading a main-menu pilot changed its saved logical state')
            enter_fws(window);game.wait(timeout=10)
            if game.returncode:raise RuntimeError('reloaded pilot did not enter/exit flight cleanly')
            window=start();tap('Down');tap('Return');tap('Return');time.sleep(1.5)
            enter_tour(window);game.wait(timeout=10)
            if game.returncode:raise RuntimeError('Tour pilot did not enter/exit flight cleanly')
            print('Private X11 front end: edited names, Control qualification, DOS save, main menu, FWS briefing/custom arming/flight, saved-pilot reload and Tour squadron/route-review/flight passed')
    finally:
        if game and game.poll() is None:game.kill();game.wait()
        display.terminate();display.wait(timeout=5)
