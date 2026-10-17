#!/usr/bin/env python3
"""Check that native rain reaches the real mission frame, beneath its cockpit.

Disposable configuration copies differ only in the precipitation preference.
Each process starts from the same mission and random state without advancing
simulation. Original installation files are never changed.
"""
import argparse
from pathlib import Path
import subprocess
import struct
import tempfile
from PIL import Image

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,required=True)
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--captures',type=Path)
a=p.parse_args();data=a.data_dir.resolve();executable=(a.build/'tfx').resolve()
with tempfile.TemporaryDirectory(prefix='tfx-rain-scene-') as temporary:
 root=Path(temporary)
 for name in ('DID.DAT','TFX.DAT'):(root/name).symlink_to(data/name)
 images={}
 layout=subprocess.check_output([str((a.build/'cockpit_frame_probe').resolve()),str(data),'layouts'],text=True).splitlines()[0].split()
 frame=subprocess.check_output([str((a.build/'cockpit_frame_probe').resolve()),str(data),'frame'],input=b'0 0 28\n')
 offset_y=struct.unpack_from('<i',frame,4)[0];footer=int(layout[1])+offset_y+1;coverage=frame[16+64000:]
 assert len(coverage)==64000
 for environment in ('yugos_dc','yugos_st'):
  for enabled in (0,1):
   (root/'TFX.CFG').write_text(f'SOUNDFX=0\nMUSIC=0\nMODEL=3\nDETAIL=2\nREALISM=0,{enabled},1,1,0,1,0\nLANG=1\n')
   target=root/f'{environment}-{enabled}.ppm'
   subprocess.run([str(executable),'--data-dir',str(root),'--mission','830','--environment',environment,'--flight-model','arcade','--screenshot',str(target)],check=True,capture_output=True,text=True,timeout=20)
   with Image.open(target) as source:images[environment,enabled]=source.convert('RGB').copy()
   if a.captures:
    a.captures.mkdir(parents=True,exist_ok=True);images[environment,enabled].resize((960,720),Image.Resampling.NEAREST).save(a.captures/f'{environment}-{enabled}.png')
 assert images['yugos_dc',0].tobytes()==images['yugos_dc',1].tobytes(),'precipitation preference altered a clear-weather frame'
 before=images['yugos_st',0];after=images['yugos_st',1]
 changed=[(x,y) for y in range(200) for x in range(320) if before.getpixel((x,y))!=after.getpixel((x,y))]
 assert changed,'storm rain painted no visible pixels'
 assert all(y<footer and not coverage[y*320+x] for x,y in changed),('rain leaked into the cockpit instruments',changed)
 assert len({after.getpixel(point) for point in changed})==1,('rain changed something other than its single palette index',changed)
 assert before.crop((0,footer,320,200)).tobytes()==after.crop((0,footer,320,200)).tobytes(),'rain altered the lower cockpit'
 print(f'Real mission rain composition passed: {len(changed)} single-colour storm pixels, clear weather unchanged, cockpit instruments preserved')
