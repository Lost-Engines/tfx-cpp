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
from aerodynamic_snapshot import fields,snapshot

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
    craft,model,landed,cold,terrain,boost,terrain_boost,gear,slot,weapon,occupied,low,high,height,speed=row[:15];position=row[15:18];frame=row[18:27];temperature,celsius=row[27:]
    im.cpu.mem_write(im.data,baseline)
    for field,value,fmt in ((0x11b2a,craft-1,'<H'),(0x1347a,6 if model else 1,'<B'),(0x8d3a,landed,'<H'),(0x1347c,cold,'<B'),(0xabea,terrain,'<B'),(0xe774,128 if boost else 0,'<B'),(0xe762,terrain_boost,'<H'),(0xabf2,height,'<h'),(0x13444,speed,'<i')):im.write(field,fmt,value)
    im.write(0x8f30,'<B',temperature);im.write(0x14956,'<H',0);im.write(0x8c98,'<h',celsius)
    im.write(0x1345e,'<9h',*frame)
    for field,value in zip((0x1341c,0x13428,0x13434),position):im.write(field,'<I',value)
    im.cpu.mem_write(0x300000,struct.pack('<9h',*frame));heading=im.call(0xcd5a8,eax=0x300000)&65535;im.write(0x86ca,'<H',heading)
    for i in range(12):im.write(0x7d70+i,'<B',gear if i==10 else 2)
    im.cpu.mem_write(im.data+0x13374,bytes(20));im.write(0x13374+slot*2,'<2B',weapon,occupied)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
    im.call(0x95f3c,limit=2000000)
    expected=snapshot(im);actual=list(map(int,line.split()))
    assert actual==expected,(index,[(i,hex(fields[i][0]) if i<len(fields) else 'random',x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
print(f'{len(cases)} fresh assembled aerodynamic initializations agree across all 260 owned snapshot fields and ordered random states; full original initializer executes')
