#!/usr/bin/env python3
"""Compare the complete native moving-ground phase counter, including high-word state."""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0xcac04);rows=[];expected=[];fixture=[]
for case in range(8192):
 initial=rng.choice((-2147483648,-65536,-32768,-2751,-1,0,1,1374,1375,1376,2750,32767,65536,2147483647)) if case<1024 else rng.randrange(-2147483648,2147483648)
 movement=rng.choice((-32768,-8192,-1376,-1,0,1,4,1375,8192,32767)) if case<1024 else rng.randrange(-32768,32768)
 rows.append([initial,movement]);im.write(0xad7c,'<i',initial);im.call(0xcac04,eax=movement&0xffffffff);value=im.read(0xad7c,'<i')[0];expected.append(value)
 if case<128 or case%67==0:fixture.append([initial,movement,value])
output=subprocess.check_output([str((a.build/'horizon_phase_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(output)==len(rows)
for case,(line,value) in enumerate(zip(output,expected)):assert int(line)==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
print('8192 complete original ground-phase updates agree: signed movement shift, retained high-word period test, single correction, low-word comparisons and preservation of the adjacent period mode')
