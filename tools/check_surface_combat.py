#!/usr/bin/env python3
"""Compare surface acquisition and launch requests with the original 2.05 code.

Original targeting, enumerators, bearing, firing chance and player shot limit
execute. The projectile constructor and terrain-presence lookup are boundaries;
projectile motion/contacts and terrain SSD execution have separate comparisons.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference


def signed(value):return struct.unpack('<i',struct.pack('<I',value&0xffffffff))[0]


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args();rng=random.Random(0x7be44)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,0x40000)
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    launches=[];target_status=0
    def launch(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);yaw,roll,speed,weapon,target,owner=struct.unpack('<6I',im.cpu.mem_read(sp+4,24))
        assert owner==0x320000
        actor=100 if target==im.data+0x10f28 else 101 if 0x300000<=target<0x301000 else (target-0x301000)//128
        values=[weapon,*[signed(im.cpu.reg_read(reg)) for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)],im.cpu.reg_read(r.UC_X86_REG_ECX)&65535,yaw&65535,roll&65535,signed(speed),actor,*struct.unpack('<3i',im.cpu.mem_read(target,12))]
        launches.append(values);im.return_from(24)
    image.intercept(0xa2f84,'Record native weapon construction arguments before allocation; complete projectile execution is compared separately.',launch)
    image.intercept(0xb0d80,'Supply whether the authored terrain cell exists; terrain lookup has its own native comparison.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,1 if target_status else 65535),im.return_from()))
    image.intercept(0xb6e88,'Supply whether the selected terrain SSD is already destroyed; its damage execution is separately verified.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,int(target_status==1)),im.return_from()))
    rows=[];expected=[];total=0;shots=0
    for case in range(4096):
        command='G' if case%4==0 else 'R' if case%8==2 else 'N';side=case%4;range_=rng.choice((0,1,2,8,20,50,65535));weapon=rng.randrange(27);limit=rng.choice((0,1,2,255));used=rng.choice((0,1,2,254,255));low=rng.randrange(65536);high=rng.randrange(65536);plane=case%3;steps=rng.choice((1,16,64));position=[rng.randrange(-150000000,150000001),rng.randrange(-4000000,1),rng.randrange(-150000000,150000001)];speed=rng.randrange(-2147483648,2147483648)
        radius=signed(range_*5280*32);offset=rng.choice((radius,radius//8,0,300000,-300000));player=[signed(position[0]+offset),signed(position[1]+rng.choice((0,offset))),position[2]];contacts=[]
        image.write(0x10f6c,'<50I',*([0]*50));image.write(0x11034,'<50I',*([0]*50))
        for actor in rng.sample(range(100),rng.randrange(1,25)):
            target=[signed(position[0]+rng.randrange(-3000000,3000001)),rng.randrange(-4000000,1),signed(position[2]+rng.randrange(-3000000,3000001))];flags=rng.choice((0,8,128,256,384));contacts.append([actor,*target,flags]);pointer=0x301000+actor*128
            image.cpu.mem_write(pointer,bytes(80));image.cpu.mem_write(pointer,struct.pack('<3i',*target));image.cpu.mem_write(pointer+66,struct.pack('<H',flags));image.write((0x11034 if actor<50 else 0x10f6c)+(actor%50)*4,'<I',pointer)
        if command=='G':player=[rng.randrange(-32768,32768),0,rng.randrange(-32768,32768)];steps=1
        row=[command,side,range_,weapon,limit,used,low,high,plane,steps,*position,speed,*player,len(contacts),*[v for contact in contacts for v in contact]]
        profile=bytearray(46);profile[31]=side;struct.pack_into('<HBB',profile,42,range_,weapon,limit);image.cpu.mem_write(0x330000,bytes(profile));state=bytearray(49);struct.pack_into('<3i',state,0,*position);struct.pack_into('<i',state,18,speed);struct.pack_into('<II',state,38,0x300000,0x330000);state[46]=used;image.cpu.mem_write(0x320000,bytes(state))
        image.write(0x11b2a,'<H',plane);image.write(0x10f28,'<3i',*player);image.cpu.mem_write(image.native(0xc9894),struct.pack('<2H',low,high));digest=14695981039346656037
        target_status=2 if command=='R' else plane
        body=bytearray(19);body[0]=10;struct.pack_into('<2h',body,1,player[0] if command=='G' else 0,player[2] if command=='G' else 0);struct.pack_into('<H',body,17,weapon);image.cpu.mem_write(0x300000,bytes(body))
        if command=='R':
            cell=[rng.randrange(200),rng.randrange(200)];body=bytearray(13);body[0]=16
            body+=bytes([10])+struct.pack('<2h',*cell)+bytes(12)+struct.pack('<H',weapon)
            body+=bytes([2])+struct.pack('<3h',*cell,0)+bytes([0]);steps=128;row[9]=steps;row.append(body.hex());image.cpu.mem_write(0x300000,bytes(body))
        for _ in range(steps):
            launches.clear();image.call(0x7bee8 if command=='G' else 0x7c2bc if command=='R' else 0x7be44,eax=0x320000)
            a,b=struct.unpack('<2H',image.cpu.mem_read(image.native(0xc9894),4));values=[a,b,image.cpu.mem_read(0x320000+46,1)[0],len(launches),*[v for launch in launches for v in launch]]
            for value in values:
                for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            total+=1;shots+=len(launches)
        rows.append(row);expected.append(digest)
    result=subprocess.run([str(args.build/'surface_combat_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[int(v) for v in result.stdout.split()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i][:20],a,b)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(' '.join(map(str,row+[digest]))+'\n' for i,(row,digest) in enumerate(zip(rows,expected)) if i%8 in (0,1,2)))
        subprocess.run([str(args.build/'surface_combat_probe'),str(args.save_fixture)],check=True)
    print(len(rows),'surface combat scenarios;',total,'native updates and',shots,'launch requests agree')


if __name__=='__main__':main()
