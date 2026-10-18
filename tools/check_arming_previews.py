#!/usr/bin/env python3
"""Compare complete original 3D arming frames, miniature cursors and loading logo.

The original model/SSD loaders, camera setters, animation, shape interpreter,
polygon painter, palette lookups and widgets execute unchanged. DOS files,
allocation, silent external devices and VGA page transport are supplied by the
isolated harness; no installation is written or user display opened.
"""
import argparse
from pathlib import Path
import subprocess
from native_arming import NativeArming

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--output',type=Path,help='save the F-117 reference/C++ opening screenshots')
args=parser.parse_args()
# Thirty-two idle draws cover a full miniature revolution, including byte wrap,
# and advance the native store thumbnails and weapon-bay animation every draw.
positions=[(100,75),(160,100),(10,10),(315,195)]*8
count=0
for aircraft in range(3):
    request=str(aircraft)+'\n'+''.join(f'{x} {y} 0 0 0\n' for x,y in positions)
    actual=subprocess.check_output([str((args.build/'arming_preview_probe').resolve()),str(args.data_dir),'sequence'],input=request.encode())
    assert len(actual)==(len(positions)+1)*64000
    native=NativeArming(args.data_dir,args.research,previews=True)
    native.initialise_aircraft(aircraft);native.open_screen()
    for frame in range(len(positions)+1):
        if frame:
            native.position=positions[frame-1]
            native.frame(1,-1,[-1]*10)
        want=native.displayed;got=actual[frame*64000:(frame+1)*64000]
        if args.output and aircraft==1 and frame==0:
            from PIL import Image
            args.output.mkdir(parents=True,exist_ok=True)
            palette=bytes((value*255+31)//63 for value in native.read('iff/raw/armscr2.lbm')[4:772])
            for label,pixels in (('cpp',got),('native',want)):
                image=Image.frombytes('P',(320,200),pixels);image.putpalette(palette)
                image.convert('RGB').resize((1280,800),Image.Resampling.NEAREST).save(args.output/f'arming-{label}.png')
        assert got==want,(aircraft,frame,sum(a!=b for a,b in zip(got,want)),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:12])
        count+=1
    print(f'Aircraft {aircraft}: all {len(positions)+1} complete native 3D arming frames agree in every indexed pixel',flush=True)

# Execute the real post-arming logo routine, rather than assuming it shares
# the startup presentation or that --skip-intro should suppress it.
native.palettes.clear();native.image.call(0x7d594,limit=20000000)
raw=native.read('iff/raw/tfxstat.lbm')
assert native.palettes==[bytes(value*level//40 for value in raw[4:772]) for level in range(1,41)]
assert bytes(native.video.pixels())==raw[772:],'post-arming logo differs from its original bitmap'
print(f'{count} complete original/C++ 3D arming frames passed; original pre-flight TFX logo resource and all 40 fade stages confirmed')
