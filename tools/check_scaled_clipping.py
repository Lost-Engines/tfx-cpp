#!/usr/bin/env python3
"""Check that authored camera-unit changes preserve clipped polygon/line/point output.

Native integer projection is checked separately by check_orbit_camera.py.
This property check covers scale propagation through the software clipper.
"""
import argparse
from pathlib import Path
import random
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();rng=random.Random(0xbc3e8);cases=[]
for depth in [15,16,17,32,64]:
    cases += [(2,[(0,0,depth*65536)]),(1,[(-8*65536,0,depth*65536),(8*65536,0,64*65536)]),(0,[(-8*65536,-6*65536,depth*65536),(8*65536,-6*65536,64*65536),(0,6*65536,32*65536)])]
for _ in range(128):
    cases.append((0,[(rng.randrange(-20*65536,20*65536),rng.randrange(-10*65536,10*65536),rng.randrange(10*65536,80*65536)) for _ in range(3)]))
scales=[1,.5,.25,.125,.025,.005,.0025,1/7,1/23];rows=[]
for kind,points in cases:
    for scale in scales:rows.append([kind,len(points),scale,*[n for point in points for n in point]])
output=subprocess.check_output([str((a.build/'scaled_projection_probe').resolve()),str(a.data_dir)],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
for index,case in enumerate(cases):
    block=output[index*len(scales):(index+1)*len(scales)]
    assert all(frame==block[0] for frame in block),(index,case,block)
    if index in (0,3):assert int(block[0].split()[1])==0,(index,block)
    if index==6:assert int(block[0].split()[1])==1,(index,block)
print(f'Scaled near clipping preserves complete polygon/line/point output in {len(rows)} camera-unit cases')
