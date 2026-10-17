#!/usr/bin/env python3
"""Compare original aircraft/surface draw admission before the renderer.

Complete 0x78180 and 0x7c354 pool traversal and range checks execute. The
orientation/SSD drawing boundary records admitted handles and reports hidden,
so post-visible AI activation is outside this isolated spatial comparison.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000,4096);im.cpu.mem_write(0x300000,(0x300200).to_bytes(4,'little'))
im.write(0x128c8,'<I',0x300200)
im.intercept(0xb6ea4,'Orientation handoff is outside spatial admission; pool traversal and all range predicates execute.',lambda image:image.return_from())
seen=[]
def draw(image):
    seen.append(image.cpu.reg_read(r.UC_X86_REG_EAX))
    image.cpu.reg_write(r.UC_X86_REG_EAX,0);image.return_from()
im.intercept(0xb4ff0,'Record admitted SSD handle and return hidden; actual projection/drawing has separate original VGA checks.',draw)
rng=random.Random(0x78180);rows=[];expected=[]
wrap=lambda v:((v+2147483648)&4294967295)-2147483648
edges=(-2147483648,-4194305,-4194304,-4194303,-1,0,1,4194303,4194304,4194305,2147483647)
for i in range(4096):
    reference=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
    delta=[rng.randrange(-4194304,4194305) for _ in range(3)]
    delta[i%3]=edges[(i//3)%len(edges)]
    position=[wrap(v+d) for v,d in zip(reference,delta)];row=position+reference;rows.append(row)
    im.cpu.mem_write(0x300200,b'\0'*80)
    im.cpu.mem_write(0x300200,struct.pack('<3i',*position));im.cpu.mem_write(0x30022a,struct.pack('<H',77))
    seen.clear();im.call(0x78180,eax=0x300000,edx=1,ebx=reference[0]&0xffffffff,ecx=reference[1]&0xffffffff,stack=(reference[2]&0xffffffff,))
    air=int(seen==[77]);assert seen in ([],[77]),seen
    im.cpu.mem_write(0x300224,struct.pack('<H',77))
    seen.clear();im.call(0x7c354,eax=reference[0]&0xffffffff,edx=reference[1]&0xffffffff,ebx=reference[2]&0xffffffff)
    surface=int(seen==[77]);assert seen in ([],[77]),seen
    expected.append([air,surface])
output=subprocess.check_output([str((a.build/'actor_visibility_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
actual=[list(map(int,line.split())) for line in output]
assert actual==expected,next(((i,rows[i],got,want) for i,(got,want) in enumerate(zip(actual,expected)) if got!=want),('length',len(actual),len(expected)))
if a.record:
    a.record.write_text('\n'.join(' '.join(map(str,row+want)) for i,(row,want) in enumerate(zip(rows,expected)) if i<128 or i%31==0)+'\n')
print(f'{len(rows)} complete original aircraft/surface draw regions agree: inclusive Q8 bounds, air altitude exclusion, surface altitude, wrapping and INT_MIN')
