#!/usr/bin/env python3
"""Compare original scenery initialisers, attachments and terrain placement data."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=Path('build'))
parser.add_argument('--research', type=Path, required=True)
parser.add_argument('--terrain-only', action='store_true', help='compare terrain selection without the older static SSD declaration summary')
args = parser.parse_args()
source = (args.research / 'analysis/maps/data.js').read_text()
world = json.loads(source[source.index('=') + 1:].strip().removesuffix(';'))
probe = str((args.build / 'tfx_probe').resolve())
data_dir = str((args.research / 'installs/cd_1994_09/TFX').resolve())
objects = [] if args.terrain_only else list(world['objects'].items())
requests = ''.join(str(int(identifier,16))+'\n' for identifier,_ in objects)
actual = subprocess.check_output([probe, 'definitions', data_dir], input=requests.encode()).splitlines()
assert len(actual) == len(objects)
for (identifier, definition), line in zip(objects, actual):
    result = json.loads(line)
    expected_parts = [[p['slot'],p['name'],*(v&65535 for v in p['rotation'])] for p in definition['parts']]
    expected_draws = [[d['slot'],*definition['anchors'][d['anchor']]] if d['anchor'] is not None else [d['slot'],0,0,0] for d in definition['draw_parts']]
    expected_streams = [[s['part'],s['parameter'],s['words']] for s in definition['parameter_streams']]
    expected = [definition['flags'],expected_parts,expected_draws,expected_streams]
    assert result == expected,(identifier,definition['names'],result,expected)
# Authoring-only grids lack a playable environment config. Two grids also
# contain out-of-table cell IDs; the C++ loader diagnoses those explicitly.
environments = [e for e in world['environments'] if e['config'] and not e['undefined_tile_indices'] and e['name']!='columbia']
expected_variants = r'''
const fs=require('fs'),vm=require('vm');
for(const name of ['analysis/models/data.js','analysis/models/model.js','analysis/maps/data.js','analysis/maps/world.js'])vm.runInThisContext(fs.readFileSync(name,'utf8'));
for(const name of JSON.parse(fs.readFileSync(0,'utf8'))){
 const e=TFX_WORLD.environments.find(e=>e.name===name),cells=[];
 for(let z=0;z<200;z++)for(let x=0;x<200;x++)cells.push([e.cells[z*200+x],TFXScenery.variant(e,x,z)]);
 console.log(JSON.stringify(cells));
}
'''
names = [e['name'] for e in environments]
selections=[(name,name) for name in names]
for name,lighting in [('yugoslav','yugos_n'),('columbia','colum_d'),('somalia','somal_st'),('libya','libya_tw'),('seaworld','seaclear')]:
    environments.append(next(e for e in world['environments'] if e['name']==name))
    names.append(name)
    selections.append((name,lighting))
expected = subprocess.check_output(['node','-e',expected_variants], cwd=args.research, input=json.dumps(names).encode()).splitlines()
actual = subprocess.check_output([probe, 'environment', data_dir], input=('\n'.join(name+' '+lighting for name,lighting in selections)+'\n').encode()).splitlines()
assert len(actual) == len(expected) == len(names)
for environment, selection, line, cells in zip(environments, selections, actual, expected):
    lighting=next(e for e in world['environments'] if e['name']==selection[1])
    status, palette, actual_cells = json.loads(line)
    assert status == (128 if 'night' in lighting['config'].split() else 0),environment['name']
    assert actual_cells == json.loads(cells),environment['name']
print(f'Terrain metadata comparison passed: {len(names)*40000} cells and variant choices across {len(names)} grid/lighting combinations' if args.terrain_only else f'World comparison passed: {len(objects)} definitions, {len(names)*40000} terrain cells and variant choices across {len(names)} grid/lighting combinations')
