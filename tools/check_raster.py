#!/usr/bin/env python3
"""Compare C++ palette-index drawing modes with captured native VGA pixels."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=Path('build'))
parser.add_argument('--research', type=Path, required=True)
args = parser.parse_args()
fixtures = json.loads((args.research / 'analysis/lighting/raster-modes.json').read_text())['cases']
requests = ''.join(f"{c['mode']} {'shifted' if c['kind']=='shifted quad' else c['kind']} {c['procedural_seed_before'] or 0x4321}\n" for c in fixtures)
output = subprocess.check_output([str((args.build / 'tfx_probe').resolve()),'raster',str((args.research / 'installs/cd_1994_09/TFX').resolve())], input=requests.encode())
at = 0
for case in fixtures:
    seed, = struct.unpack_from('<I',output,at)
    pixels = output[at+4:at+4+64000]
    at += 64004
    if case['procedural_seed_after'] is not None:
        assert seed == case['procedural_seed_after'],(case['mode'],case['kind'],'procedural seed',seed,case['procedural_seed_after'])
    if case['kind']=='circle':
        assert hashlib.sha256(pixels).hexdigest() == case['pixels_sha256'],(case['mode'],'complete native circle')
    interior = bytes(pixels[y*320+x] for y in range(60,100) for x in range(60,100))
    expected = base64.b64decode(case['interior_base64'])
    assert interior == expected,(case['mode'],case['kind'],'interior',sum(a!=b for a,b in zip(interior,expected)))
assert at == len(output)
print(f'Native raster comparison passed: {len(fixtures)} interiors (43,200 pixels), 9 complete circles and 3 procedural seed transitions')

rounded = json.loads((args.research / 'analysis/models/rounded-checks.json').read_text())['cases']
requests = ''.join(' '.join(map(str,[*c['previous'],*c['corner'],*c['next']]))+'\n' for c in rounded)
actual = subprocess.check_output([str((args.build / 'tfx_probe').resolve()),'rounded'],input=requests.encode()).decode().splitlines()
assert len(actual)==len(rounded)
for case,line in zip(rounded,actual):
    assert list(map(int,line.split())) == [v for p in case['native_vertices'] for v in p],case

gradients = json.loads((args.research / 'analysis/lighting/gouraud-checks.json').read_text())['gradients']
requests = ''.join('-1 gradient 17185 '+' '.join(map(str,c['vertex_colours']))+'\n' for c in gradients)
output = subprocess.check_output([str((args.build / 'tfx_probe').resolve()),'raster',str((args.research / 'installs/cd_1994_09/TFX').resolve())], input=requests.encode())
for i,case in enumerate(gradients):
    pixels=output[i*64004+4:(i+1)*64004]
    for j in range(80):
        row=pixels[60*320+20+j]
        column=pixels[(20+j)*320+60]
        if case['reversed_lookup']:row,column=255-row,255-column
        assert row==case['row60_indices'][j],(case['vertex_colours'],'row',j,row,case['row60_indices'][j])
        assert column==case['column60_indices'][j],(case['vertex_colours'],'column',j,column,case['column60_indices'][j])
print(f'Native geometry/shading comparison passed: {len(rounded)} rounded corners and 1,280 Gouraud samples')
