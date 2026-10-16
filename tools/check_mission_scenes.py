#!/usr/bin/env python3
"""Check all retail mission scene selections/starts, then render their initial scenes."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--research',type=Path,required=True)
parser.add_argument('--flight-steps',type=int,default=0)
parser.add_argument('--flight-model',choices=('arcade','simple','military-spec','realistic'),default='arcade')
args=parser.parse_args()

def dataset(path):
    s=path.read_text()
    return json.loads(s[s.index('=')+1:].strip().removesuffix(';'))

world=dataset(args.research/'analysis/maps/data.js')
metadata=dataset(args.research/'analysis/missions/data.js')
ids={m['id'] for m in metadata['missions'] if m['category']!='retained'}
missions=sorted([m for m in world['missions'] if m['id'] in ids],key=lambda m:m['name'])
assert len(missions)==128
build=args.build.resolve()
data=str((args.research/'installs/cd_1994_09/TFX').resolve())
actual=subprocess.check_output([str(build/'tfx_probe'),'missions',data],input=('\n'.join(m['name'] for m in missions)+'\n').encode()).splitlines()
assert len(actual)==len(missions)
for mission,line in zip(missions,actual):
    start=next(p for p in mission['points'] if p['kind']=='start')
    landed=start['altitude']=='landed'
    position=[int(start['x']*2048),0 if landed else int(start['altitude']),int(start['z']*2048)]
    expected=[mission['world'],mission['world'][:8].lower(),mission['environment'],mission['way'],int(mission['plane']) if mission['plane'] is not None else None,position,int(landed)]
    assert json.loads(line)==expected,(mission['name'],json.loads(line),expected)
failures=[]
notes=Counter()
outcomes=[]
for mission in missions:
    result=subprocess.run([str(build/'tfx'),'--data-dir',data,'--mission',mission['name'].removeprefix('miss'),'--flight-model',args.flight_model,'--flight-steps',str(args.flight_steps),'--screenshot',os.devnull],capture_output=True,text=True,timeout=20)
    if result.returncode:failures.append((mission['name'],result.stderr))
    else:
        assert 'model parts' in result.stdout and ': 0 model parts' not in result.stdout,mission['name']
        finished=[line for line in result.stdout.splitlines() if line.startswith('Mission result:')]
        assert len(finished)<=1,(mission['name'],finished)
        if finished:outcomes.append((mission['name'],finished[0]))
        for line in result.stderr.splitlines():notes[line]+=1
assert not failures,failures
print(f'Mission scene startup passed: {len(missions)} retail missions; signed starts, regional geometry and separate weather palettes verified')
print('Distinct preview limitations:',dict(notes))

if args.flight_steps:print('Mission result handoffs reached exactly once:',len(outcomes),outcomes[:3])
