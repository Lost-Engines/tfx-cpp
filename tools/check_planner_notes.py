#!/usr/bin/env python3
"""Compare every retail planner annotation using complete native widget painters."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from unicorn import x86_const as r
from native_planner import NativePlanner

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
names=sorted({node['resource'] for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'})
rows=[];expected=[];labels=[];counts=[]
for name in names:
    planner=NativePlanner(directory,args.research)
    planner.image.intercept(0xaae74,'Mission-note widget comparison excludes the separately loaded geographic cell-label table.',lambda im:im.return_from())
    planner.initialise(name)
    rows.append(str(planner.archive.hash_name('waytxt/'+name+'.way'))+'\n')
    im=planner.image;cpu=planner.cpu;video=planner.video
    base=[bytes(plane) for plane in video.page(video.get(0x59a64))]
    count=im.read(0xa7b4,'<H')[0]
    keys=[struct.unpack('<IH',cpu.mem_read(im.data+0x17320+index*6,6))[1] for index in range(count)]
    counts.append(len(keys))
    for key in keys:
        video.set(0x55907,0xe800);video.set(0x55909,0xe800)
        for out,data in zip(video.page(0xe800),base):out[:]=data
        im.write(0x2416c,'<I',0)
        im.write(0x2418b,'<B',0)
        im.write(0x24186,'<B',0)
        im.write(0x24178,'<H',0xe800)
        im.call(0xaaadc,eax=key&255,edx=key>>8);widget=cpu.reg_read(r.UC_X86_REG_EAX)
        assert widget
        im.call(0xaedec,eax=widget,limit=10000000)
        im.call(0xcebf8,eax=widget,edx=im.data+0x17edc,ebx=15,ecx=1,stack=(1,),limit=10000000)
        expected.append(bytes(video._deplane(video.page(video.get(0x59a66)))));labels.append((name,key))
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--notes'],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr
actual=result.stdout;offset=0;number=0
for name,count in zip(names,counts):
    found_count,=struct.unpack_from('<I',actual,offset);offset+=4
    assert found_count==count,(name,found_count,count)
    for _ in range(count):
        frame=expected[number];found=actual[offset:offset+64000];offset+=64000
        assert found==frame,(labels[number],sum(a!=b for a,b in zip(found,frame)),[(i%320,i//320,a,b) for i,(a,b) in enumerate(zip(found,frame)) if a!=b][:12])
        number+=1
assert offset==len(actual)
print(len(expected),'complete native annotation widgets agree pixel for pixel across all retail planners, including placement, text truncation and frame/text overlap')
