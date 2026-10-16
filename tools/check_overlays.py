#!/usr/bin/env python3
"""Compare decoded compiled cockpit artwork with its original VGA pixel writes."""
import argparse
from pathlib import Path
import subprocess
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'));sys.path.insert(0,str(args.research/'tools'))
from did_unpack import Archive
from decode_cockpits import capture
archive=Archive.read(directory/'DID.DAT')
entries={entry.identifier:entry for entry in archive.entries}
cases=[];expected=[]
for name in ('dat/infcock.hud','dat/cockpit.bin','dat/a.bin','dat/misshud.hud','dat/cockmap.bin'):
    raw=archive.unpack(entries[archive.hash_name(name)])
    positions=[(0,0),(-8,0),(8,0),(0,28)]
    if raw.startswith(bytes.fromhex('e800000000')):positions.extend((pan,vertical) for pan in (-79,-60,-20,-1,1,20,60,79) for vertical in (0,28))
    for pan,vertical in positions:
        pixels,coverage,statistics=capture(raw,pan,vertical)
        assert statistics['outside']==0,(name,pan,vertical,statistics)
        cases.append(f'{name} {pan} {vertical}');expected.append(pixels+coverage)
output=subprocess.check_output([str((args.build/'overlay_probe').resolve()),str(directory)],input=('\n'.join(cases)+'\n').encode())
assert len(output)==len(expected)*128000
for index,(case,want) in enumerate(zip(cases,expected)):
    got=output[index*128000:(index+1)*128000]
    assert got==want,(case,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Compiled cockpit artwork agrees in {len(cases)} complete native pixel/coverage frames across five resources and viewport offsets')
