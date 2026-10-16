#!/usr/bin/env python3
"""Compare decoded aircraft dynamics with original full preset initialization.

The complete original 0x95f3c initializer executes in a fresh image per aircraft,
with original startup, empty stores and declared airborne pose. Hardware FPTAN
replaces Unicorn's narrowing; no other dependencies are intercepted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_tangent

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();data=a.research/'installs/cd_1994_09/TFX/TFX.DAT';rng=random.Random(0x96688)
geometry=[0x147a0,0x14218,0x14200,0x141e0,0x14088,0x14148,0x14228,0x14140,0x14080,0x14248,0x13fc8,0x14150,0x14430,0x14068,0x141b0,0x140d0,0x141b8,0x140e0,0x140f8,0x14108,0x14098,0x8cd0]
coefficients=[0x146a0,0x14630,0x14640,0x14608,0x147a0,0x8d00,0x141a8,0x141a0,0x14190,0x14198,0x14178,0x14180,0x14168,0x140b0]
other=[0x140a8,0x14078,0x14128,0x140c0,0x14070,0x14120,0x14118,0x8d28,0x8d30,0x14220,0x14488,0x14500,0x8d20,0x14540,0x14548,0x14698]
actual=subprocess.check_output([str((a.build/'aerodynamic_airframe_probe').resolve()),str(data)],text=True).splitlines();assert len(actual)==3
inputs=[];expected=[];fixtures=[]
calibration_fields=[0x141a8,0x14198,0x14178,0x14148,0x14088,0x14228,0x14140,0x14080,0x8cd0,0x14258]
for craft in range(3):
    im=NativeReference(data);im.call(0xde851);backend=hardware_tangent(im,a.build)
    im.write(0x11b2a,'<H',craft);im.write(0x1345e,'<9h',32767,0,0,0,32767,0,0,0,32767);im.write(0x13444,'<i',400);im.write(0x1347a,'<B',1);im.write(0x13428,'<f',-800)
    im.call(0x95f3c,limit=2000000)
    wanted=[im.read(offset,'<Q')[0] for offset in (0x142c8,0x14258,0x14850)]
    wanted += [im.read(base+slot*8,'<Q')[0] for slot in range(10) for base in (0x13bd0,0x13c20,0x13c70)]
    wanted += [im.read(offset,'<Q')[0] for offset in geometry+coefficients+other]+[im.read(0x8cd8+craft,'<B')[0]]
    observed=list(map(int,actual[craft].split()));assert observed==wanted,(craft,[(i,x,y) for i,(x,y) in enumerate(zip(observed,wanted)) if x!=y],len(observed),len(wanted))
    for case in range(128):
        previous=0 if case==0 else rng.uniform(-.1,.1)
        im.write(0x14238,'<d',previous);im.call(0x95f3c,limit=2000000)
        row=[im.read(offset,'<Q')[0] for offset in calibration_fields]+[struct.unpack('<Q',struct.pack('<d',previous))[0]]
        inputs.append(row);expected.append([im.read(offset,'<Q')[0] for offset in (0x141a0,0x14190)])
output=subprocess.check_output([str((a.build/'aerodynamic_airframe_probe').resolve()),'--calibration'],input=('\n'.join(' '.join(map(str,row)) for row in inputs)+'\n').encode()).decode().splitlines();assert len(output)==len(inputs)
for index,(row,line,wanted) in enumerate(zip(inputs,output,expected)):
    observed=list(map(int,line.split()));assert observed==wanted,(index,observed,wanted)
    if index%7==0:fixtures.append(' '.join(map(str,row+wanted)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'All three complete decoded aerodynamic aircraft profiles and {len(inputs)} full-initializer pitch calibrations agree; explicit hardware FPTAN')
