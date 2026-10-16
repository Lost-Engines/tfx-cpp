#!/usr/bin/env python3
"""Compare original mount permissions and complete pylon assignment state."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--save-fixture',type=Path)
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu
model_base=image.native(0x70aa4+0x47c94)
rng=random.Random(0x89c08)
patterns=sorted({0,1023,*[1<<slot for slot in range(10)],*[(1<<a)|(1<<b) for a in range(10) for b in range(a+1,10)]})
cases=[(plane,weapon,occupied,(plane+weapon+occupied)%10) for plane in range(1,4) for weapon in range(-1,27) for occupied in patterns]
cases += [(rng.randrange(1,4),rng.randrange(-1,27),rng.randrange(1024),rng.randrange(10)) for _ in range(1024)]
for synthetic in (False,True):
    if synthetic:
        for weapon in range(27):
            for plane,field in enumerate((23,27,25)):
                image.write(0x809c+weapon*48+field,'<H',(weapon*317+plane*193+0x155)&1023)
    rows=[];expected=[]
    for plane,weapon,occupied,slot in cases:
        image.write(0x11b2a,'<H',plane-1);image.write(0x1330e,'<h',weapon)
        for mount in range(10):
            present=bool(occupied&(1<<mount))
            image.write(0x13374+mount*2,'<2B',1 if present else 255,int(present))
            cpu.mem_write(model_base+mount*2,struct.pack('<H',mount+10 if present else 65535))
        allowed=0
        if weapon>=0:
            for mount in range(10):
                if image.call(0x89c08,eax=mount)&255:allowed|=1<<mount
        image.call(0x8b3d4,eax=slot,edx=123)
        values=[allowed]
        for mount in range(10):
            values.extend([*image.read(0x13374+mount*2,'<2B'),int(struct.unpack('<H',cpu.mem_read(model_base+mount*2,2))[0]!=65535)])
        rows.append(f'{plane} {weapon} {occupied} {slot}\n');expected.append(values)
    result=subprocess.run([str(args.build/'arming_probe'),'--synthetic' if synthetic else str(args.data_dir)],input=''.join(rows),capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    actual=[list(map(int,line.split())) for line in result.stdout.splitlines()]
    assert len(actual)==len(expected),(len(actual),len(expected))
    for number,(a,b) in enumerate(zip(actual,expected)):assert a==b,(synthetic,cases[number],a,b)
    if synthetic and args.save_fixture:
        selected={plane*28*len(patterns)+weapon*len(patterns)+(weapon*11+plane*7)%len(patterns) for plane in range(3) for weapon in range(28)}
        fixture=[]
        for number in sorted(selected):
            digest=14695981039346656037
            for value in expected[number]:
                for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            fixture.append(rows[number].strip()+' '+str(digest)+'\n')
        args.save_fixture.write_text(''.join(fixture))
    print(len(cases),'synthetic' if synthetic else 'retail','complete mount-permission/assignment states agree, including all occupied pairs, unrelated stores, clearing and forbidden assignments',flush=True)
