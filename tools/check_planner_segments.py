#!/usr/bin/env python3
"""Compare original fixed-point animated route reveals and their remaining lengths."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from native_planner import NativePlanner

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
names=sorted({node['resource'] for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'})
rows=[];expected=[];labels=[]
for name in names:
    planner=NativePlanner(directory,args.research);planner.initialise(name)
    im=planner.image;cpu=planner.cpu;video=planner.video
    base=[bytes(plane) for plane in video.page(video.get(0x59a64))]
    routes=im.read(0xa7c8,'<I')[0];head,=struct.unpack('<I',cpu.mem_read(routes,4));pointer=head;ordinal=0
    while pointer:
        following,=struct.unpack('<I',cpu.mem_read(pointer,4));ordinal+=1
        if not following: break
        x,y=struct.unpack('<2h',cpu.mem_read(pointer+10,4));next_x,next_y=struct.unpack('<2h',cpu.mem_read(following+10,4))
        length=max(abs(next_x-x),abs(next_y-y))
        for extent in sorted({0,2,length//2,length,length+2}):
            cpu.mem_write(pointer,bytes(4))
            video.set(0x55907,0xe800);video.set(0x55909,0xe800)
            for out,data in zip(video.page(0xe800),base):out[:]=data
            im.call(0xacd44,eax=head,limit=10000000)
            remaining=im.call(0xac1d8,eax=243,edx=extent,ebx=x,ecx=199-y,stack=(next_x,199-next_y),limit=10000000)
            expected.append(struct.pack('<I',remaining)+bytes(video.pixels()));labels.append((name,ordinal,extent))
            rows.append(f'{planner.archive.hash_name("waytxt/"+name+".way")} {ordinal} {extent}\n')
            cpu.mem_write(pointer,struct.pack('<I',following))
        pointer=following
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--segments'],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr
actual=result.stdout;assert len(actual)==len(expected)*64004,(len(actual),len(expected))
for number,frame in enumerate(expected):
    found=actual[number*64004:(number+1)*64004]
    assert found==frame,(labels[number],sum(a!=b for a,b in zip(found,frame)),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(found,frame)) if a!=b][:12])
print(len(expected),'complete original fixed-point route reveals agree in remaining length and every pixel, including empty, partial and completed segments')
