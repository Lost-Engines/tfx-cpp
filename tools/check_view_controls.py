#!/usr/bin/env python3
"""Compare the original view queue and all ten function-key selectors.

External contact selection and optional sound requests are declared boundaries.
The real native queue, selectors, fixed camera placement and matrix rotations run.
"""
import argparse
from pathlib import Path
import random
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
context=[]
def target(im):
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000 if context[14] else 0);im.return_from()
def tracking(im):
    im.write(0x1351c,'<I',0x300000 if context[16] else 0);im.return_from()
im.intercept(0x902c4,'Supply the selected target pointer; selection priority is tested separately.',target)
im.intercept(0x901b4,'Supply target availability to the virtual-cockpit selector; bearing is not consumed here.',tracking)
for address in (0xa4edc,0xa6068):im.intercept(address,'Exclude optional fly-past sound effects, which do not change view state.',lambda im:im.return_from())
rng=random.Random(0x8fd84);cases=[]
for view in range(29):
    for key in range(10):
        cases += [[0,view,rng.randrange(-8,9),rng.randrange(51)],[5,key,0,0,0,0,0,0,300,4000,-800,8000,1234,5678,0,1,1,key%2,1],[4],[2],[2]]
for n in range(8192):
    if n%173==0:cases.append([0,rng.randrange(29),rng.randrange(-20,21),rng.randrange(51)])
    op=rng.choices([1,2,3,4,5],[3,4,1,1,8])[0]
    if op==1:cases.append([1,rng.randrange(29),rng.choice([-100,0,19,20,21,300])])
    elif op==5:cases.append([5,rng.randrange(10),*[int(rng.randrange(20)==0) for _ in range(4)],rng.randrange(2),rng.randrange(2),rng.choice([0,19,20,300,1000]),rng.randrange(200000),rng.randrange(-8000,-40),rng.randrange(200000),*[rng.randrange(65536) for _ in range(3)],*[rng.randrange(2) for _ in range(4)]])
    else:cases.append([op])
output=subprocess.check_output([str((a.build/'view_control_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
handlers=[0x85348,0x85498,0x85528,0x855b8,0x855ec,0x856c8,0x857e0,0x858a8,0x8598c,0x85820]
for index,(row,line) in enumerate(zip(cases,output)):
    op,*data=row
    if op==0:
        view,dx,dy=data;im.call(0x8fc44)
        for field,fmt,value in [(0x87b6,'<h',view),(0x13578,'<h',0),(0x10be8,'<h',dx),(0x10be6,'<h',dy),(0x13262,'<h',0),(0x13264,'<h',-1),(0x777a,'<h',-1),(0x777c,'<h',-1),(0x7778,'<h',0),(0x87b4,'<h',0),(0x87ac,'<h',0),(0x10bed,'<B',0),(0x87dc,'<B',0)]:im.write(field,fmt,value)
        im.write(0x13508,'<10h',*([0]*10));im.write(0x13520,'<3i',0,0,0);im.call(0xcccc4,eax=im.data+0x13562)
    elif op==1:im.write(0x13444,'<i',data[1]);im.call(0x8fd84,eax=data[0])
    elif op==2:im.call(0x8fdfc)
    elif op==3:im.call(0x8fd54)
    elif op==4:im.call(0x8feb4)
    elif op==5:
        key,*context=data
        inhibited,crashed,ejected,landing,shift,low,speed,x,y,z,pitch,yaw,roll,missile,available,ground,tracked=context
        for field,fmt,value in [(0xabe9,'<B',inhibited),(0x12c04,'<h',crashed),(0x86ce,'<B',ejected),(0x86cf,'<B',landing),(0x1323c,'<h',shift),(0xa4ea,'<B',low),(0x13444,'<i',speed),(0x13424,'<i',x),(0x13430,'<i',y),(0x1343c,'<i',z),(0x16e70,'<I',0x300000 if missile else 0),(0x8840,'<I',0x300000 if available and ground else 0)]:im.write(field,fmt,value)
        im.write(0x86c8,'<3H',pitch,yaw,roll);im.write(0x14880,'<2d',0,0);im.call(handlers[key])
    want=[]
    for field,fmt in [(0x87b6,'<h'),(0x13578,'<h'),(0x1358c,'<h'),(0x1358e,'<h'),(0x13508,'<10h'),(0x10be8,'<h'),(0x10be6,'<h'),(0x777a,'<h'),(0x777c,'<h'),(0x13262,'<h'),(0x13264,'<h'),(0x87b8,'<h'),(0x7778,'<h'),(0x87b4,'<h'),(0x1357c,'<h'),(0x1357e,'<h'),(0x13580,'<h'),(0x87ac,'<h'),(0x10bed,'<B'),(0x87dc,'<B'),(0x87f0,'<9h'),(0x13562,'<9h'),(0x13520,'<3i')]:want.extend(im.read(field,fmt))
    got=list(map(int,line.split()));assert got==want,(index,row,[(n,x,y) for n,(x,y) in enumerate(zip(got,want)) if x!=y],len(got),len(want))
print(f'All ten view keys and queued transitions agree in {len(cases)} native updates with declared target/audio boundaries')
