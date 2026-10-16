#!/usr/bin/env python3
"""Compare native Realistic attitude-command calculation, 0x99f6f..0x9a100.

The original numerical suffix executes without stubbing its producers. Inputs
are the completed input/manual stage's controls and aerodynamic coefficients.
A synthetic caller frame supplies only the enclosing routine's saved EBP/return.
Startup and all arithmetic execute; FSIN/FCOS use the hardware adapter.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_sine_cosine

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);backend=hardware_sine_cosine(im,a.build);rng=random.Random(0x99f6f)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fields=[0x14458,0x14460,0x13d10,0x148a0,0x14788,0x8cf8,0x14338,0x14878,0x14418,0x14700,0x14438,0x14320,0x141c0,0x14158,0x14270,0x14780,0x14268,0x147a0,0x14200,0x14218,0x8cd0,0x14098,0x141b8,0x14120,0x14118,0x14610,0x14620,0x142c0]
cases=[]
for i in range(8192):
    state=[rng.uniform(-3,3) for _ in range(3)]
    manual=[rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(0,1),rng.uniform(-1,1),rng.uniform(0,180000)]
    data=[rng.uniform(-1,1),rng.choice([0,1,1.000001,10,60,150,300,700]),rng.choice([.088,1.225]),rng.uniform(9000,30000)]
    coefficients=[rng.choice([.7,-1.5]),rng.uniform(-5,-.1),rng.uniform(-5,-.1),rng.uniform(.1,2),rng.uniform(-5,-.1)]
    geometry=[rng.choice([50,78,105.9]),rng.choice([5.697,6.4]),rng.choice([10.5,13.2,13.56]),rng.choice([-.8726638888888888,.10471966666666664]),rng.uniform(.1,.3),rng.uniform(-.05,.05)]
    context=[rng.choice([0,.675]),rng.choice([0,-5.7]),rng.uniform(-1e5,1e5),rng.uniform(-1e5,1e5),rng.choice([.02,.04,.1])]
    cases.append([i%2,*map(bits,state+manual+data+coefficients+geometry+context)])
output=subprocess.check_output([str((a.build/'aerodynamic_commands_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    im.write(0x8f32,'<B',row[0])
    for field,value in zip(fields,row[1:]):im.write(field,'<Q',value)
    # The selected suffix uses no enclosing locals; its epilogue restores only
    # EBP/return. Keep the synthetic frame above its ordinary call workspace.
    frame=im.STACK+0x100
    im.cpu.mem_write(frame,struct.pack('<2I',0,im.RETURN));im.cpu.reg_write(r.UC_X86_REG_EBP,frame)
    im.call(0x99f6f)
    expected=[im.read(field,'<Q')[0] for field in fields[:3]]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'All {len(cases)} original Realistic attitude-command cases agree; bounded suffix with explicit caller frame and hardware FSIN/FCOS')
