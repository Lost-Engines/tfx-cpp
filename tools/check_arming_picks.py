#!/usr/bin/env python3
"""Compare arming mount selection with original SSD collision dispatch."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference
from native_planner import NativePlanner

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();resources=NativePlanner(args.data_dir,args.research)
im=NativeReference(args.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,0x30000)
definition,instance=0x300000,0x310000
im.intercept(0xc8568,'Resolve the controlled aircraft SSD handle; original query transforms and event dispatch execute.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,instance),im.return_from()))
def bind(im):
    im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EAX),struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EDX)&65535))
    im.return_from()
im.intercept(0xb4d3c,'Supply symbolic model handles while the original SSD initializer executes.',bind)
rng=random.Random(0xb76a8);cases=[];expected=[]
for plane,name in enumerate(('efa_glob','f17_glob','f22_glob')):
    raw=resources.read('ss/'+name+'.ssd')
    table=10+raw[9]*6
    entries=[table+i*2+struct.unpack_from('<h',raw,table+i*2)[0]*2 for i in range(raw[8])]
    im.cpu.mem_write(definition,raw);im.cpu.mem_write(instance,bytes(65536))
    im.write(0x1b250,'<I',definition)
    im.write(0x20b98,'<I',definition);im.write(0x20b9c,'<I',instance)
    im.write(0x20ba0,'<I',im.native(0xb6c84));im.write(0x20c4a,'<H',0)
    im.call(0xb54dc,eax=definition+entries[0])
    points=[];at=entries[2]
    while struct.unpack_from('<H',raw,at)[0]==28:
        lo=list(struct.unpack_from('<3h',raw,at+2));hi=list(struct.unpack_from('<3h',raw,at+8))
        lo[2]+=160;hi[2]+=160
        centre=[(a+b)//2 for a,b in zip(lo,hi)]
        points.extend([(centre,centre),(lo,hi),(hi,lo),([0,0,0],centre)])
        for axis in range(3):
            for side in (lo,hi):
                for delta in (-1,0,1):
                    point=centre.copy();point[axis]=side[axis]+delta;points.append((point,point))
        at+=16
    for _ in range(4096):
        current=[rng.randrange(-500,501),130,rng.randrange(-700,501)]
        previous=[0,0,0] if rng.randrange(3)==0 else [current[0]+rng.randrange(-20,21),130,current[2]+rng.randrange(-20,21)]
        points.append((previous,current))
    for previous,current in points:
        im.write(0x20b80,'<6h',*previous,*current)
        im.write(0xabec,'<h',-1)
        im.call(0xb76a8,eax=0,edx=0,ebx=0,ecx=160)
        cases.append([plane,*previous,*current]);expected.append(im.read(0xabec,'<h')[0])
actual=subprocess.check_output([str((args.build/'arming_preview_probe').resolve()),str(args.data_dir),'picks'],input=''.join(' '.join(map(str,case))+'\n' for case in cases).encode()).splitlines()
assert len(actual)==len(expected)
for case,got,want in zip(cases,actual,expected):assert int(got)==want,(case,got,want)
print(f'Original arming SSD mount picks agree in {len(cases)} directed boundary and swept-pointer cases')

# Arming holds AAC90 at one, advancing the SSD stream on every model draw.
# Run the complete native actor draw wrapper, supplying only visibility and
# polygon-output boundaries, rather than calling the animation helper directly.
im.intercept(0xcbf24,'Supply a visible arming actor and its output centre; culling is outside this animation capture.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,1),im.return_from(stack_bytes=20)))
for file in (0xb635c,0xb6438,0xb65b0,0xb668c,0xb6810,0xb68dc,0xb6a44):im.intercept(file,'Exclude polygon output while retaining actor draw animation and event dispatch.',lambda im:im.return_from())
im.write(0xac08,'<I',im.native(0x75954))
for field in (0xabf4,0xabf8,0xabfc):im.write(field,'<I',0x300900)
expected=[]
for name in ('efa_glob','f17_glob','f22_glob'):
    raw=resources.read('ss/'+name+'.ssd');table=10+raw[9]*6
    initial=table+struct.unpack_from('<h',raw,table)[0]*2
    im.cpu.mem_write(definition,raw);im.cpu.mem_write(instance,bytes(65536))
    im.write(0x20b98,'<I',definition);im.write(0x20b9c,'<I',instance);im.write(0x20ba0,'<I',im.native(0xb6c84))
    im.call(0xb54dc,eax=definition+initial)
    im.call(0xb52d4,eax=0,edx=5);im.write(0xac90,'<B',1)
    frames=[]
    for _ in range(20):
        im.call(0xb4ff0,eax=0,edx=0,ebx=65536,ecx=160*65536)
        frames.append(bytes(im.cpu.mem_read(instance+17,1))[0])
    expected.append(frames)
actual=subprocess.check_output([str((args.build/'arming_preview_probe').resolve()),str(args.data_dir),'animations']).splitlines()
assert [list(map(int,line.split())) for line in actual]==expected,([line.decode() for line in actual],expected)
print('All three arming bay-animation sequences agree with 60 complete native actor draws')
