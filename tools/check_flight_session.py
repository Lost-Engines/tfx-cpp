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
p.add_argument('--career-rules',action='store_true',help='compare career permissions/stores with inherited arcade=0')
p.add_argument('--output',type=Path,help='retain native/C++ frames and the read-only observer log in a new directory')
p.add_argument('--frames',type=int,default=4)
p.add_argument('--ticks-per-frame',type=int,default=4,help='declared external timer interval, before native frame clamps')
p.add_argument('--until-result',action='store_true',help='compare through a natural result and FINISH, with --frames as the upper bound')
p.add_argument('--until-landed',action='store_true',help='compare an automatic approach through its natural stopped state')
p.add_argument('--strict-pixels',action='store_true')
p.add_argument('--inputs',type=Path,help='compare explicit keyboard events/held keys using a private window and virtual external GLFW devices')
p.add_argument('--native-capture',type=Path,help='reuse a prior matching native capture without executing the original again')
p.add_argument('--lapc-effects',action='store_true',help='compare live LAPC effect requests; the host PCM device is muted before start')
p.add_argument('--rom-dir',type=Path,help='Roland ROM directory for --lapc-effects')
a=p.parse_args()
if a.until_result and a.until_landed:p.error('choose either --until-result or --until-landed')
if a.lapc_effects and (not a.inputs or not a.rom_dir):p.error('--lapc-effects needs --inputs and --rom-dir')
if not 4 <= a.ticks_per_frame <= 65535:p.error('--ticks-per-frame must be between 4 and 65535')
inputs=FlightInputs.read(a.inputs)if a.inputs else FlightInputs([])
tools=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='tfx-flight-session-') as temporary:
    root=a.output.resolve() if a.output else Path(temporary);root.mkdir(parents=True,exist_ok=True)
    native=a.native_capture.resolve() if a.native_capture else root/'native'
    install=root/'TFX';install.mkdir()
    original=(a.research/'installs/cd_1994_09/TFX').resolve()
    for name in (('TFX.DAT','DID.DAT','START.EXE')if a.lapc_effects else ('TFX.DAT','DID.DAT')):(install/name).symlink_to(original/name)
    model={'arcade':0,'simple':1,'realistic':2,'military-spec':3}[a.flight_model]
    device=2 if a.lapc_effects else 0
    (install/'TFX.CFG').write_bytes(f'CONTROL=0\r\nMODEL={model}\r\nSOUNDFX={device}\r\nMUSIC={device}\r\nREALISM=0,0,1,1,0,0,0\r\n'.encode())
    if not a.native_capture:
        subprocess.run([sys.executable,'-B',str(tools/'capture_native_flight.py'),'--research',str(a.research.resolve()),'--output',str(native),'--mission',str(a.mission),'--frames',str(a.frames),'--ticks-per-frame',str(a.ticks_per_frame),'--flight-model',a.flight_model,*(['--inputs',str(a.inputs.resolve())]if a.inputs else []),*(['--until-result']if a.until_result else []),*(['--until-landed']if a.until_landed else []),*(['--lapc-effects']if a.lapc_effects else []),*(['--career-rules']if a.career_rules else [])],check=True,timeout=max(300,a.frames*4))
    expected=json.loads((native/'session.json').read_text())
    assert expected.get('resource_root')=='TFX','native capture predates the corrected DOS texture root; recapture it'
    assert expected['mission']==a.mission and expected['flight_model']==a.flight_model and expected['ticks_per_frame']==a.ticks_per_frame,'native capture configuration differs'
    assert expected.get('lapc_effects',False)==a.lapc_effects,'native audio capture configuration differs'
    assert expected['presentation_numbers']=={'mission':a.mission,'arcade':0 if a.career_rules else 1},'native capture inherited campaign state differs'
    if a.until_result:
        terminal=expected.get('terminal',{})
        assert terminal.get('returned') and 1<=terminal['frame']<=a.frames,'native capture did not return through a result within the requested bound'
        a.frames=terminal['frame']
    if a.until_landed:
        landed=expected.get('landing_checkpoint',{})
        assert 1<=landed.get('frame',0)<=a.frames,'native automatic landing did not stop within the requested bound'
        a.frames=landed['frame']
    assert [row for row in expected.get('inputs',[])if row['frame']<=a.frames]==inputs.rows(a.frames),'native capture keyboard inputs differ'
    assert len(expected['snapshots'])==a.frames+1,'reuse a native capture ending at the requested frame; untagged render events cannot be sliced safely'
    if 'reference' in expected:
        for name,key in (('TFX.DAT','executable_sha256'),('DID.DAT','archive_sha256')):
            assert hashlib.sha256((original/name).read_bytes()).hexdigest()==expected['reference'][key],('native capture resource differs',name)
    env=dict(os.environ)
    if a.lapc_effects:env['TFX_OBSERVE_LAPC']='1'
    # LSan cannot inspect a process under ptrace; ordinary sanitizer tests keep it enabled.
    env['ASAN_OPTIONS']=env.get('ASAN_OPTIONS','')+':detect_leaks=0'
    if (native/'radar.json').exists():env['TFX_OBSERVE_RADAR_CONTEXT']='1'
    if 'projectile_guidance' in expected:env['TFX_OBSERVE_PROJECTILE_GUIDANCE']='1'
    # GDB reads sourced files incrementally. Retain the exact observer beside
    # the capture so ongoing development cannot change a running comparison.
    observer=root/'observe.gdb';observer.write_bytes((tools/'observe_flight_session.gdb').read_bytes())
    command=['gdb','--quiet','--batch','--return-child-result','-x',str(observer),'--args',str((a.build/'tfx').resolve()),'--data-dir',str(install),'--mission',str(a.mission),'--control','keyboard','--flight-model',a.flight_model]
    if a.lapc_effects:command+=['--rom-dir',str(a.rom_dir.resolve())]
    if a.career_rules:command.append('--career-rules')
    display=None;audio_module=None
    try:
        if a.lapc_effects:
            sink='tfx_reference_'+str(os.getpid())
            audio_module=subprocess.check_output(['pactl','load-module','module-null-sink','sink_name='+sink,'rate=48000','channels=2'],text=True).strip()
            env['PULSE_SINK']=sink
        if a.inputs:
            import select
            read,write=os.pipe()
            display=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','1024x768x24','-nolisten','tcp'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            os.close(write)
            try:
                if not select.select([read],[],[],5)[0]:raise RuntimeError('private X11 display did not start')
                number=os.read(read,64).decode().strip()
            finally:os.close(read)
            env.update(DISPLAY=':'+number,LIBGL_ALWAYS_SOFTWARE='1',XDG_RUNTIME_DIR=str(root),XMODIFIERS='@im=none',TFX_FLIGHT_INPUTS=json.dumps(inputs.rows(a.frames)),TFX_TICKS_PER_FRAME=str(a.ticks_per_frame),TFX_TOOLS_DIRECTORY=str(tools))
            # Pulse socket discovery needs the real runtime directory; the
            # test's only stream explicitly selects its private silent sink.
            if a.lapc_effects:
                if 'XDG_RUNTIME_DIR' in os.environ:env['XDG_RUNTIME_DIR']=os.environ['XDG_RUNTIME_DIR']
                else:env.pop('XDG_RUNTIME_DIR',None)
            for name in ('WAYLAND_DISPLAY','XDG_SESSION_TYPE','DBUS_SESSION_BUS_ADDRESS'):env.pop(name,None)
            command+=['--frames',str(a.frames),'--scale','2']
        else:
            if a.ticks_per_frame!=4:raise ValueError('custom timer intervals require an explicit input file and private virtual devices')
            command+=['--flight-frames',str(a.frames),'--screenshot',str(root/'cpp.ppm')]
        result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=max(180,a.frames*2))
    finally:
        if display is not None:
            display.terminate()
            try:display.wait(timeout=3)
            except subprocess.TimeoutExpired:display.kill();display.wait()
        if audio_module is not None:subprocess.run(['pactl','unload-module',audio_module],check=True)
    (root/'observer.log').write_text(result.stdout+result.stderr)
    if a.inputs and result.returncode==0:
        (root/'cpp.indices').write_bytes((root/f'cpp-frame-{a.frames}.indices').read_bytes())
    assert result.returncode==0,(result.stdout+result.stderr)[-6000:]
    assert 'exited normally' in result.stdout and 'ERROR:' not in result.stderr,(result.stdout+result.stderr)[-6000:]
    lines=result.stdout.splitlines()
    def integers(prefix):return [[int(value) for value in line[len(prefix):].split()] for line in lines if line.startswith(prefix)]
    def records(prefix):return [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    if a.lapc_effects:
        assert 'CPP_HOST_AUDIO_MUTED' in lines,'host PCM device was not muted before start'
        assert records('CPP_LAPC_CUE ')==[event for event in expected['lapc_requests']if event['frame']<=a.frames],('LAPC effect requests',records('CPP_LAPC_CUE '),expected['lapc_requests'])
        if expected.get('sample_requests') is not None:
            wanted=[event for event in expected['sample_requests']if event['frame']<=a.frames]
            assert records('CPP_SAMPLE_REQUEST ')==wanted,('sample requests',records('CPP_SAMPLE_REQUEST '),wanted)
    if a.until_result:
        finished=records('CPP_FINISH ')
        assert len(finished)==1,('FINISH execution count',finished)
        wanted=expected['terminal']['campaign'];actual=finished[0]
        differences={key:[actual.get(key,0),wanted.get(key,0)]for key in actual.keys()|wanted.keys()if actual.get(key,0)!=wanted.get(key,0)}
        assert not differences,('final campaign values',differences)
    if (native/'radar.json').exists():
        events=json.loads((native/'radar.json').read_text())
        wanted=[{**event,'projectiles':[{key:value for key,value in shot.items()if key!='previous'}for shot in event['projectiles']]}for event in events if event['frame']<=a.frames]
        actual=records('CPP_RADAR_INPUT ')
        assert actual==wanted,('live radar inputs',[(got,want)for got,want in zip(actual,wanted)if got!=want][:3],len(actual),len(wanted))
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
    if 'hud_alert_events' in expected:
        wanted=[event for event in expected['hud_alert_events']if event['frame']<=a.frames]
        assert records('CPP_HUD_ALERT ')==wanted,('HUD warning requests',records('CPP_HUD_ALERT '),wanted)
    radio=records('CPP_RADIO ')
    wanted_radio=[event for event in expected['radio_events'] if event['frame']<=a.frames]
    assert radio==wanted_radio,('radio requests',radio,wanted_radio)
    initial=records('CPP_INITIAL ')
    assert len(initial)==1,('player initialization count',initial)
    if 'armament' in expected['snapshots'][0]:
        assert initial[0]['fuel']==expected['snapshots'][0]['armament'][-1],('initial fuel',initial[0],expected['snapshots'][0]['armament'][-1])
    launch=native/'launch.json'
    if launch.exists():
        import struct
        before_arming=next(event for event in json.loads(launch.read_text())if event['event']=='arming_screen')
        bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
        want={'fuel':bits(before_arming['fuel']),'mass':bits(before_arming['raw_fields']['0x14320']),'capacity':bits(before_arming['raw_fields']['0x14770'])}
        assert initial[0]==want,('pre-arming initialization',initial[0],want)
    for field,prefix in (('mission_progress','CPP_MISSION_PROGRESS '),('player_damage','CPP_PLAYER_DAMAGE '),('automatic_landing','CPP_AUTOMATIC_LANDING '),('cannon','CPP_CANNON '),('radar_pulse','CPP_RADAR_PULSE '),('speed_factor','CPP_SPEED_FACTOR '),('cheat_state','CPP_CHEAT_STATE '),('aiming_flags','CPP_AIMING_FLAGS '),('control_configuration','CPP_CONTROL_CONFIGURATION '),('autopilot_targets','CPP_AUTOPILOT_TARGETS '),('body_basis','CPP_BODY '),('sensors','CPP_SENSORS '),('armament','CPP_ARMAMENT '),('projectiles','CPP_PROJECTILES '),('player_parts','CPP_PLAYER_PARTS '),('launch_notice','CPP_LAUNCH_NOTICE '),('player_models','CPP_PLAYER_MODELS ')):
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
    if 'world_cameras' in expected:
        # Native ejection paints the horizon before installing its world camera.
        # Compare actual horizon inputs and world-entry cameras at their own
        # consumer boundaries, rather than conflating a stale cache with a pose.
        actual_horizons=[item['horizon']for item in cameras]
        wanted_horizons=[item['horizon']for item in expected['horizons']]
        assert actual_horizons==wanted_horizons,('horizon inputs',actual_horizons,wanted_horizons)
        # scene::draw retains world coordinates in doubles; projector() casts
        # their Q16 values to the original signed 32-bit camera cache.
        actual_cameras=[[(coordinate+2**31)%2**32-2**31 for coordinate in row]for row in records('CPP_WORLD_CAMERA ')]
        assert actual_cameras==expected['world_cameras'],('world cameras',[(i,x,y)for i,(x,y)in enumerate(zip(actual_cameras,expected['world_cameras']),1)if x!=y][:4],len(actual_cameras),len(expected['world_cameras']))
    else:
        assert cameras==expected['horizons'][:len(cameras)],('camera/horizon',cameras,expected['horizons'][:len(cameras)])
    actual=(root/'cpp.indices').read_bytes();image=(native/f'frame-{a.frames}.indices').read_bytes()
    assert len(actual)==len(image)==64000
    differences=sum(x!=y for x,y in zip(actual,image))
    if expected.get('recordings'):
        from native_recording import decode_recording
        for recording in expected['recordings']:
            assert recording['closed'],('recording input must stop before the capture ends',recording)
            name=recording['name'].replace('\\','/').rsplit('/',1)[-1]
            path=next((path for path in install.iterdir()if path.name.lower()==name.lower()),None)
            assert path is not None,('C++ recording not written',name)
            got=decode_recording(path.read_bytes());want=decode_recording((native/recording['file']).read_bytes())
            assert len(got)==len(want),('recording frame count',len(got),len(want))
            for index,(observed,original_frame)in enumerate(zip(got,want)):
                for field in original_frame:
                    if observed[field]!=original_frame[field]:
                        mismatches=[(i,x,y)for i,(x,y)in enumerate(zip(observed[field],original_frame[field]))if x!=y]
                        raise AssertionError(('recording frame',index,field,len(observed[field]),len(original_frame[field]),mismatches[:2]))
    if 'projectile_guidance' in expected:
        wanted=[event for event in expected['projectile_guidance']if event['frame']<=a.frames]
        actual=records('CPP_PROJECTILE_GUIDANCE ')
        assert actual==wanted,('projectile guidance inputs',[(i,x,y)for i,(x,y)in enumerate(zip(actual,wanted),1)if x!=y][:3],len(actual),len(wanted))
    if 'cockpit_displays' in expected:
        actual=records('CPP_COCKPIT_DISPLAYS ')
        wanted=[event for event in expected['cockpit_displays']if event['frame']<=a.frames]
        assert actual==wanted,('cockpit display inputs',[(i,x,y)for i,(x,y)in enumerate(zip(actual,wanted),1)if x!=y][:3],len(actual),len(wanted))
    if 'air_brake' in expected['snapshots'][1]:
        actual=records('CPP_AIR_BRAKE ')
        wanted=[snapshot['air_brake']for snapshot in expected['snapshots'][1:a.frames+1]]
        assert actual==wanted,('air-brake fraction/switch',[(i,x,y)for i,(x,y)in enumerate(zip(actual,wanted),1)if x!=y][:3])
    verified=['player','actors','shared RNG','radio','camera','horizon']
    if a.lapc_effects:
        verified.append('LAPC requests')
        if expected.get('sample_requests') is not None:verified.append('sample requests')
    if a.until_result:verified.append('natural result/FINISH campaign values')
    if (native/'radar.json').exists():verified.append('ordered radar inputs')
    if 'projectile_guidance' in expected:verified.append('projectile guidance inputs')
    if 'cockpit_displays' in expected:verified.append('cockpit display inputs')
    if 'autopilot_targets' in expected['snapshots'][1]:verified.append('autopilot targets')
    if 'trail_events' in expected:verified.append('smoke samples')
    if 'hud_alert_events' in expected:verified.append('HUD warning requests')
    if expected.get('recordings'):verified.append('recorded model queues')
    verified += [field for field in ('mission_progress','player_damage','automatic_landing','cannon','radar_pulse','speed_factor','cheat_state','aiming_flags','control_configuration','body_basis','sensors','animation','armament','projectiles','player_parts','launch_notice','player_models') if field in expected['snapshots'][1]]
    rules='career'if a.career_rules else 'Arcade'
    print(f'Mission {a.mission}, {a.flight_model}, {rules} rules, {a.frames} complete frames: {", ".join(verified)} agree. Images: {len(different_frames)}/{a.frames} frames differ; final image {differences}/64000 different indices.')
    if a.strict_pixels:assert not different_frames,('whole-frame pixels',different_frames[:20],differences)
