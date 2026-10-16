#!/usr/bin/env python3
"""Compare complete planner map pages against native resource loading/composition."""
import argparse
import json
from pathlib import Path
import subprocess
from native_planner import NativePlanner

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args()
directory=args.research/'installs/cd_1994_09/TFX'
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
names=sorted({node['resource'] for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'})
rows=[];expected=[]
for name in names:
    planner=NativePlanner(directory,args.research)
    planner.initialise(name)
    rows.append(str(planner.archive.hash_name('waytxt/'+name+'.way'))+'\n')
    expected.extend(planner.map(layer) for layer in range(3))
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--maps'],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr
actual=result.stdout;assert len(actual)==len(expected)*64768,(len(actual),len(expected))
for number,frame in enumerate(expected):
    found=actual[number*64768:(number+1)*64768]
    assert found==frame,(names[number//3],number%3,next((i,a,b) for i,(a,b) in enumerate(zip(found,frame)) if a!=b))
print(len(expected),'complete native planner pages agree in all pixels and DAC entries across every retail mission and all three map views')
