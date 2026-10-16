#!/usr/bin/env python3
"""Compare native autopilot rate-to-control conversion, 0x9bb20..0x9bfa5.

The original bounded conversion executes with supplied completed guidance,
current controls and aerodynamic derivatives. The enclosing frame supplies
only scratch space. Hardware FSIN is the only intercepted numerical dependency;
mode 3 retains its incoming controls while clearing the shared pitch bias.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.cpu.mem_map(0x300000,4096);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x9b003);events=[]
def sound(image):
    sample=image.cpu.reg_read(r.UC_X86_REG_EAX);count=image.read(0x1496d,'<B')[0]
    if sample==8:events.append(4 if count==1 else 3)
    elif sample==0x4b:events.append(1 if count==0 else 2)
    else:raise AssertionError(('unexpected guidance sound',sample))
    image.return_from()
im.intercept(0xa4edc,'Observe ordered speed/recovery afterburner sounds',sound)
for file in (0xa4dfc,0xb52d4,0x81198):im.intercept(file,'Observe nonnumerical guidance output delivery',lambda image:image.return_from())
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
guidance=[0x14378,0x143c8,0x14390,0x143b0,0x143a8,0x14370,0x14388,0x143a0,0x14300,0x142f8,0x142f0,0x14340,0x14318,0x13d00]
manual=[0x14338,0x14348,0x8d40,0x145a8]
power=[0x14880,0x14888,0x14878,0x14890,0x14858]
motion=[0x14820,0x147f0,0x14508,0x14758]
geometry=[0x147a0,0x14218,0x14200,0x14098,0x8cd0,0x14430]
data=[0x14438,0x14700,0x14320];coefficients=[0x14268,0x14158,0x14780]
context=[0x140a8,0x14078,0x142d0,0x142d8,0x14408,0x142c0,0x14610]
basis=[0x148c0,0x148d8,0x14860,0x148c8,0x148e0,0x14868,0x148d0,0x148e8,0x14870]
identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for i in range(8192):
    craft=1+i%3;mode=(i//3)%5;stages=0 if craft==2 else 4
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    if i%4:
        for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    frame=struct.unpack('<9h',im.cpu.mem_read(0x300000,18));axes=[frame[row*3+col]*3.051850947599719e-05 for col in range(3) for row in range(3)]
    velocity=[rng.uniform(-300,300),rng.uniform(-300,300),rng.uniform(-50,50)]
    rates=[rng.uniform(-.2,.2) for _ in range(3)]
    if i%4==0:velocity[2]=0;rates=[0,0,0]
    state=[rng.uniform(-1,1) for _ in guidance];state[4]=0 if i%4==0 else rng.uniform(-.3,.3)
    manual_in=[rng.uniform(-1,1),rng.uniform(-25000,0),rng.uniform(100,700),rng.choice([0,1])]
    power_in=[1,1,rng.uniform(0,150000),rng.uniform(0,1),rng.uniform(100,10000)]
    motion_in=velocity+[rng.uniform(-5,5) for _ in range(3)]+rates+[rng.uniform(0,1e5),rng.uniform(0,1e5),rng.uniform(-20000,-500)]+[rng.uniform(-60,60) for _ in range(2)]
    geom=[rng.choice([50,78,105.9]),rng.choice([10.5,13.2,13.56]),rng.choice([5.697,6.4]),.2,.1,.024]
    data_in=[rng.choice([.4,1.225]),rng.choice([150,199.999,200,300,500]),rng.uniform(9000,25000)]
    coeff=[rng.uniform(-2,-.1),rng.uniform(-2,-.1),rng.uniform(.1,2)]
    limits=[rng.uniform(2,4),rng.uniform(2,4)]
    ctx=[rng.choice([96000,120000,187200]),rng.choice([0,60000,124800]),rng.uniform(50000,150000),rng.uniform(100000,300000),rng.uniform(10000,250000),rng.choice([.02,.04,.1]),rng.uniform(-50000,50000)]
    cases.append([craft,i%2,(i//2)%2,(i//4)%2,mode,1,rng.randrange(65536),rng.randrange(-32768,32768),rng.choice([1,2,11,14]),rng.randrange(stages+1),rng.randrange(4),rng.randrange(4),fbits(rng.uniform(.5,1)),*map(bits,state+manual_in+power_in+motion_in+geom+data_in+coeff+limits+ctx+axes),*frame])
for row in cases:
    extra=[.7 if row[0]==1 else -1.5,rng.uniform(-2,-.1),rng.uniform(-.05,.05),rng.uniform(-.5,.5),.675 if row[0]==3 else 0,-5.7 if row[0]==3 else 0,rng.choice([.1,.3,.6]),rng.uniform(0,1)]+[rng.uniform(-1,1) for _ in range(7)]
    row.extend(map(bits,extra))
output=subprocess.check_output([str((a.build/'aerodynamic_guidance_probe').resolve()),'--controls'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];restores=snaps=changes=0
for index,(row,line) in enumerate(zip(cases,output)):
    craft,military,followed,warp,mode,enabled,heading,track,brake,after,control,display,throttle=row[:13];values=row[13:-24];frame=row[-24:-15];extra=row[-15:]
    scalar_groups=[guidance,manual,power];at=0
    for group in scalar_groups:
        for field,value in zip(group,values[at:at+len(group)]):im.write(field,'<Q',value)
        at+=len(group)
    for field in motion:im.write(field,'<3Q',*values[at:at+3]);at+=3
    im.write(0x8c88,'<2Q',*values[at:at+2]);at+=2
    for group in (geometry,data,coefficients,[0x14400,0x143f8],context,basis):
        for field,value in zip(group,values[at:at+len(group)]):im.write(field,'<Q',value)
        at+=len(group)
    assert at==len(values),(at,len(values))
    im.write(0x1493e,'<9h',*frame)
    for field,value,fmt in ((0x11b2a,craft-1,'<H'),(0x1347a,1 if military else 6,'<B'),(0x11108,0x300000 if followed else 0,'<I'),(0xe780,warp,'<B'),(0x14960,mode,'<H'),(0x14958,enabled,'<H'),(0x1493a,heading,'<H'),(0x148f8,track,'<i'),(0x7d77,brake,'<B'),(0x1496d,after,'<B'),(0x10bed,control,'<B'),(0x6c38,display,'<B'),(0x133f8,throttle,'<I'),(0x8cd8+craft-1,0 if craft==2 else 4,'<B'),(0xe76c,23,'<H'),(0x14962,5,'<H'),(0x1327a,1,'<H'),(0x1327c,0,'<H'),(0x1327e,0,'<H'),(0x13278,2,'<H'),(0x13270,.7,'<d'),(0x13269,0,'<B'),(0x1347b,1,'<B'),(0x8867,1,'<B'),(0xabe9,0,'<B'),(0x12c04,0,'<H'),(0x86ce,0,'<B'),(0x8d3a,0,'<H')):im.write(field,fmt,value)
    extra_fields=[0x141c0,0x14270,0x141b8,0x14418,0x14120,0x14118,0x140c8,0x8cf8,0x148a0,0x14788,0x14730,0x14898,0x140b8,0x148f0,0x14848]
    for field,value in zip(extra_fields,extra):im.write(field,'<Q',value)
    events.clear();im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    im.cpu.emu_start(im.native(0x9bb20),im.native(0x9bfa5),count=1000000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x9bfa5)
    expected=[im.read(field,'<Q')[0] for group in (guidance,manual,power) for field in group]+[word for field in motion for word in im.read(field,'<3Q')]+list(im.read(0x8c88,'<2Q'))
    expected += [im.read(field,fmt)[0] for field,fmt in ((0x14962,'<H'),(0x14960,'<H'),(0x14958,'<H'),(0x7d77,'<B'),(0x1496d,'<B'),(0x10bed,'<B'),(0x6c38,'<B'),(0x133f8,'<I'))]+[int(im.read(0x1347b,'<B')[0]==255)]+[v&0xffffffff for v in im.read(0x1493e,'<9h')]+[0,0]+[im.read(field,'<Q')[0] for field in extra_fields[8:]]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    assert not events
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')

print(f'{len(cases)} original autopilot control conversions agree, including mode-3 retained controls, keyboard targets, trim and cleared pitch bias; bounded native region and hardware FSIN')
