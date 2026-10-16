#!/usr/bin/env python3
"""Compare complete original arming widget frames, excluding the 3D preview boundary."""
import argparse
from pathlib import Path
import random
import subprocess
from native_arming import NativeArming

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args()
rng=random.Random(0x8b184);cases=[];expected=[]
for aircraft in range(3):
    for ordinal in range(64):
        selected=ordinal%23 or -1
        first=max(1,min(17,selected-rng.randrange(6))) if selected>=0 else rng.randrange(1,18)
        stores=[-1]*10 if ordinal<23 else [rng.randrange(27) if rng.randrange(3) else -1 for _ in range(10)]
        previous_drag=rng.randrange(100)/10000
        cases.append([aircraft,first,selected,*stores,previous_drag])
requests=''.join(' '.join(map(str,case))+'\n' for case in cases)
actual=subprocess.check_output([str((args.build/'arming_screen_probe').resolve()),str(args.data_dir)],input=requests.encode())
assert len(actual)==len(cases)*64000
native=NativeArming(args.data_dir,args.research)
current_aircraft=None
for index,case in enumerate(cases):
    aircraft,first,selected,*tail=case
    if aircraft!=current_aircraft:
        native.initialise_aircraft(aircraft);current_aircraft=aircraft
    want=native.frame(first,selected,tail[:10],tail[10])
    got=actual[index*64000:(index+1)*64000]
    if got!=want:
        different=[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b]
        from PIL import Image
        Image.frombytes('L',(320,200),got).save('/tmp/tfx-arming-widget-cpp.png')
        Image.frombytes('L',(320,200),want).save('/tmp/tfx-arming-widget-native.png')
        raise AssertionError((case,len(different),different[:30]))
print(f'Arming widgets agree in every pixel of {len(cases)} complete native frames')
