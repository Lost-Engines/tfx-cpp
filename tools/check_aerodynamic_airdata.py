#!/usr/bin/env python3
"""Compare original air-data prefix 0x98ebc..0x991cc and full atmosphere.

The original normalisation, projections, angle and sqrt helpers and atmosphere
execute under original startup precision. FPATAN uses actual host x87. Wind is
supplied at its cached-state boundary; execution returns at the next coefficient
stage, without running separate coefficient/fuel/failure or warning producers.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);backend=hardware_fpatan(im,a.build);rng=random.Random(0x98ebc)
def finish(image):
    frame=image.cpu.reg_read(r.UC_X86_REG_EBP)
    previous,edx,destination=struct.unpack('<3I',image.cpu.mem_read(frame,12))
    for register,value in ((r.UC_X86_REG_EBP,previous),(r.UC_X86_REG_EDX,edx),(r.UC_X86_REG_ESP,frame+12),(r.UC_X86_REG_EIP,destination)):image.cpu.reg_write(register,value)
im.intercept(0x991cc,'End capture after complete air-data/atmosphere output, before separately owned coefficient/fuel/failure stages',finish)
bits=lambda value:struct.unpack('<Q',struct.pack('<d',value))[0]
float_bits=lambda value:struct.unpack('<I',struct.pack('<f',value))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if index%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18))
    velocity=[rng.choice([-.001,.001,0,5,rng.uniform(-1000,1000)]) for _ in range(3)]
    if index%101==0:velocity=[1e9,1e9,0]
    wind=[rng.uniform(-50,50) if index%3 else 0 for _ in range(3)]
    down=rng.choice([0,-11000,-10000,-20000,rng.uniform(-40000,100)])
    values=[down,rng.uniform(1000,20000),rng.uniform(0,10000),rng.uniform(0,5000),rng.choice([.02,.04,.1]),rng.uniform(0,1e6),rng.uniform(-.5,.5)]
    atmosphere=[1.225,.0065,11000]
    cases.append([index%2,rng.randrange(-20,40),*frame,*map(bits,velocity),*map(float_bits,wind),*map(bits,values),rng.randrange(-32768,32768),*map(bits,atmosphere)])
output=subprocess.check_output([str((a.build/'aerodynamic_airdata_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    realistic,temp=row[:2];frame=row[2:11];velocity=row[11:14];wind=row[14:17];values=row[17:24];heading=row[24];atmosphere=row[25:]
    im.write(0x8e25,'<B',0);im.write(0x8f30,'<B',realistic);im.write(0x1496b,'<B',0);im.write(0x14956,'<h',0);im.write(0x8c98,'<h',temp)
    im.write(0x1493e,'<9h',*frame);im.write(0x14820,'<3Q',*velocity);im.write(0x133fc,'<3I',*wind)
    for offset,value in zip((0x14768,0x14220,0x14858,0x142a0,0x142c0,0x13b60,0x14418),values):im.write(offset,'<Q',value)
    im.write(0x148f8,'<i',heading)
    for offset,value in zip((0x141e8,0x14210,0x14260),atmosphere):im.write(offset,'<Q',value)
    im.call(0x98ebc,limit=1000000)
    expected=[im.read(offset,'<Q')[0] for offset in (0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870)]
    expected += list(im.read(0x147a8,'<3Q'))+list(im.read(0x14708,'<3Q'))
    expected += [im.read(offset,'<Q')[0] for offset in (0x14438,0x14240,0x142b8,0x14790,0x146b8,0x14060,0x14418,0x14700,0x14778,0x143d8,0x14320,0x13b60)]
    expected += [im.read(offset,'<i')[0]&0xffffffff for offset in (0x13444,0x148f8)]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Aerodynamic air data agrees in {len(cases)} original basis, ground/air velocity, angle, atmosphere, speed/Mach, mass, pressure and clock cases; explicit hardware FPATAN and coefficient-stage end boundary')
