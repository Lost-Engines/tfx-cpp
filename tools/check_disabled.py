#!/usr/bin/env python3
"""Compare the disabled/ejected player callback after 64 ordinary flight frames."""
import argparse
from pathlib import Path
import random
import subprocess
import check_arcade

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--save-fixture',type=Path)
args=parser.parse_args();check_arcade.DATA=args.data_dir;rng=random.Random(0x8e5a8)
rows=[];expected=[];fixture=[];origins=[]
for aircraft in range(1,4):
    for altitude in (-1,-800,-6000):
        controls=[(rng.choice((1,2,4,10,18)),rng.randrange(-8,9),rng.randrange(-8,9),i%4,int(i<80),int(120<=i<180)) for i in range(512)]
        position=(293888,altitude,236544);angles=(0,32767,0);speed=.65
        header=' '.join(map(str,[aircraft,len(controls),*position,*angles,speed]))
        case_rows=[header,*[' '.join(map(str,row)) for row in controls]];rows.extend(case_rows)
        native=check_arcade.capture(aircraft,position,angles,speed,controls,disabled=True);expected.extend(native);origins.extend([(aircraft,altitude,frame) for frame in range(len(native))])
        digest=14695981039346656037
        for byte in ''.join(' '.join(map(str,row))+'\n' for row in native).encode():digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixture.extend([*case_rows,str(digest)])
output=subprocess.run([str(args.build/'arcade_probe'),'--disabled'],input='\n'.join(rows)+'\n',text=True,capture_output=True,check=True)
actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
for origin,a,b in zip(origins,actual,expected):
    differences=[(name,x,y) for name,x,y in zip(check_arcade.NAMES,a,b) if x!=y]
    assert not differences,(origin,differences)
if args.save_fixture:
    args.save_fixture.write_text('\n'.join(fixture)+'\n');subprocess.run([str(args.build/'arcade_probe'),'--check-disabled',str(args.save_fixture)],check=True)
print(len(expected),'native disabled/ejected player flight steps agree')
