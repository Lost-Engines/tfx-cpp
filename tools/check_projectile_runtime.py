#!/usr/bin/env python3
"""Compare the original projectile population loop, including dispenser births.

Only world contacts, SSD output, mounted anchors and threat registration are
intercepted. The original linked list, constructors, removal, clock wrapper,
all motion callbacks and child constructors execute unchanged.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from unicorn import x86_const as r, UC_HOOK_CODE
from native_reference import NativeReference
from check_projectiles import KINDS


def original(data_dir,frames,elapsed,dispenser,capacity):
    image=NativeReference(data_dir/'TFX.DAT');cpu=image.cpu
    cpu.mem_map(0x300000,0x40000);cpu.mem_map(0x400000,0xa0000)
    head,tail=0x320000,0x320100
    cpu.mem_write(head+52,struct.pack('<I',tail));cpu.mem_write(tail+56,struct.pack('<I',head))
    count=capacity
    for index in range(count):cpu.mem_write(0x400000+index*80+52,struct.pack('<I',0x400000+(index+1)*80 if index+1<count else 0))
    image.write(0x16e74,'<I',0x400000);image.write(0x16e78,'<I',head)
    image.write(0x16e80,'<I',head);image.write(0x16e7c,'<I',tail)
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    image.write(0xe774,'<B',0)
    image.write(0x93b0,'<H',4)
    image.write(0x86c8,'<3H',0,12000,0);image.write(0x13444,'<i',400)
    image.write(0x13424,'<i',1000000>>8);image.write(0x13430,'<i',-300000>>8);image.write(0x1343c,'<i',1000000>>8)
    target=image.data+0x10f28 if dispenser>=6 else 0x310000
    if dispenser>=6:cpu.mem_write(target,struct.pack('<3i',1000000,-300000,1000000))
    cpu.mem_write(0x310000,struct.pack('<3i',*((1000000,-300000,1000000) if dispenser in (2,3,4) else (2000000,-200000,3000000))))
    for index in range(27):image.write(0x809c+48*index+16,'<2H',100+index*2,101+index*2)
    identities={};next_id=0;events=[]
    def constructor(cpu,*_):
        nonlocal next_id
        next_id+=1;identities[cpu.reg_read(r.UC_X86_REG_EAX)]=next_id
    cpu.hook_add(UC_HOOK_CODE,constructor,begin=image.native(0xa2d80),end=image.native(0xa2d80))
    def visual(im):
        handle=im.cpu.reg_read(r.UC_X86_REG_EAX)&65535
        events.extend((0,(handle-100)//2,(handle-100)%2));im.return_from()
    image.intercept(0xb52d4,'Capture shared weapon SSD entry-zero calls; no geometry is drawn.',visual)
    def launched(im):
        events.extend((1,identities[im.cpu.reg_read(r.UC_X86_REG_EDX)]));im.return_from()
    image.intercept(0x75998,'Record launch notifications without simulating aircraft threat pointers.',launched)
    def removed(im):
        events.extend((2,identities[im.cpu.reg_read(r.UC_X86_REG_EDX)]));im.return_from()
    image.intercept(0x759a4,'Record target-reference cleanup; targets are supplied fixed points.',removed)
    def contacts(im):
        pointer=struct.unpack('<I',cpu.mem_read(head+52,4))[0]
        while pointer!=tail:
            events.extend((3,identities[pointer],image.read(0x13476,'<H')[0]))
            pointer=struct.unpack('<I',cpu.mem_read(pointer+52,4))[0]
        im.return_from()
    image.intercept(0xa373c,'Capture the independently verified world-contact phase and list traversal order.',contacts)
    image.intercept(0x8b984,'Supply the test-authored store anchor.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x310200),im.return_from()))
    def anchor(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0]
        im.cpu.mem_write(pointer,struct.pack('<3i',1001000,-300500,1002000));im.return_from()
    image.intercept(0xb81de,'Supply the transformed mounted-store anchor; the render transform is separate.',anchor)
    for weapon in ((15,16,0) if dispenser==1 else range(27)):
        image.call(0xa2f84,eax=1000000,edx=(-300000)&0xffffffff,ebx=1000000,ecx=0,stack=(12000,0,400,weapon,0 if dispenser==4 else target,0x310100))
    result=[];warning=0
    for frame in range(frames):
        events.clear()
        if dispenser==5:cpu.mem_write(0x310000,struct.pack('<3i',2000000+frame*10000,-200000,3000000-frame*7000))
        if (2<=dispenser<=3 or dispenser>=6) and frame==2:
            image.write(0xe774,'<B',1)
            image.call(0xa353c if dispenser in (2,6) else 0xa3588,eax=target,edx=64 if dispenser<6 else {6:60,7:40,8:5}[dispenser])
            image.write(0xe774,'<B',0)
        image.call(0x71fd4,eax=elapsed,limit=10000000)
        values=[];pointer=struct.unpack('<I',cpu.mem_read(head+52,4))[0];bodies=[]
        while pointer!=tail:
            body=bytes(cpu.mem_read(pointer,80));callback=struct.unpack_from('<I',body,60)[0]
            function=callback-0x10000+0x70aa4 if callback else 0
            handle=struct.unpack_from('<H',body,46)[0]
            bodies.extend([identities[pointer],body[6],struct.unpack_from('<H',body,4)[0],KINDS[function],struct.unpack_from('<h',body,64)[0],*struct.unpack_from('<6i3Hihh',body,8),struct.unpack_from('<i',body,67)[0],(handle-100)%2,body[66],body[79]])
            pointer=struct.unpack_from('<I',body,52)[0]
        cached_weapon=cpu.mem_read(warning+6,1)[0] if warning else -1
        warning=image.call(0x70b4c)
        values=[len(bodies)//21,*bodies,*struct.unpack('<2H',cpu.mem_read(image.native(0xc9894),4)),cached_weapon,identities.get(warning,0),len(events),*events]
        digest=14695981039346656037
        for value in values:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        result.append(digest)
    return result


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    args=parser.parse_args();total=0
    for dispenser in range(9):
        for elapsed in (0,1,4,10,18,55):
            frames=128 if elapsed else 4
            capacity=98
            expected=original(args.data_dir,frames,elapsed,dispenser,capacity)
            result=subprocess.run([str(args.build/'projectile_runtime_probe'),str(args.data_dir)],input=f'{frames} {elapsed} {dispenser} {capacity}\n',text=True,capture_output=True,check=True)
            observed=[int(v) for v in result.stdout.split()]
            assert len(observed)==len(expected)
            for frame,(a,b) in enumerate(zip(observed,expected)):assert a==b,(dispenser,elapsed,frame,a,b)
            total+=frames
            print('Population',dispenser,'elapsed',elapsed,frames,'frames agree',flush=True)
    print(total,'native population frames agree, including launch/removal order, child releases, player/AI decoy strengths, exact shared RNG, retained/recycled HUD warning records and substep contact passes')


if __name__=='__main__':main()
