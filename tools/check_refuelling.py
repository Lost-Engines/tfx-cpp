#!/usr/bin/env python3
"""Compare persistent native tanker selection/coupling, hookup and fuel transfer.

Original key handler, selector/controller, anchor placement, bearing, integer
roots and fuel-transfer prefix execute. Allied registry, player poses, flags,
shape types and ticks are supplied. SSD shape-type lookup is supplied at its
already verified resource boundary. Model/sound/voice/radio requests are
observed without rendering or playback; other flight physics is not simulated.
"""
import argparse
from collections import Counter
import math
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();directory=a.research/'installs/cd_1994_09/TFX';im=NativeReference(directory/'TFX.DAT');im.cpu.mem_map(0x300000,0x10000)
events=[];types=[-1]*50;moved=None;warning=False;pointer=lambda slot:0x300000+slot*256
im.intercept(0xb7a3c,'Supply the verified SSD shape category for a registry resource handle',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,types[(image.cpu.reg_read(r.UC_X86_REG_EAX)&65535)-1]&0xffffffff),image.return_from()))
im.intercept(0xa4dfc,'Observe urgent-priority sample requests without audio playback',lambda image:(events.append([0,image.cpu.reg_read(r.UC_X86_REG_EAX),-1]),image.return_from()))
im.intercept(0xa4edc,'Observe normal-priority sample requests without audio playback',lambda image:(events.append([1,image.cpu.reg_read(r.UC_X86_REG_EAX),-1]),image.return_from()))
def model(image):
    handle=image.cpu.reg_read(r.UC_X86_REG_EAX)&65535;entry=image.cpu.reg_read(r.UC_X86_REG_EDX)&65535
    assert handle==777 or 1<=handle<=50
    events.append([2 if handle==777 else 3,entry,-1 if handle==777 else handle-1]);image.return_from()
im.intercept(0xb52d4,'Observe SSD player/tanker entry requests without evaluating the separate scene program',model)
def voice(image):
    stack=image.cpu.reg_read(r.UC_X86_REG_ESP);arguments=struct.unpack('<4I',image.cpu.mem_read(stack+4,16))
    assert arguments==(1,image.data+0x9f62,image.data+0x9d40,0),arguments
    events.append([4,0,-1]);image.return_from()
im.intercept(0x70b44,'Observe the fixed refuelling connected-voice request without playback',voice)
def radio(image):
    global warning
    assert image.cpu.reg_read(r.UC_X86_REG_EAX)==image.data+0x23e4
    warning=True;image.return_from()
im.intercept(0x81198,'Observe the supplied-afterburner refuelling radio warning',radio)
def following(cpu,address,size,unused):
    global moved
    moved=(cpu.reg_read(r.UC_X86_REG_ESI)-pointer(0))//256
    assert 0<=moved<50
im.cpu.hook_add(UC_HOOK_CODE,following,begin=im.native(0x95171),end=im.native(0x95171));im.write(0xe76c,'<H',777);im.write(0xac74,'<I',im.native(0x70b44))
rng=random.Random(0x94efc);cases=[]
for craft in range(3):
    for variant in range(16):
        world=[10000,-1200,20000];angles=[0,0,0]
        for step in range(128):
            if variant>=4 and step%8==0:
                world=[rng.randrange(-1000000,1000000),rng.randrange(-8000,0),rng.randrange(-1000000,1000000)]
                angles=[rng.randrange(65536) for _ in range(3)]
            elif variant<4:
                angles=[0x1000 if 80<=step<90 else 0,0,0]
            q8=[value*256+fraction for value,fraction in zip(world,(17,-13,37))]
            patches=[]
            if step==0:
                for slot,kind,flags,offset in [(0,49,1,(0,0,1000)),(1,50,256,(0,0,1000)),(2,50,1,(5000,-500,12000)),(3,50,1,(5000,-500,24000)),(49,50,1,(5000,-500,12000))]:
                    patches.append([slot,1,kind,flags,*[p+d for p,d in zip(q8,offset)],*angles])
            if variant>=4 and step%32==0:patches.append([2,1,50,1,*[p+rng.randrange(-20000,20000) for p in q8],*angles])
            if variant==2 and step==64:patches.append([2,0,0,0,0,0,0,0,0,0])
            divisors=[(24,12,24),(1,1,1),(50,30,50),(2,3,4)][variant%4] if variant>=4 else (24,12,24)
            elapsed=4 if variant<2 else [0,1,4,16,108,65535][step%6]
            speed=300 if variant<4 else [0,269,270,300,360,361,800][step%7]
            toggle=int(step in (100,110)) if variant<4 else int(step%19==0)
            fuel=[0,-0.0,1000,math.nextafter(986,0),math.nextafter(986,math.inf),10000][step%6]
            row=[int(step==0),1 if variant<4 else variant%2,variant%3,0 if variant<4 else variant%4,[0,1,50,-1,32767,-32768][variant%6],*divisors,-1 if variant%3 else 2,123,11,22,33,craft,*world,*q8,*angles,speed,elapsed,toggle,int(variant>=4 and step%5==0),int(variant>=4 and step%7==0),int(variant>=4 and step%11==0),step%3,fuel,[1000,5000,0,-100][step%4],step%2,len(patches)]
            for patch in patches:row.extend(patch)
            cases.append(row)
observed=Counter()
output=subprocess.check_output([str((a.build/'refuelling_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for index,(row,line) in enumerate(zip(cases,output)):
    reset,enabled,saved,phase,delay,dx,dy,dz,selected,horizontal,ex,ey,ez,craft=row[:14];world=row[14:17];q8=row[17:20];angles=row[20:23];speed,elapsed,toggle,inhibited,crashed,ejected,mode,fuel,capacity,burner,patch_count=row[23:34]
    if reset:
        types[:]=[-1]*50;im.write(0x10f6c,'<50I',*([0]*50));im.write(0x7785,'<B',enabled);im.write(0x13268,'<B',saved);im.write(0x13b04,'<B',phase);im.write(0x8c82,'<h',delay);im.write(0x8c7c,'<3h',dx,dy,dz);im.write(0x13af4,'<I',pointer(selected) if selected>=0 else 0);im.write(0x13af0,'<i',horizontal);im.write(0x13af8,'<3i',ex,ey,ez)
        im.cpu.mem_write(pointer(0),bytes(50*256))
    for patch in range(patch_count):
        slot,present,kind,flags,*pose=row[34+patch*10:44+patch*10];types[slot]=kind;im.write(0x10f6c+slot*4,'<I',pointer(slot) if present else 0)
        if present:
            im.cpu.mem_write(pointer(slot),struct.pack('<3i3H',*pose));im.cpu.mem_write(pointer(slot)+0x42,struct.pack('<H',flags));im.cpu.mem_write(pointer(slot)+0x2a,struct.pack('<H',slot+1))
    for field,value in zip((0x13424,0x13430,0x1343c),world):im.write(field,'<i',value)
    im.write(0x10f28,'<3i',*q8);im.write(0x86c8,'<3H',*angles);im.write(0x11b2a,'<H',craft);im.write(0x13444,'<i',speed);im.write(0x13476,'<H',elapsed)
    im.write(0xabe9,'<B',inhibited);im.write(0x86ce,'<B',crashed);im.write(0x12c04,'<H',ejected);im.write(0x7140,'<B',mode);im.write(0x11108,'<I',0x400100)
    im.write(0x14858,'<d',fuel);im.write(0x14770,'<d',capacity);im.write(0x1496d,'<B',burner);events.clear();moved=None;warning=False
    if toggle:im.call(0x83e00)
    im.cpu.mem_write(im.STACK,struct.pack('<I',im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    im.cpu.emu_start(im.native(0x8f6df),im.native(0x8f72c),count=100000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8f72c)
    try:im.call(0x94efc,limit=1000000)
    except RuntimeError as error:raise RuntimeError((index,row[:34],str(error))) from error
    selected,=im.read(0x13af4,'<I');target,=im.read(0x11108,'<I')
    expected=[*im.read(0x7785,'<B'),*im.read(0x13268,'<B'),*im.read(0x13b04,'<B'),*im.read(0x8c82,'<h'),*im.read(0x8c7c,'<3h'),(selected-pointer(0))//256 if selected else -1,*im.read(0x13af0,'<i'),*im.read(0x13af8,'<3i'),*im.read(0x7140,'<B'),(target-pointer(0))//256 if target!=0x400100 else -1,moved if moved is not None else -1]
    expected.extend(im.read(field,'<i')[0] for field in (0x13424,0x13430,0x1343c));expected.extend([*im.read(0x14858,'<Q'),int(warning),len(events)])
    for event in events:expected.extend(event)
    for slot in range(50):
        present=im.read(0x10f6c+slot*4,'<I')[0]!=0;expected.append(int(present))
        if present:expected.extend(struct.unpack('<3i3H',im.cpu.mem_read(pointer(slot),18)));expected.extend([struct.unpack('<H',im.cpu.mem_read(pointer(slot)+0x42,2))[0],types[slot]])
    observed['coupled_frames']+=int(expected[2]==3)
    observed['tanker_updates']+=int(moved is not None)
    if (index//128)%16<4:observed['connections_from_approach']+=sum(event[0]==4 for event in events)
    actual=list(map(int,line.split()));assert actual==expected,(index,row[:34],[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:20],actual[:25],expected[:25],len(actual),len(expected))
print(f'Native refuelling selection/coupling, tanker poses, exact fuel bits and requests agree in {len(cases)} persistent updates across all three aircraft')

print(dict(observed))
