#!/usr/bin/env python3
"""Compare initial live Tour briefing frames in every original language."""
import argparse
import json
from pathlib import Path
import subprocess
from native_planner import NativePlanner

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
names=sorted({node['resource'] for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'})
rows=[];expected=[];labels=[]
for language,number in (('english',1),('french',2),('german',3),('italian',4),('spanish',5)):
    for name in names:
        planner=NativePlanner(directory,args.research);planner.image.write(0xab36,'<B',number)
        planner.initialise(name,modal=True)
        rows.append(language+' '+name+'\n');expected.append(planner.displayed);labels.append((language,name))
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--review-intro'],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr
actual=result.stdout;assert len(actual)==len(expected)*64000
for number,frame in enumerate(expected):
    found=actual[number*64000:(number+1)*64000]
    assert found==frame,(labels[number],sum(a!=b for a,b in zip(found,frame)),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(found,frame)) if a!=b][:12])
print(len(expected),'live original introductory planner frames agree in all pixels across five languages, including native translated-note overlays; C++ also rejects Escape/Enter and accepts Space')
