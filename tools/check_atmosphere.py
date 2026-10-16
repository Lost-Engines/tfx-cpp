#!/usr/bin/env python3
"""Compare complete original altitude/temperature/density/sound stage 0x992fc.

The native x87 arithmetic and Watcom square-root helper execute without
interception. Surface temperatures, profile coefficients and retained altitude
are declared inputs; this does not yet drive a live Realistic flight session.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x992fc)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
climate=list(im.read(0x8c98,'<20h'));cases=[]
for index in range(8192):
    height=rng.choice([0,10,20,25,40,rng.uniform(-.5,45)])
    down=rng.choice([0,-11000,-11000.000000001,-10999.999999999,-height*1000,rng.uniform(-40000,100)])
    cases.append([index%2,rng.choice(climate),*map(bits,[height,down,rng.choice([1.225,rng.uniform(.8,1.5)]),rng.choice([.0065,rng.uniform(.003,.009)]),rng.choice([11000,rng.uniform(8000,16000)])])])
output=subprocess.check_output([str((a.build/'atmosphere_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    realistic,temp,height,down,density,lapse,limit=row
    im.write(0x8f30,'<B',realistic);im.write(0x1496b,'<B',0);im.write(0x14956,'<h',0);im.write(0x8c98,'<h',temp)
    for offset,value in zip((0x14060,0x14768,0x141e8,0x14210,0x14260),(height,down,density,lapse,limit)):im.write(offset,'<Q',value)
    im.call(0x992fc)
    expected=[im.read(offset,'<Q')[0] for offset in (0x14438,0x14240,0x142b8,0x14790)]
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Atmosphere agrees in {len(cases)} complete original density, temperature and sound-speed float-bit cases without intercepted dependencies')
