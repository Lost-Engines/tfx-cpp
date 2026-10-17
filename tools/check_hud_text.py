#!/usr/bin/env python3
"""Compare original upper-HUD flight readouts and brake/chute/cable messages."""
import argparse
import math
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--aerodynamic',action='store_true',help='check native angle-of-attack and climb-rate indicators')
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.call(0xde547)
rng=random.Random(0x7f8e0);cases=[]
mach_edges=[0,-.0049,-.005,-.0051,.005,.015,.025,.035,.045,.055,.065,.075,.085,.095,.105,.995,1.005,1.015,1.025,2.675,2.685]
mach_edges=[value for edge in mach_edges for value in (edge,math.nextafter(edge,0),math.nextafter(edge,math.inf),-edge)]
for index in range(768):
    height=[0,.0625,.06125,-.5,-12.5,-999.99,-1000,-10000][index%8] if index<64 else -rng.random()*20000
    speed=rng.randrange(-1000,2000);mach=mach_edges[index%len(mach_edges)] if index<336 else rng.uniform(0,4);load=[0,.05,1.05,9.95,-2.55][index%5]
    throttle=[0,.6,.85,1,1.2][index%5]
    position=[rng.randrange(-500000,500000),0,rng.randrange(-500000,500000)]
    dx,dy=[(0,0),(1,0),(0,28),(-100,0),(100,0),(0,-30),(0,-54),(0,-80),(0,115),(0,170)][index%10]
    cases.append([height,speed,mach,load,throttle,*position,index%2,(index//2)%2,(index//4)%2,dx,dy])
if args.aerodynamic:
    cases=[]
    for index in range(768):
        alpha=rng.uniform(-2,2) if index>=128 else (60-(index%100))*3.14159/180
        if index%4==0:alpha=math.nextafter(alpha,math.inf)
        down=rng.uniform(-200,200) if index>=128 else (index%55-27)/3.281
        if index%5==0:down=math.nextafter(down,-math.inf)
        dx,dy=[(0,0),(1,0),(0,28),(-100,0),(100,0),(0,-30),(0,-54),(0,-80),(0,115),(0,170)][index%10]
        # Native endpoint pixels have no vertical clipping. Exclude the
        # undefined out-of-frame writes; line/mask clipping remains exercised.
        if 92+dx<0 or 6+dy<0 or 46+dy>=200:continue
        row=math.trunc(60-(180/3.14159)*alpha)+dy
        climb_row=26-math.trunc(-down*3.281)+dy
        if not 0<=row<200:continue
        if 6+dy<=climb_row<=46+dy and not 0<=climb_row<200:continue
        cases.append([alpha,down,dx,dy])
command=[str((args.build/'hud_text_probe').resolve()),str(directory)]+(['--aerodynamic'] if args.aerodynamic else [])
output=subprocess.check_output(command,input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
stride=128000;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    if args.aerodynamic:
        alpha,down,dx,dy=row
        im.write(0x14418,'<d',alpha);im.write(0x14830,'<d',down)
        im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
        video.reset()
        for plane in video.planes:plane[:]=bytes([99])*16000
        im.call(0xb9238,stack=(0,319,0,199))
        try:im.call(0x7f870,limit=1000000)
        except RuntimeError:
            print('Aerodynamic HUD case',index,row,flush=True);raise
        want=bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
        assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
        continue
    height,speed,mach,load,throttle,px,py,pz,brake,chute,cable,dx,dy=row
    im.write(0x13428,'<f',height);im.write(0x13444,'<i',speed);im.write(0x14778,'<d',mach);im.write(0x133f4,'<f',load);im.write(0x133f8,'<f',throttle)
    for field,value in zip((0x13424,0x13430,0x1343c),(px,py,pz)):im.write(field,'<i',value)
    im.write(0x145a8,'<d',brake);im.write(0x14964,'<H',chute);im.write(0x8d14,'<H',cable)
    im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x7f8e0,limit=1000000);im.call(0x7eb7c,limit=1000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'{"Aerodynamic angle-of-attack and climb-rate indicators" if args.aerodynamic else "Upper-HUD flight values and brake/chute/cable labels"} agree in {len(cases)} complete native pixel/coverage frames')
