#!/usr/bin/env python3
"""Compare complete original and actual C++ flight sessions.

Checks player/actor/random state and camera/horizon handoffs through the real
launch and frame loops. Reports whole indexed-image differences separately;
--strict-pixels makes remaining drawing differences fail the comparison too.
Requires original resources, Unicorn, did-unpack and GDB. Installs stay read-only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from flight_inputs import FlightInputs

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--mission',type=int,default=501)
p.add_argument('--flight-model',choices=('arcade','simple','military-spec','realistic'),default='arcade')
p.add_argument('--output',type=Path,help='retain native/C++ frames and the read-only observer log in a new directory')
p.add_argument('--frames',type=int,default=4)
p.add_argument('--strict-pixels',action='store_true')
p.add_argument('--inputs',type=Path,help='compare explicit keyboard events/held keys using a private window and virtual external GLFW devices')
p.add_argument('--native-capture',type=Path,help='reuse a prior matching native capture without executing the original again')
a=p.parse_args()
inputs=FlightInputs.read(a.inputs)if a.inputs else FlightInputs([])
tools=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='tfx-flight-session-') as temporary:
    root=a.output.resolve() if a.output else Path(temporary);root.mkdir(parents=True,exist_ok=True)
    native=a.native_capture.resolve() if a.native_capture else root/'native'
    install=root/'TFX';install.mkdir()
    original=(a.research/'installs/cd_1994_09/TFX').resolve()
    for name in ('TFX.DAT','DID.DAT'):(install/name).symlink_to(original/name)
    model={'arcade':0,'simple':1,'realistic':2,'military-spec':3}[a.flight_model]
    (install/'TFX.CFG').write_bytes(f'CONTROL=0\r\nMODEL={model}\r\nSOUNDFX=0\r\nMUSIC=0\r\nREALISM=0,0,1,1,0,0,0\r\n'.encode())
    if not a.native_capture:
        subprocess.run([sys.executable,'-B',str(tools/'capture_native_flight.py'),'--research',str(a.research.resolve()),'--output',str(native),'--mission',str(a.mission),'--frames',str(a.frames),'--flight-model',a.flight_model,*(['--inputs',str(a.inputs.resolve())]if a.inputs else [])],check=True,timeout=300)
    expected=json.loads((native/'session.json').read_text())
    assert expected['mission']==a.mission and expected['flight_model']==a.flight_model and expected['ticks_per_frame']==4,'native capture configuration differs'
    assert expected['presentation_numbers']=={'mission':a.mission,'arcade':1},'native capture inherited campaign state differs'
    assert [row for row in expected.get('inputs',[])if row['frame']<=a.frames]==inputs.rows(a.frames),'native capture keyboard inputs differ'
    assert len(expected['snapshots'])>a.frames,'native capture is shorter than the requested session'
    if 'reference' in expected:
        for name,key in (('TFX.DAT','executable_sha256'),('DID.DAT','archive_sha256')):
            assert hashlib.sha256((original/name).read_bytes()).hexdigest()==expected['reference'][key],('native capture resource differs',name)
    env=dict(os.environ)
    # LSan cannot inspect a process under ptrace; ordinary sanitizer tests keep it enabled.
    env['ASAN_OPTIONS']=env.get('ASAN_OPTIONS','')+':detect_leaks=0'
    command=['gdb','--quiet','--batch','--return-child-result','-x',str(tools/'observe_flight_session.gdb'),'--args',str((a.build/'tfx').resolve()),'--data-dir',str(install),'--mission',str(a.mission),'--control','keyboard','--flight-model',a.flight_model]
    display=None
    try:
        if a.inputs:
            import select
            read,write=os.pipe()
            display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            os.close(write)
            try:
                if not select.select([read],[],[],5)[0]:raise RuntimeError('private X11 display did not start')
                number=os.read(read,64).decode().strip()
            finally:os.close(read)
            env.update(DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=str(root),XMODIFIERS='@im=none',TFX_FLIGHT_INPUTS=json.dumps(inputs.rows(a.frames)),TFX_TOOLS_DIRECTORY=str(tools))
            for name in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):env.pop(name,None)
            command+=['--frames',str(a.frames),'--scale','2']
        else:command+=['--flight-frames',str(a.frames),'--screenshot',str(root/'cpp.ppm')]
        result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=max(180,a.frames*2))
    finally:
        if display is not None:
            display.terminate()
            try:display.wait(timeout=3)
            except subprocess.TimeoutExpired:display.kill();display.wait()
    (root/'observer.log').write_text(result.stdout+result.stderr)
    if a.inputs and result.returncode==0:
        (root/'cpp.indices').write_bytes((root/f'cpp-frame-{a.frames}.indices').read_bytes())
    assert result.returncode==0,(result.stdout+result.stderr)[-6000:]
    assert 'exited normally' in result.stdout and 'ERROR:' not in result.stderr,(result.stdout+result.stderr)[-6000:]
    lines=result.stdout.splitlines()
    def integers(prefix):return [[int(value) for value in line[len(prefix):].split()] for line in lines if line.startswith(prefix)]
    def records(prefix):return [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    before=integers('CPP_PRE ');after=integers('CPP_POST ');world=records('CPP_WORLD ')
    assert len(before)==len(after)==len(world)==a.frames,(len(before),len(after),len(world),a.frames)
    for index,(cpp_pre,cpp_post,cpp_world) in enumerate(zip(before,after,world)):
        native_pre=expected['snapshots'][index];native_post=expected['snapshots'][index+1]
        for cpp,native_pose in ((cpp_pre,native_pre),(cpp_post,native_post)):
            want=native_pose['position']+native_pose['angles']+[native_pose['speed']]
            assert cpp==want,('player',index,cpp,want)
        want={field:native_post[field] for field in ('actors','random')}
        assert cpp_world==want,('world',index,cpp_world,want)
    assert not records('CPP_WARNINGS '),('unhandled scene diagnostics',records('CPP_WARNINGS '))
    if 'trail_events' in expected:
        trails=records('CPP_TRAIL ')
        wanted=[event for event in expected['trail_events']if event[0]<=a.frames]
        assert trails==wanted,('trail samples',len(trails),len(wanted),[(i,got,want)for i,(got,want)in enumerate(zip(trails,wanted))if got!=want][:4])
    radio=records('CPP_RADIO ')
    wanted_radio=[event for event in expected['radio_events'] if event['frame']<=a.frames]
    assert radio==wanted_radio,('radio requests',radio,wanted_radio)
    for field,prefix in (('body_basis','CPP_BODY '),('sensors','CPP_SENSORS '),('armament','CPP_ARMAMENT '),('projectiles','CPP_PROJECTILES '),('player_parts','CPP_PLAYER_PARTS '),('launch_notice','CPP_LAUNCH_NOTICE ')):
        if field in expected['snapshots'][1]:
            actual_records=records(prefix)
            wanted_records=[snapshot[field] for snapshot in expected['snapshots'][1:a.frames+1]]
            assert actual_records==wanted_records,(field,[(i,got,want) for i,(got,want) in enumerate(zip(actual_records,wanted_records),1) if got!=want][:4])
    if 'preflight_projection' in expected:
        assert records('CPP_PREFLIGHT ')==[expected['preflight_projection']],('preflight projection',records('CPP_PREFLIGHT '),expected['preflight_projection'])
    if 'animation' in expected['snapshots'][1]:
        animation=records('CPP_ANIMATION ')
        assert animation==[snapshot['animation'] for snapshot in expected['snapshots'][1:a.frames+1]],('animation',animation,[snapshot['animation'] for snapshot in expected['snapshots'][1:a.frames+1]])
    renders=records('CPP_RENDER ')
    assert len(renders)==a.frames,('render count',len(renders),a.frames)
    different_frames=[]
    for index,render in enumerate(renders,1):
        original_image=(native/f'frame-{index}.indices').read_bytes()
        if render['sha256']!=hashlib.sha256(original_image).hexdigest():different_frames.append(index)
        assert render['pattern_seed']==expected['snapshots'][index]['pattern_seed'],('pattern seed',index,render['pattern_seed'],expected['snapshots'][index]['pattern_seed'])
    cameras=records('CPP_CAMERA_HORIZON ')
    assert cameras==expected['horizons'][:len(cameras)],('camera/horizon',cameras,expected['horizons'][:len(cameras)])
    actual=(root/'cpp.indices').read_bytes();image=(native/f'frame-{a.frames}.indices').read_bytes()
    assert len(actual)==len(image)==64000
    differences=sum(x!=y for x,y in zip(actual,image))
    verified=['player','actors','shared RNG','radio','camera','horizon']
    if 'trail_events' in expected:verified.append('smoke samples')
    verified += [field for field in ('body_basis','sensors','animation','armament','projectiles','player_parts','launch_notice') if field in expected['snapshots'][1]]
    print(f'Mission {a.mission}, {a.flight_model}, {a.frames} complete frames: {", ".join(verified)} agree. Images: {len(different_frames)}/{a.frames} frames differ; final image {differences}/64000 different indices.')
    if a.strict_pixels:assert not different_frames,('whole-frame pixels',different_frames[:20],differences)
