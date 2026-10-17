#!/usr/bin/env python3
"""Compare original AWACS bearing/altitude sample concatenation.

A4E80 and its complete numeric builders execute. Only sample append and final
urgent request delivery are observed at their device-independent boundaries.
No original resources or synthesized audio are included in retained fixtures.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');samples=[];submitted=[]
def append(image):samples.append(image.cpu.reg_read(r.UC_X86_REG_EAX));image.return_from()
def submit(image):submitted.append(1);image.return_from()
im.intercept(0xa4cb0,'Observe appended PCM sample slot; numeric construction and ordered concatenation execute.',append)
im.intercept(0xa4c84,'Observe final urgent speech submission; original sample scheduling is independently verified.',submit)
rng=random.Random(0xa4e80);rows=[];expected=[]
edges=(-1,0,1,19,20,21,29,30,31,99,100,101,119,120,129,130,199,200,262,360,3699,30001)
for index in range(4096):
    bearing=(-1,0,1,20,21,99,100,101,359,360,361)[index%11] if index<128 else rng.randrange(-30,391)
    altitude=edges[index%len(edges)] if index<256 else rng.randrange(263)
    rows.append([bearing,altitude]);samples.clear();submitted.clear()
    im.call(0xa4e80,eax=bearing&0xffffffff,edx=altitude&0xffffffff)
    assert bool(samples)==bool(submitted),(index,samples,submitted)
    expected.append([len(samples),*samples])
output=subprocess.check_output([str((a.build/'radar_voice_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
actual=[list(map(int,line.split())) for line in output]
assert actual==expected,next(((i,rows[i],got,want) for i,(got,want) in enumerate(zip(actual,expected)) if got!=want),('length',len(actual),len(expected)))
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row+want)) for i,(row,want) in enumerate(zip(rows,expected)) if i<128 or i%31==0)+'\n')
print(f'{len(rows)} complete original AWACS sample sequences agree: bearing/altitude guards, zero, teens/tens, hundreds, lookup tail and request order')
