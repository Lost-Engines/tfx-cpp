#!/usr/bin/env python3
"""Compare original cockpit, head-turn and chase camera motion and matrices.

Player poses and the current ground height are supplied. Unrelated navigation,
world-painter configuration, weather and player-model flag writes are excluded.
The actual native camera dispatcher, smoothing and matrix setters execute.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference
from unicorn import x86_const as r

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--refuelling',action='store_true',help='exercise all four refuelling model phases')
parser.add_argument('--horizon',action='store_true',help='observe the native background pitch/roll handoff')
parser.add_argument('--split-basis',action='store_true',help='supply distinct physics and renderer bases as used by Simple flight')
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');base=im.layout['objects'][0]['preferred_base']
for address,reason in [(0x94efc,'Supply the player pose without the separate navigation-contact controller.'),(0xca780,'Exclude world-painter mode configuration; native camera matrix setters still execute.'),(0xca6fc,'Exclude missile-camera world-painter mode configuration.'),(0xb6ea4,'Exclude forwarding player angles into the model renderer.'),(0xb4fd0,'Exclude forwarding the player model into the scene queue.'),(0x90320,'Exclude forwarding the player pose into the model renderer.')]:im.intercept(address,reason,lambda im:im.return_from())
horizon_angles=[];ground_motion=[]
if a.horizon:
    im.intercept(0x8fcd4,'Observe native horizon pitch/roll from the complete camera controller; its complete geometry/VGA consumer is checked separately.',lambda im:(horizon_angles.append([im.cpu.reg_read(r.UC_X86_REG_EAX)&65535,im.cpu.reg_read(r.UC_X86_REG_EDX)&65535,struct.unpack('<h',im.cpu.mem_read(base+0x47c08,2))[0]]),im.return_from()))
im.intercept(0xcac04,'Observe native ground-phase movement after the completed camera update; its exact counter is checked separately.',lambda im:(ground_motion.append(im.cpu.reg_read(r.UC_X86_REG_EAX)&65535),im.return_from()))
if a.horizon:
    im.intercept(0xcaf84,'Observe the direct missile-nose horizon call; geometry/VGA rendering has separate checks.',lambda im:(horizon_angles.append([im.cpu.reg_read(r.UC_X86_REG_EAX)&65535,im.cpu.reg_read(r.UC_X86_REG_EDX)&65535,struct.unpack('<h',im.cpu.mem_read(base+0x47c08,2))[0]]),im.return_from()))
model_entries=[]
im.intercept(0xb52d4,'Record the native player-model entry request without loading its SSD resource.',lambda im:(model_entries.append(im.cpu.reg_read(r.UC_X86_REG_EDX)&65535),im.return_from()))
im.intercept(0x787fc,'Supply no fallback aircraft when neither an explicit ground nor air target is selected.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
im.write(0x13b04,'<B',0);im.cpu.mem_map(0x300000,4096);im.cpu.mem_map(0x310000,4096)
im.write(0xe774,'<B',0);im.write(0x8840,'<I',0);im.write(0x1351c,'<I',0)
rng=random.Random(0x92144);cases=[]
identity=[32767,0,0,0,32767,0,0,0,32767]
modes=[0,3,4,6,7,8,9,10,11,12,13,14,15,16,17,18,20,21,23,24,25,26,27,28]
for mode in modes:
    for variant in range(4):
        position=[rng.randrange(200000),rng.randrange(-8000,-32),rng.randrange(200000)]
        if mode==21:position[1]=[-1000,-81,-80,-1][variant]
        angles=[rng.randrange(65536) for _ in range(3)]
        im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
        for entry,angle in zip((0xccf4c,0xcd058,0xcd15c),angles):im.call(entry,eax=0x300000,edx=angle)
        basis=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
        im.cpu.mem_write(0x300000,struct.pack('<9h',*basis))
        im.call(0xccf4c,eax=0x300000,edx=(variant+1)*4096)
        im.call(0xcd15c,eax=0x300000,edx=1024)
        body=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
        orbit=identity if variant<2 else basis
        for step in range(128):
            # Persistent runs include deliberate signed-angle wrap and floor contact.
            angles=[(value+rng.randrange(-128,129))&65535 for value in angles]
            position=[position[0]+rng.randrange(-8,9),position[1]+rng.randrange(-2,3),position[2]+rng.randrange(-8,9)]
            q8=[v*256+rng.randrange(256) for v in position]
            pan=0 if step<32 else rng.randrange(256) if mode==4 else rng.randrange(16) if mode in (8,9) else 0
            row=[step==0,mode,*position,*q8,*angles,rng.choice([1,10,20,30,50]),pan,-32,variant%2,*basis]
            row += [int(step%7!=0),position[0]*256+32000,position[1]*256+8000,position[2]*256+24000,int((step+1)%11!=0),position[0]*256-16000,position[1]*256-10000,position[2]*256-32000,300,int(step%23==0)]
            row += [int(mode==7 or step<32 or step%17>4),q8[0]+1000,q8[1]-2000,q8[2]+4000,*angles,row[28],*row[29:32]]
            if step==0:row += [40 if mode==4 else 30 if mode==16 else 0,variant%2,20,variant//2,[0,300,2500,-100][variant],position[0]+100,position[1]-10,position[2]+100,*orbit]
            if a.split_basis:row+=body
            cases.append(row)
if a.refuelling:
    for index,row in enumerate(cases):row.append(index%4)
command=[str((a.build/'view_camera_probe').resolve())]
if a.refuelling:command.append('--refuelling')
if a.horizon:command.append('--horizon')
if a.split_basis:command.append('--split-basis')
output=subprocess.check_output(command,input=('\n'.join(' '.join(str(int(v)) for v in row) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for index,(row,line) in enumerate(zip(cases,output)):
    phase=row[-1] if a.refuelling else 0
    if a.refuelling:row=row[:-1]
    body=row[-9:] if a.split_basis else row[15:24]
    if a.split_basis:row=row[:-9]
    im.write(0x13b04,'<B',phase)
    reset,mode=row[:2];position=row[2:5];q8=row[5:8];angles=row[8:11];elapsed,pan,ground,low=row[11:15];basis=row[15:24];tracked,tx,ty,tz,observed,ox,oy,oz,speed,landing=row[24:34]
    if reset:
        if a.horizon:im.cpu.mem_write(base+0x47c08,struct.pack('<h',0))
        distance,recenter,delay,tracking,target_distance,fx,fy,fz=row[45:53];orbit=row[53:62]
        im.call(0x8fc44);im.write(0x87ac,'<h',0);im.write(0x13494,'<3i',0,0,0);im.write(0x134ac,'<3H',0,0,0);im.write(0x13508,'<10h',*([0]*10));im.write(0x13578,'<h',0);im.write(0x87b6,'<h',mode);im.write(0x87b8,'<h',distance);im.write(0x1357c,'<h',recenter);im.write(0x1357e,'<h',delay);im.write(0x13580,'<h',tracking);im.write(0x87b4,'<h',target_distance);im.write(0x13520,'<3i',fx,fy,fz);im.write(0x87f0,'<9h',*orbit)
        im.write(0x87ba,'<3h',0,0,0);im.write(0x87c0,'<3i',0,0,0);im.write(0x13590,'<2H',0,0);im.write(0x13588,'<H',0);im.write(0x134dc,'<i',0);im.write(0x1359c,'<i',position[0]);im.write(0x13598,'<i',position[1]);im.write(0x13594,'<i',position[2])
    missile,mx,my,mz,mp,mh,mr,impact,ix,iy,iz=row[34:45]
    im.write(0x16e70,'<I',0x310200 if missile else 0);im.cpu.mem_write(0x310208,struct.pack('<3i',mx,my,mz));im.cpu.mem_write(0x310220,struct.pack('<3H',mp,mh,mr))
    im.write(0x87dc,'<B',0)
    im.write(0x13444,'<i',speed);im.write(0x86cf,'<B',landing)
    im.write(0x11108,'<I',0x310000 if tracked else 0);im.write(0x11104,'<I',0x310100 if observed else 0)
    im.cpu.mem_write(0x310000,struct.pack('<3i',tx,ty,tz));im.cpu.mem_write(0x310100,struct.pack('<3i',ox,oy,oz))
    for field,value in zip((0x13424,0x13430,0x1343c),position):im.write(field,'<i',value)
    im.write(0x10f28,'<3i',*q8);im.write(0x86c8,'<3H',*angles);im.write(0x13476,'<H',elapsed);im.write(0x1358a,'<H',pan);im.write(0xabf2,'<h',ground);im.write(0xa4ea,'<B',low)
    im.cpu.mem_write(base+0x47c38,struct.pack('<9h',*basis));im.write(0x1345e,'<9h',*body)
    for field,value in zip((0x1341c,0x13428,0x13434),q8):im.write(field,'<f',value/256)
    model_entries.clear();horizon_angles.clear();ground_motion.clear()
    im.call(0x92144,limit=2000000)
    want=[]
    for field,fmt in [(0x87b8,'<h'),(0x1357c,'<h'),(0x1357e,'<h'),(0x87dc,'<B'),(0x87f0,'<9h'),(0x87ba,'<3h'),(0x87c0,'<3i'),(0x13590,'<2H'),(0x13588,'<H'),(0x87b0,'<h'),(0x87b2,'<h'),(0x87ae,'<h'),(0x134dc,'<i'),(0x134f0,'<i'),(0x134f8,'<i'),(0x13500,'<i')]:want.extend(im.read(field,fmt))
    want += [struct.unpack('<i',im.cpu.mem_read(base+field,4))[0] for field in (0x491e1,0x491e7,0x491ed)]
    want += list(struct.unpack('<9h',im.cpu.mem_read(base+0x47c4a,18)))
    assert len(model_entries)<=1,(index,model_entries)
    want += [model_entries[0] if model_entries else -1]
    for field,fmt in [(0x87b6,'<h'),(0x87b4,'<h'),(0x1358c,'<h'),(0x1358e,'<h'),(0x13508,'<10h'),(0x87ac,'<h'),(0x13580,'<h'),(0x1358a,'<H'),(0x13494,'<3i'),(0x134ac,'<3H'),(0x13520,'<3i')]:want.extend(im.read(field,fmt))
    if a.horizon:
        want += [1,*horizon_angles[-1]] if horizon_angles else [0,0,0,0]
        want += [int(bool(ground_motion)),struct.unpack('<h',struct.pack('<H',ground_motion[-1]))[0] if ground_motion else 0,*[im.read(at,'<i')[0] for at in (0x1359c,0x13598,0x13594)]]
    got=list(map(int,line.split()));assert got==want,(index,row,[(n,x,y) for n,(x,y) in enumerate(zip(got,want)) if x!=y][:25],len(got),len(want))
print(f'{len(modes)} cockpit, head/chase, missile/infrared and impact camera modes agree in {len(cases)} native pose/matrix updates with declared world/weather boundaries')
