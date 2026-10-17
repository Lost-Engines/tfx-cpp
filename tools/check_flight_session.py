#!/usr/bin/env python3
"""Compare complete original and actual C++ neutral-flight sessions.

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

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--mission',type=int,default=501)
p.add_argument('--flight-model',choices=('arcade','simple','military-spec','realistic'),default='arcade')
p.add_argument('--output',type=Path,help='retain native/C++ frames and the read-only observer log in a new directory')
p.add_argument('--frames',type=int,default=4)
p.add_argument('--strict-pixels',action='store_true')
p.add_argument('--native-capture',type=Path,help='reuse a prior matching native capture without executing the original again')
a=p.parse_args()
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
        subprocess.run([sys.executable,'-B',str(tools/'capture_native_flight.py'),'--research',str(a.research.resolve()),'--output',str(native),'--mission',str(a.mission),'--frames',str(a.frames),'--flight-model',a.flight_model],check=True,timeout=180)
    expected=json.loads((native/'session.json').read_text())
    assert expected['mission']==a.mission and expected['flight_model']==a.flight_model and expected['ticks_per_frame']==4,'native capture configuration differs'
    assert expected['presentation_numbers']=={'mission':a.mission,'arcade':1},'native capture inherited campaign state differs'
    assert len(expected['snapshots'])>a.frames,'native capture is shorter than the requested session'
    env=dict(os.environ)
    # LSan cannot inspect a process under ptrace; ordinary sanitizer tests keep it enabled.
    env['ASAN_OPTIONS']=env.get('ASAN_OPTIONS','')+':detect_leaks=0'
    result=subprocess.run(['gdb','--quiet','--batch','--return-child-result','-x',str(tools/'observe_flight_session.gdb'),'--args',str((a.build/'tfx').resolve()),'--data-dir',str(install),'--mission',str(a.mission),'--control','keyboard','--flight-model',a.flight_model,'--flight-frames',str(a.frames),'--screenshot',str(root/'cpp.ppm')],cwd=root,env=env,capture_output=True,text=True,timeout=180)
    (root/'observer.log').write_text(result.stdout+result.stderr)
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
    radio=records('CPP_RADIO ')
    wanted_radio=[event for event in expected['radio_events'] if event['frame']<=a.frames]
    assert radio==wanted_radio,('radio requests',radio,wanted_radio)
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
    print(f'Mission {a.mission}, {a.flight_model}, {a.frames} complete frames: player, actors, shared RNG, radio, camera and horizon state agree. Images: {len(different_frames)}/{a.frames} frames differ; final image {differences}/64000 different indices.')
    if a.strict_pixels:assert not different_frames,('whole-frame pixels',different_frames[:20],differences)
