#!/usr/bin/env python3
"""Execute original projectile constructors and complete timed motion sequences.

Guidance targets and player/store-anchor inputs are supplied; SSD events and
child releases are captured. World contacts, proximity fuses and damage remain
separate integration boundaries. No game files are modified.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

CALLBACKS=[0,0xa4380,0xa4414,0xa422c,0xa42c8,0xa3b6c,0xa3d70,0xa3fd8,0xa3f14,0xa4080,0xa41a0,0xa3af0,0xa42bc]
KINDS={v:i for i,v in enumerate(CALLBACKS)}


def original(data_dir,row,synthetic):
    weapon,ticks,elapsed,owned,target_player,invulnerable,decoys,distance,x,y,z,pitch,heading,roll,speed,tx,ty,tz,category,motion=row
    image=NativeReference(data_dir/'TFX.DAT');cpu=image.cpu
    cpu.mem_map(0x300000,0x40000)
    address=0x300000;target=image.data+0x10f28 if target_player else 0x310000
    cpu.mem_write(target,struct.pack('<3i',tx,ty,tz))
    table=0x809c+weapon*48
    image.write(table+16,'<2H',10,11)
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    image.write(0x13476,'<H',elapsed);image.write(0xabe9,'<B',invulnerable);image.write(0x12f29,'<B',decoys)
    image.write(0x86c8,'<3H',pitch,heading,roll);image.write(0x13444,'<i',speed)
    image.write(0x13424,'<i',x>>8);image.write(0x13430,'<i',y>>8);image.write(0x1343c,'<i',z>>8)
    if synthetic:
        image.write(table+29,'<B',category);image.write(table+35,'<i',10000);image.write(table+41,'<h',300)
        stages=[(25,motion),(80,3),(200,5),(0,0)]
        cpu.mem_write(0x320000,b''.join(struct.pack('<HI',duration,image.native(CALLBACKS[kind]) if kind else 0) for duration,kind in stages))
        image.write(table,'<I',0x320000)
    events=[];children=[]
    def visual(im):
        events.append(im.cpu.reg_read(r.UC_X86_REG_EAX));im.return_from()
    image.intercept(0xb52d4,'Capture SSD entry 0; local visual state does not feed motion.',visual)
    image.intercept(0x75998,'Target threat registration is outside the isolated projectile-motion sequence.',lambda im:im.return_from())
    image.intercept(0x8b984,'Supply the mounted-store anchor; its transform is a declared external input.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x310200),im.return_from()))
    def anchor(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0]
        im.cpu.mem_write(pointer,struct.pack('<3i',x+1000,y-500,z+2000));im.return_from()
    image.intercept(0xb81de,'Supply the already-transformed mounted-store anchor without drawing.',anchor)
    image.intercept(0x7d208,'Supply distance to player for the ECM decision; no player flight is simulated.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,distance),im.return_from(stack_bytes=4)))
    def release(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP)
        h,b,s,w,t,o=struct.unpack('<6I',im.cpu.mem_read(sp+4,24))
        pos=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]
        p=im.cpu.reg_read(r.UC_X86_REG_ECX)&65535
        children.extend([*pos,p,h&65535,b&65535,struct.unpack('<i',struct.pack('<I',s))[0],w]);im.return_from(stack_bytes=24)
    image.intercept(0xa2f84,'Capture dispenser releases without recursively running another projectile population.',release)
    image.call(0xa2d80,eax=address,edx=x&0xffffffff,ebx=y&0xffffffff,ecx=z&0xffffffff,stack=(pitch,heading,roll,speed,weapon,target,image.data+0x10f28 if owned else 0x310100))
    result=[]
    for tick in range(ticks):
        events.clear();children.clear()
        body=bytes(cpu.mem_read(address,80))
        if struct.unpack_from('<H',body,64)[0]:
            cpu.mem_write(address+20,body[8:20])
            function=struct.unpack_from('<I',body,60)[0]-0x10000+0x70aa4
            image.call(function,eax=address,limit=300000)
        body=bytes(cpu.mem_read(address,80))
        callback=struct.unpack_from('<I',body,60)[0]
        function=callback-0x10000+0x70aa4 if callback else 0
        values=[struct.unpack_from('<H',body,4)[0],KINDS[function],struct.unpack_from('<h',body,64)[0],*struct.unpack_from('<6i3Hihh',body,8),struct.unpack_from('<i',body,67)[0],weapon,int(struct.unpack_from('<H',body,46)[0]==11),int(bool(events)),len(children)//8,*children]
        digest=14695981039346656037
        for value in values:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        result.append((digest,values))
    return result


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args()
    rng=random.Random(0xa2d80);total=0;fixtures=[]
    for synthetic in (False,True):
        rows=[];expected=[]
        for case in range(96 if synthetic else 108):
            weapon=case%27
            row=[weapon,256,case%10+1,case%2,(case//2)%2,(case//4)%2,(case//8)%2,5000,
                 rng.randrange(-10000000,10000001),rng.randrange(-2000000,-100000),rng.randrange(-10000000,10000001),
                 rng.randrange(65536),rng.randrange(65536),rng.randrange(65536),rng.randrange(100,1000),
                 rng.randrange(-10000000,10000001),rng.randrange(-2000000,0),rng.randrange(-10000000,10000001),
                 (1,3,13,14)[case%4],case%11+1]
            rows.append(row);expected.append(original(args.data_dir,row,synthetic))
        text=''.join(' '.join(map(str,row))+'\n' for row in rows)
        command=[str(args.build/'projectile_probe'),'--synthetic' if synthetic else str(args.data_dir)]
        result=subprocess.run(command,input=text,text=True,capture_output=True,check=True)
        observed=[int(v) for v in result.stdout.split()];cursor=0
        for index,(row,samples) in enumerate(zip(rows,expected)):
            for tick,(digest,values) in enumerate(samples):
                if observed[cursor]!=digest:
                    detail=subprocess.run([*command,'--verbose'],input=' '.join(map(str,row))+'\n',text=True,capture_output=True,check=True)
                    actual=[int(v) for v in detail.stdout.splitlines()[tick].split()]
                    first=next((i for i,(a,b) in enumerate(zip(actual,values)) if a!=b),'length')
                    raise AssertionError(('synthetic',synthetic,'case',index,'tick',tick,'first',first,'C++',actual,'native',values))
                cursor+=1
            if synthetic:
                digest=14695981039346656037
                for sample,_ in samples:
                    for byte in struct.pack('<Q',sample):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
                fixtures.append(' '.join(map(str,row+[digest]))+'\n')
        assert cursor==len(observed)
        total+=cursor
        print(len(rows),'synthetic' if synthetic else 'retail','sequences;',cursor,'native projectile updates agree',flush=True)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(fixtures))
        subprocess.run([str(args.build/'projectile_probe'),'--check',str(args.save_fixture)],check=True)
    print(total,'original projectile state transitions verified; world contacts remain separate')


if __name__=='__main__':main()
