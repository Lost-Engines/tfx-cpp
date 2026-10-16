#!/usr/bin/env python3
"""Compare complete original Tour reviews through their automatic parser return.

Held right mouse dismisses notes. Note calls, every segment reveal extent and
successful return are observed without replacing those original routines. Only
DOS resources/hardware/heap are supplied; the final palette ramp executes unchanged.
"""
import argparse
import json
from pathlib import Path
import subprocess
import struct
from unicorn import x86_const as r
from native_planner import NativePlanner

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
names=sorted({node['resource'] for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'})
expected=[];total=0;palettes=[]
for name in names:
    planner=NativePlanner(directory,args.research);planner.buttons=2;planner.stop_after=None
    im=planner.image;cpu=planner.cpu;cpu.mem_write(0x7f1000,name.encode('ascii')+bytes(1));events=[]
    im.intercept(0xaaf04,'Observe note order; the original lookup, widget and wait continue.',lambda im:events.append('N'+str(cpu.reg_read(r.UC_X86_REG_EAX)&65535)))
    im.intercept(0xac1d8,'Observe reveal extents; original clipping, pixels and progress continue.',lambda im:events.append('S'+str(cpu.reg_read(r.UC_X86_REG_EDX)&65535)))
    fading=[False];fades=[]
    im.intercept(0xca3c0,'Observe entry to the final fade without replacing its original ramp.',lambda im:fading.__setitem__(0,True))
    def palette(im):
        if fading[0]:
            pointer,=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+4,4))
            fades.append(bytes((value*255+31)//63 for value in cpu.mem_read(pointer,768)))
    im.intercept(0xde454,'Observe complete hardware DAC transfers; original palette storage/output continues.',palette)
    result=im.call(0xaed28,eax=0x7f1000,edx=im.data+0x48c4,ebx=1,limit=100000000)
    assert result==1,(name,result)
    assert len(fades)==40,(name,len(fades))
    palettes.extend(fades+[bytes(768)])
    total+=len(events);expected.append(' '.join(events+['done']))
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--review'],input='\n'.join(names)+'\n',capture_output=True,text=True)
assert result.returncode==0,result.stderr
actual=result.stdout.splitlines();assert len(actual)==len(expected)
for name,a,b in zip(names,actual,expected):assert a==b,(name,a,b)
print(len(names),'complete native Tour reviews agree in',total,'note/reveal transitions and automatic parser return; all original note waits and line progress execute')
result=subprocess.run([str(args.build/'planning_probe'),str(directory),'--review-fade'],input=('\n'.join(names)+'\n').encode(),capture_output=True)
assert result.returncode==0,result.stderr
assert result.stdout==b''.join(palettes),'review fade palette/phase differs'
print(len(palettes),'complete final palettes agree with original native 40-retrace fades and the final black screen')
