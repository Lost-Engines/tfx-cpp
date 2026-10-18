#!/usr/bin/env python3
"""Compare a custom AGM-109H loadout, automatic lock and F9 in mission 703.

Both executables receive Shift+PLOP, cheat Ctrl+D, and actual arming-screen mouse
input. No inventory, target, flight state or outcome is injected. The original
2.05 scrollbar, weapon row and legal F-117 mount supply these pointer positions.
The optional sound check uses the existing private muted LAPC session transport.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--output',type=Path)
p.add_argument('--rom-dir',type=Path,help='also compare live sample/effect requests without audible host output')
p.add_argument('--airborne',action='store_true',help='also exercise release/guidance, using an explicit test-authored airborne start')
p.add_argument('--native-capture',type=Path,help='reuse a matching original capture')
a=p.parse_args()
clicks=[
    [307,150,1], # Scroll to the final six weapons.
    [256,86,1],  # Select AGM-109H, row 2 of that page.
    [149,160,0], # Settle the dragged-store segment over the legal mount.
    [149,160,1], # Attach its paired stores.
    [149,160,2], # Return from placement to idle.
    [197,199,1], # DONE.
]
rows=[{'frame':1+i*2,'event':key,'held':['right-shift',key]}for i,key in enumerate('plop')]
rows += [
    {'frame':9,'event':'d','held':['control','d'],'arming':clicks},
    {'frame':13,'event':'f9'},
    {'frame':17,'event':'f1'},
    {'frame':19,'event':'space'},
]
with tempfile.TemporaryDirectory(prefix='tfx-cruise-session-')as temporary:
    root=a.output.resolve()if a.output else Path(temporary)
    root.mkdir(parents=True,exist_ok=True)
    tape=root/'inputs.json';tape.write_text(json.dumps(rows,indent=2)+'\n')
    mission=703;mission_options=[]
    if a.airborne:
        from native_planner import NativePlanner
        resources=NativePlanner(a.research/'installs/cd_1994_09/TFX',a.research)
        source=resources.read('missions/miss703.mis')
        assert source.count(b',landed,')==1
        source=source.replace(b',landed,',b',-2000,',1).replace(b'INIT:',b'INIT:\r\n\tspeed 300',1)
        source=b'\r\n'.join(source.splitlines())+b'\r\n'
        fixture=root/'airborne.mis';fixture.write_bytes(source)
        mission=9703;mission_options=['--mission-file',str(fixture)]
    command=[sys.executable,'-B',str(Path(__file__).with_name('check_flight_session.py')),
        '--research',str(a.research.resolve()),'--build',str(a.build.resolve()),
        '--mission',str(mission),'--flight-model','military-spec','--frames','24',
        '--inputs',str(tape),'--strict-pixels','--x87-backend',str(a.build.resolve()),
        '--output',str(root/'session'),*mission_options]
    if a.rom_dir:command+=['--lapc-effects','--rom-dir',str(a.rom_dir.resolve())]
    if a.native_capture:command+=['--native-capture',str(a.native_capture.resolve())]
    subprocess.run(command,check=True)
    session=json.loads(((a.native_capture if a.native_capture else root/'session/native')/'session.json').read_text())
    assert session['arming_events']==[{'frame':9,'clicks':clicks}]
    armed=session['snapshots'][9]['armament']
    assert armed[0]==7 and armed[1]==0 and armed[4:6]==[19,1],('custom cruise loadout',armed)
    assert session['snapshots'][13]['view_mode']==28,'F9 did not enter the ground-target observer'
    if a.rom_dir:
        assert {'frame':9,'priority':2,'ids':[74]}in session['sample_requests'],'the original tracking announcement was not exercised'
    if a.airborne:assert session['projectile_guidance'],'the airborne case did not launch a guided missile'
    else:assert not session['projectile_guidance'],'the runway case unexpectedly launched a missile'
    print('Custom AGM-109H arming, acquisition and F9 agree through 24 complete original/C++ frames, including '+('airborne missile guidance'if a.airborne else'landed fire inhibition'))
