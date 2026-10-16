#!/usr/bin/env python3
"""Compare the scripted native automatic approach, flare and rollout stage.

The original 0x9fecf..0xa028f region executes its rotations, integer conversions,
square root, frame/basis updates and kinematic motion. Execution stops before
the separate touchdown finalizer when requested. Only hardware FSIN/FCOS use
adapters; no approach or motion rules are substituted.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_x87 import hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backend=hardware_sine_cosine(im,a.build);rng=random.Random(0x9fecf)
for file in (0xa028f,0xa02c8):im.cpu.hook_add(UC_HOOK_CODE,lambda cpu,address,size,unused:cpu.emu_stop(),begin=im.native(file),end=im.native(file))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];basis=[0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870];cases=[]
for i in range(8192):
 carrier=i%2;wheel=rng.uniform(1,4);deck=carrier*20*.3048*8
 position=[rng.uniform(-1e6,1e6),rng.uniform(-1e6,1e6),rng.choice([-wheel-deck-.001,-wheel-deck,-wheel-deck+.001,rng.uniform(-10000,0)])]
 if i%101==0:position=[1e12,-1e12,0]
 targets=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
 if i%3:targets=[int(position[1])+rng.randrange(-100,101),0,int(position[0])+rng.randrange(-100,101)]
 if i%101==0:targets=[0,0,0]
 values=position+[rng.uniform(-63,63) for _ in range(2)]+[rng.uniform(0,10),rng.choice([-20,-7,0,19,20,21]),rng.choice([-2,0,.499999,.5,.500001,2.499999,2.5,2.500001,100,140]),rng.choice([.01,.02,.05,.2]),wheel]
 cases.append([rng.randrange(65536),carrier,(i//2)%2,*targets,*[rng.randrange(-1000000,1000000) for _ in range(3)],*map(bits,values)])
output=subprocess.check_output([str((a.build/'automatic_approach_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];flares=stops=0
for i,(row,line) in enumerate(zip(cases,output)):
 heading,carrier,flare=row[:3];target=row[3:6];player=row[6:9];values=row[9:]
 im.write(0x8f88,'<H',heading);im.write(0x8f8b,'<B',carrier);im.write(0x1495a,'<H',flare);im.write(0x14920,'<3i',*target);im.write(0x1492c,'<3i',*player)
 im.write(0x14758,'<3Q',*values[:3]);im.write(0x8c88,'<2Q',*values[3:5])
 for f,v in zip((0x14398,0x14378,0x14700,0x142c0,0x145e8),values[5:]):im.write(f,'<Q',v)
 im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x9fecf),im.RETURN,count=1000000)
 stop=im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0xa02c8);assert im.cpu.reg_read(r.UC_X86_REG_EIP) in (im.native(0xa028f),im.native(0xa02c8))
 expected=[v&0xffffffff for f in (0x14920,0x1492c) for v in im.read(f,'<3i')]+[im.read(f,'<Q')[0] for f in (0x14398,0x14378,0x14700)]+list(im.read(0x14758,'<3Q'))+list(im.read(0x8c88,'<2Q'))+[im.read(f,'<Q')[0] for f in basis]+[v&0xffffffff for v in im.read(0x1493e,'<9h')]+[im.read(0x1495a,'<H')[0],int(stop)]
 actual=list(map(int,line.split()));assert actual==expected,(i,row,[(j,x,y) for j,(x,y) in enumerate(zip(actual,expected)) if x!=y])
 flares+=not flare and bool(im.read(0x1495a,'<H')[0]);stops+=stop
 if i%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert flares>1000 and stops>1000
print(f'{len(cases)} original automatic approach/flare/rollout updates agree: {flares} new flares and {stops} touchdown-finalizer requests; only hardware transcendental adapters')
