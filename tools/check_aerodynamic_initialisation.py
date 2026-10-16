#!/usr/bin/env python3
"""Compare fresh assembled flight state with complete native 0x95f3c.

Original startup, presets, geometry, wind/random initialization, store effects,
physical conversion and calibration all execute. Hardware FPATAN/FSIN/FCOS/FPTAN
are the only intercepted numerical dependencies. Declared scene/cockpit inputs
supply orientation, pose, gear state, stores and damage-system conditions.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent
from aerodynamic_snapshot import fields,tail,snapshot
from aerodynamic_reference import initialise_reference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,4096);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x95f3c)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095
baseline=bytes(im.cpu.mem_read(im.data,data_size))
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for i in range(768):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if i%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18))
    position=[rng.uniform(0,60000),rng.choice([-800,-10,5]),rng.uniform(0,60000)]
    cases.append([1+i%3,(i//3)%2,(i//6)%2,(i//12)%2,(i//24)%2,(i//48)%2,(i//96)%2,rng.choice([1,2]),rng.randrange(10),rng.randrange(27),(i//192)%2,rng.randrange(65536),rng.randrange(65536),rng.choice([-20,-11,-10,0,100]),rng.choice([0,100,400,1000]),*map(fbits,position),*frame,i%2,rng.randrange(-20,51)])
output=subprocess.check_output([str((a.build/'aerodynamic_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for index,(row,line) in enumerate(zip(cases,output)):
    initialise_reference(im,row,baseline)
    expected=snapshot(im);actual=list(map(int,line.split()))
    assert actual==expected,(index,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if i>=260 else 'random',x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
print(f'{len(cases)} fresh assembled aerodynamic initializations agree across all 282 owned snapshot fields and ordered random states; full original initializer executes')
