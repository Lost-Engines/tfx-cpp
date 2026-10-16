#!/usr/bin/env python3
"""Compare original wind initialization and the complete 0x996c0 update.

Full 0x95f3c initialization executes for 512 wind cases; its weather selector is
supplied immediately before the wind initialization block (the retail entry
ordinarily starts at profile zero). Another 8192 full wind updates run. The
original random generator runs; only FPATAN/FSIN/FCOS/FPTAN use hardware adapters.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x996c0)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
fields=[0x13b60,0x14288,0x13ba0,0x8e28,0x8e30,0x13b58,0x13b50,0x13bc8,0x13cc0,0x13b80,0x13cd0,0x13b70,0x13b48,0x13b30,0x13b38,0x8e38,0x13b90,0x13bc0,0x13b98]
tables=[0x8e40,0x8e68,0x8e90,0x8eb8,0x8ee0,0x8f08]
parameters=[[im.read(field+i*8,'<Q')[0] for field in tables] for i in range(5)]
probe=str((a.build/'aerodynamic_wind_probe').resolve())
decoded=subprocess.check_output([probe,'--parameters',str(path)],text=True).splitlines();assert [list(map(int,line.split())) for line in decoded]==parameters
selected_weather=[0]
im.intercept(0x96418,'Supply selected weather as an input immediately before original wind initialization; no instructions are replaced',lambda image:image.write(0x1496b,'<B',selected_weather[0]))
cases=[]
for i in range(8704):
    op=int(i>=512);weather=i%5
    state=[rng.uniform(0,500),rng.uniform(-20,100),rng.uniform(0,100),rng.uniform(-10,10),rng.uniform(-1,1),rng.uniform(60,240),rng.uniform(0,.1),rng.uniform(0,1),rng.uniform(0,10),rng.uniform(0,2),rng.uniform(0,1),rng.uniform(0,10),rng.choice([0,rng.uniform(0,.5)]),rng.uniform(-150,150),rng.uniform(-150,150),rng.uniform(0,1),rng.uniform(0,1),rng.uniform(0,1),rng.uniform(0,1)]
    down=rng.choice([-6000,-6000.00001,-10000,-10000.00001,-9000,0])
    cases.append([op,weather,(i//5)%2,(i//10)%2,rng.randrange(65536),rng.randrange(65536),*map(bits,state),*map(fbits,[rng.uniform(-100,100) for _ in range(3)]),*parameters[weather],bits(down)])
output=subprocess.check_output([probe],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];renewals=0
for index,(row,line) in enumerate(zip(cases,output)):
    op,weather,terrain,boost,low,high=row[:6];state=row[6:25];wind=row[25:28];down=row[34]
    for field,value in zip(fields,state):im.write(field,'<Q',value)
    im.write(0x133fc,'<3I',*wind);im.write(0x14768,'<Q',down);im.write(0xe762,'<H',terrain);im.write(0xe774,'<B',128 if boost else 0);im.write(0x1496b,'<B',weather)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
    if op:im.call(0x996c0)
    else:
        selected_weather[0]=weather
        im.write(0x11b2a,'<H',index%3);im.write(0x1345e,'<9h',32767,0,0,0,32767,0,0,0,32767);im.write(0x13428,'<f',-800);im.write(0x13444,'<i',400);im.write(0x1347a,'<B',1);im.write(0x8d3a,'<H',0);im.write(0x1347c,'<B',0);im.cpu.mem_write(im.data+0x13374,bytes(20))
        im.call(0x95f3c,limit=2000000)
    expected=[im.read(field,'<Q')[0] for field in fields]+list(im.read(0x133fc,'<3I'))+list(struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4)))
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    renewals+=op and expected[0]==0
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert renewals>1000
print(f'Wind agrees in 512 original initializations and 8192 complete updates, including {renewals} gust renewals; all five parameter profiles and ordered random states agree')
