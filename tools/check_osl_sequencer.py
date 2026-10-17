#!/usr/bin/env python3
"""Compare complete native OSL/LA playback ticks, shared state and every MIDI byte.

Both original sequencer and device driver run. Only MPU/OPL ready reads,
physical port writes, interrupt routing and post-SysEx settling are external.
No song row/effect, voice, control-flow or MIDI handler is replaced.
"""
import argparse
import json
from pathlib import Path
import subprocess
from native_osl import NativeOSL


def checksum(data):
    value=14695981039346656037
    for byte in data:value=((value^byte)*1099511628211)&0xffffffffffffffff
    return value

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--name',help='limit to one resource name/identifier')
p.add_argument('--volume',type=int,default=75)
a=p.parse_args();launcher=a.research/'installs/cd_1994_09/TFX/START.EXE'
entries=[entry for entry in json.loads((a.research/'analysis/audio/music-renders.json').read_text()) if entry['mode']=='rld' and (not a.name or a.name in (entry['name'],entry['id']))]
assert entries,'no matching OSL resources'
ticks=byte_count=0
for entry in entries:
    path=a.research/'extracted/cd_1994_09/resources'/entry['source']
    probe=[str((a.build/'osl_sequencer_probe').resolve()),str(launcher),str(path),str(a.volume)]
    output=subprocess.check_output(probe).decode().splitlines()
    native=NativeOSL(launcher.read_bytes())
    native.initialise();assert native.load(path.read_bytes())==(0,False)
    assert native.play(a.volume)==(0,False)
    for index,line in enumerate(output):
        if index:native.events.clear();native.tick();ticks+=1
        expected=native.state()+[checksum(native.channels()),len(native.events),checksum(native.events)]
        actual=list(map(int,line.split()))
        if actual!=expected:
            detail=subprocess.run(probe+[str(max(1,index)),'dump'],capture_output=True,text=True)
            dumped=detail.stderr.splitlines()
            if dumped and len(dumped[0].split())==672:
                cpp=list(map(int,dumped[0].split()));original=list(native.channels())
                print('channel differences',[(at//21,at%21,x,y) for at,(x,y) in enumerate(zip(cpp,original)) if x!=y][:30],flush=True)
            if len(dumped)>1:
                cpp_events=list(map(int,dumped[1].split()))
                print('event differences',[(at,x,y) for at,(x,y) in enumerate(zip(cpp_events,native.events)) if x!=y][:30],flush=True)
            raise AssertionError((entry['name'],index-1,actual,expected,dumped[1][:600] if len(dumped)>1 else detail.stderr[-600:]))
        byte_count+=len(native.events)
    print(entry['name'],len(output)-1,'ticks agree',flush=True)
print(f'{len(entries)} OSL LA resources, {ticks} complete original ticks and {byte_count} MIDI bytes agree at native volume {a.volume}, including all 32 shared channel records')
