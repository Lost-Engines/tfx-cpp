#!/usr/bin/env python3
"""Compare complete original arming widget frames, excluding the 3D preview boundary."""
import argparse
from pathlib import Path
import random
import subprocess
import struct
from unicorn import x86_const as r
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
        native.initialise_aircraft(aircraft);native.open_screen();current_aircraft=aircraft
    want=native.frame(first,selected,tail[:10],tail[10])
    got=actual[index*64000:(index+1)*64000]
    if got!=want:
        different=[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b]
        from PIL import Image
        Image.frombytes('L',(320,200),got).save('/tmp/tfx-arming-widget-cpp.png')
        Image.frombytes('L',(320,200),want).save('/tmp/tfx-arming-widget-native.png')
        raise AssertionError((case,len(different),different[:30]))
print(f'Arming widgets agree in every pixel of {len(cases)} complete native frames')

# Capture the controller's unavailable panel and loadout-label helper separately.
cases=[(0,0,0,0)]+[(1,weapon,x,y) for weapon in range(27) for x,y in ((30,160),(105,75),(240,40))]
actual=subprocess.check_output([str((args.build/'arming_screen_probe').resolve()),str(args.data_dir),'--panels'],input=''.join(' '.join(map(str,case))+'\n' for case in cases).encode())
assert len(actual)==len(cases)*64000
native.buttons=0
for index,(kind,weapon,x,y) in enumerate(cases):
    native.video.copy(0x59a64,0x55907)
    native.image.call(0xb9238,stack=(0,320,0,200))
    if kind==0:native.image.call(0x89388)
    else:
        pointer=native.image.read(0x809c+weapon*48+4,'<I')[0]
        text=native.text(pointer)
        native.image.call(0x89268,eax=x,edx=y,ebx=len(text)*3,ecx=pointer)
    want=native.video.pixels();got=actual[index*64000:(index+1)*64000]
    assert got==want,((kind,weapon,x,y),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Arming unavailable and store-label panels agree in every pixel of {len(cases)} native frames')

# Compare the assembled screen's palette sequence to complete original ramps.
native.initialise_aircraft(0)
ramps=native.open_screen()
native.palettes.clear();native.image.call(0xca3c0,eax=native.image.data+0x20ce0,limit=2000000)
source=native.read('iff/raw/armscr2.lbm')[4:772]
assert native.palettes==[bytes(value*level//40 for value in source) for level in range(40,0,-1)]
ramps.extend(native.palettes);ramps.append(bytes(768))
expected=b''.join(bytes((value*255+31)//63 for value in palette) for palette in ramps)
actual=subprocess.check_output([str((args.build/'arming_preview_probe').resolve()),str(args.data_dir),'fades'])
assert actual==expected,'assembled arming fade phases differ from original DAC ramps'
print(f'Assembled arming palettes agree with {len(ramps)} complete original ramp/final-black frames')
