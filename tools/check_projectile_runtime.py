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


def original(data_dir,frames,elapsed,dispenser,capacity,frame_tail=False,recycle=False):
    image=NativeReference(data_dir/'TFX.DAT');cpu=image.cpu
    cpu.mem_map(0x300000,0x40000);cpu.mem_map(0x400000,0xa0000)
    head,tail=0x320000,0x320100
    cpu.mem_write(head+52,struct.pack('<I',tail));cpu.mem_write(tail+56,struct.pack('<I',head))
    frame_index=[0]
    count=capacity
    for index in range(count):cpu.mem_write(0x400000+index*80+52,struct.pack('<I',0x400000+(index+1)*80 if index+1<count else 0))
    image.write(0x16e74,'<I',0x400000);image.write(0x16e78,'<I',head)
    image.write(0x16e80,'<I',head);image.write(0x16e7c,'<I',tail)
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    image.write(0xe774,'<B',0)
    image.write(0x93b0,'<H',4)
    image.write(0x86c8,'<3H',0,12000,0);image.write(0x13444,'<i',400)
    image.write(0x13424,'<i',1000000>>8);image.write(0x13430,'<i',-300000>>8);image.write(0x1343c,'<i',1000000>>8)
    target=image.data+0x10f28 if 6<=dispenser<=8 else 0x310000
    if 6<=dispenser<=8:cpu.mem_write(target,struct.pack('<3i',1000000,-300000,1000000))
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
            if frame_tail and (frame_index[0]+identities[pointer])%7==0:cpu.mem_write(pointer+66,b'\x01')
            pointer=struct.unpack('<I',cpu.mem_read(pointer+52,4))[0]
        im.return_from()
    image.intercept(0xa373c,'Capture the independently verified world-contact phase and list traversal order.',contacts)
    image.intercept(0x75030,'Exclude the legacy non-TFX effect output: every retail TFX world disables this helper with environment flag 0x0001; synthetic zero flags suppress the other world consumers.',lambda im:im.return_from())
    image.intercept(0x8b984,'Supply the test-authored store anchor.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x310200),im.return_from()))
    def anchor(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0]
        im.cpu.mem_write(pointer,struct.pack('<3i',1001000,-300500,1002000));im.return_from()
    image.intercept(0xb81de,'Supply the transformed mounted-store anchor; the render transform is separate.',anchor)
    image.write(0x9170,'<H',int(dispenser==9))
    def launch_batch():
        for weapon in ((15,16,0) if dispenser==1 else range(27)):
            image.call(0xa2f84,eax=1000000,edx=(-300000)&0xffffffff,ebx=1000000,ecx=0,stack=(12000,0,400,weapon,0 if dispenser==4 else target,0x310100))
    launch_batch()
    image.write(0x9170,'<H',0)
    result=[];warning=0
    for frame in range(frames):
        frame_index[0]=frame
        events.clear()
        if recycle and frame and frame%9==0:
            image.write(0x9170,'<H',int(dispenser==9));launch_batch();image.write(0x9170,'<H',0)
        if dispenser==5:cpu.mem_write(0x310000,struct.pack('<3i',2000000+frame*10000,-200000,3000000-frame*7000))
        if (2<=dispenser<=3 or 6<=dispenser<=8) and frame==2:
            image.write(0xe774,'<B',1)
            image.call(0xa353c if dispenser in (2,6) else 0xa3588,eax=target,edx=64 if dispenser<6 else {6:60,7:40,8:5}[dispenser])
            image.write(0xe774,'<B',0)
        image.call(0x71fd4,eax=elapsed,limit=10000000)
        if frame_tail:image.call(0xa31a0)
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
    parser.add_argument('--frame-tail',action='store_true',help='supply deterministic swept-contact losses and execute original post-flip retirement')
    parser.add_argument('--jettison-only',action='store_true')
    parser.add_argument('--recycle',action='store_true',help='relaunch every nine frames into a bounded reused pool')
    parser.add_argument('--frames',type=int,default=128)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();total=0
    if not 1<=args.frames<=65536:parser.error('--frames must be between 1 and 65536')
    if args.recycle and not args.frame_tail:parser.error('--recycle needs --frame-tail for declared deterministic contacts')
    results=[]
    for dispenser in ([9] if args.jettison_only else [0,1,5,9] if args.recycle else range(10)):
        for elapsed in ((4,18) if args.recycle else (0,1,4,10,18,55)):
            frames=args.frames if elapsed else 4
            capacity=17 if args.recycle else 98
            print(f'Checking projectile pool: dispenser={dispenser} elapsed={elapsed} frames={frames} capacity={capacity}',flush=True)
            expected=original(args.data_dir,frames,elapsed,dispenser,capacity,args.frame_tail,args.recycle)
            result=subprocess.run([str(args.build/'projectile_runtime_probe'),str(args.data_dir),*(['--frame-tail']if args.frame_tail else []),*(['--recycle']if args.recycle else [])],input=f'{frames} {elapsed} {dispenser} {capacity}\n',text=True,capture_output=True,check=True)
            observed=[int(v) for v in result.stdout.split()]
            assert len(observed)==len(expected)
            for frame,(a,b) in enumerate(zip(observed,expected)):assert a==b,(dispenser,elapsed,frame,a,b)
            total+=frames
            results.append(dict(dispenser=dispenser,elapsed=elapsed,frames=frames,capacity=capacity))
            print('Population',dispenser,'elapsed',elapsed,frames,'frames agree',flush=True)
    print(total,'native population frames agree, including launch/removal order, child releases, player/AI decoy strengths, exact shared RNG, retained/recycled HUD warning records and substep contact passes')

    if args.report:
        import json
        args.report.write_text(json.dumps({'recycle':args.recycle,'cases':results,'total_frames':total,'matched':True},indent=2)+'\n')

if __name__=='__main__':main()
