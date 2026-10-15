#!/usr/bin/env python3
"""Compare direct C++ model decoding with the independently checked research VM.

This checks resource interpretation, not native camera projection/rasterisation.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=Path('build'))
parser.add_argument('--research', type=Path, required=True)
args = parser.parse_args()
research = args.research.resolve()
source = (research / 'analysis/models/data.js').read_text()
models = json.loads(source[source.index('=') + 1:].strip().removesuffix(';'))['models']
cases = []
for model in models:
    for level in range(len(model['levels'])):
        cases.append([model['id'], 0, 0, level])
    if any(opcode == 63 for _, opcode, _ in model['instructions']):
        cases.append([model['id'], 128, 0, 0])
    if any(p['index'] == 7 for p in model.get('parameters', [])):
        cases.append([model['id'], 0, 255, 0])
script = r'''
const fs=require('fs'),vm=require('vm');
for(const name of ['analysis/models/data.js','analysis/models/model.js'])vm.runInThisContext(fs.readFileSync(name,'utf8'));
const models=new Map(TFX_DATA.models.map(m=>[m.id,m]));
for(const [id,status,damage,level] of JSON.parse(fs.readFileSync(0,'utf8'))){
 const parameters=Array(256).fill(0);parameters[7]=damage;
 const mesh=TFXModel.inspect(models.get(id),{rules:false,referenceScale:1,status,parameters,level,initialState:0});
 console.log(JSON.stringify([mesh.steps,mesh.primitives.map(p=>[
   {face:0,line:1,point:2}[p.kind],p.colour,p.mode??-1,p.pixelSize||0,p.radius||0,p.sourceOffset,
   (p.vertices||[p.vertex]).map((v,i)=>[...v,p.shades?.[i]??-1,...(p.textured?p.uv?.[i]||[0,0]:[0,0])])
 ])]));
}
'''
expected = subprocess.check_output(['node', '-e', script], cwd=research, input=json.dumps(cases).encode()).splitlines()
requests = ''.join(f'{int(identifier,16)} {status} {damage} {level}\n' for identifier,status,damage,level in cases)
actual = subprocess.check_output([str((args.build / 'tfx_probe').resolve()), 'shape', str(research / 'installs/cd_1994_09/TFX')], input=requests.encode()).splitlines()
assert len(actual) == len(expected) == len(cases)
vertices = 0
for case, a, b in zip(cases, actual, expected):
    a, b = json.loads(a), json.loads(b)
    assert a[0] == b[0], (case, 'step count', a[0], b[0])
    assert len(a[1]) == len(b[1]), (case, 'primitive count', len(a[1]), len(b[1]))
    for ap, bp in zip(a[1], b[1]):
        assert ap[:6] == bp[:6], (case, 'primitive metadata', ap[:6], bp[:6])
        assert len(ap[6]) == len(bp[6])
        for av, bv in zip(ap[6], bp[6]):
            # Ignore unused UV fields on untextured geometry; native page
            # binding is checked separately when the software raster is ready.
            assert all(math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-9) for x,y in zip(av[:4],bv[:4])), (case, 'vertex', av, bv)
            vertices += 1
print(f'Model interpretation comparison passed: {len(models)} models, {len(cases)} detail/state cases, {vertices} vertices')
