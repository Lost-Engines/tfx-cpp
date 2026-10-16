#!/usr/bin/env python3
"""Compare native designator acquisition geometry and surface target selectors.

The un-locked designator's input/gimbal/camera prefix executes up to graphics
setup; its original ground intersection executes separately. No image drawing,
complete targeting session or rendered-image agreement is claimed. Locked camera
tracking and mobile selectors execute separately with declared input boundaries.
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
    args=parser.parse_args();rng=random.Random(0x93040)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,0x20000)
    image.write(0x1b23c,'<I',0x300000);image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    camera=[]
    def prefix_done(im):
        frame=im.cpu.reg_read(r.UC_X86_REG_EBP);camera[:]=struct.unpack('<3i',im.cpu.mem_read(frame-0x18,12))
        old_ebp,old_edx,old_ecx,old_ebx,destination=struct.unpack('<5I',im.cpu.mem_read(frame,20))
        for reg,val in ((r.UC_X86_REG_EBP,old_ebp),(r.UC_X86_REG_EDX,old_edx),(r.UC_X86_REG_ECX,old_ecx),(r.UC_X86_REG_EBX,old_ebx),(r.UC_X86_REG_ESP,frame+20),(r.UC_X86_REG_EIP,destination)):im.cpu.reg_write(reg,val)
    image.intercept(0x92ea1,'Stop after the complete un-locked gimbal/camera prefix, before graphics setup; ground intersection executes independently.',prefix_done)
    image.intercept(0x92b1f,'Stop the locked camera prefix before graphics; native bearing and camera motion execute.',prefix_done)
    types={}
    image.intercept(0xb7a3c,'Supply each surface SSD type; surface pool flags, selection and native distance calculations execute.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,types[im.cpu.reg_read(r.UC_X86_REG_EAX)&65535]&0xffffffff),im.return_from()))
    rows=[];expected=[]
    for case in range(8192):
        command='G' if case%2 else 'I';pitch=rng.randrange(65536);heading=rng.randrange(65536);zoom=rng.choice((0,1,2,4,8,16,255));position=[rng.randrange(-500000,500001),rng.randrange(-12000,1),rng.randrange(-500000,500001)];angles=[rng.randrange(65536),rng.randrange(65536)];plane=case%3;flags=rng.randrange(16)
        rows.append([command,pitch,heading,zoom,*position,*angles,plane,flags])
        for address,value in zip((0x13424,0x13430,0x1343c),position):image.write(address,'<i',value)
        if command=='G':
            image.write(0x8828,'<2H',pitch,heading);image.write(0x883c,'<B',zoom);image.write(0x8840,'<I',0);image.write(0x8844,'<i',0);image.write(0x884a,'<h',0);image.write(0x11b2a,'<H',plane);image.write(0x86c8,'<3H',*angles,0)
            image.cpu.mem_write(0x300000,bytes(256))
            for offset,bit in ((72,1),(80,2),(75,4),(77,8)):image.cpu.mem_write(0x300000+offset,bytes([int(bool(flags&bit))]))
            image.call(0x92c24);pitch,heading=image.read(0x8828,'<2H');zoom=image.read(0x883c,'<B')[0]
            prefix=[pitch,heading,zoom,*camera]
        else:prefix=[]
        image.call(0x93040,eax=pitch,edx=heading)
        expected.append([*prefix,image.read(0x882c,'<i')[0],0,image.read(0x135ac,'<i')[0]])
    for case in range(2048):
        zoom=rng.choice((0,1,4,10,255));player=[rng.randrange(-500000,500001),rng.randrange(-12000,0),rng.randrange(-500000,500001)];target=[rng.randrange(-200000000,200000000) for _ in range(3)]
        image.write(0x883c,'<B',zoom);image.write(0x135a0,'<3i',*target)
        for address,value in zip((0x13424,0x13430,0x1343c),player):image.write(address,'<i',value)
        image.call(0x92a34);pitch,heading=image.read(0x8828,'<2H');new_zoom=image.read(0x883c,'<B')[0]
        rows.append(['L',zoom,*player,*target]);expected.append([pitch,heading,new_zoom,*camera,*[v>>8 for v in target]])
    for case in range(4096):
        a=[rng.randrange(-2147483648,2147483648) for _ in range(3)];b=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
        if case%3==0:a=[rng.choice((-2147483648,0,2147483647)) for _ in range(3)];b=[0,0,0]
        for address,value in zip((0x13424,0x13430,0x1343c),a):image.write(address,'<i',value)
        image.cpu.mem_write(0x300900,struct.pack('<3i',*b));value=image.call(0x7d208,stack=(0x300900,))
        rows.append(['D',*a,*b]);expected.append([signed(value)])
    for case in range(2048):
        cursor=rng.randrange(-1,50);wanted=rng.randrange(64);side=rng.randrange(3);player=[rng.randrange(-500000,500001),rng.randrange(-12000,0),rng.randrange(-500000,500001)];allowed=rng.sample(range(64),rng.randrange(1,12));contacts=[]
        image.write(0x128c8,'<50I',*([0]*50));types.clear();image.write(0x5d88,'<h',cursor)
        for address,value in zip((0x13424,0x13430,0x1343c),player):image.write(address,'<i',value)
        for slot in rng.sample(range(50),rng.randrange(1,40)):
            position=[(player[0]+rng.randrange(-35000,35001))*256,-rng.randrange(1000)*256,(player[2]+rng.randrange(-35000,35001))*256];heading=rng.randrange(65536);allegiance=rng.randrange(3);flags=rng.choice((0,2,4,8,16,24));kind=rng.choice([wanted,*allowed,rng.randrange(64)])
            contacts.append([slot,*position,heading,allegiance,flags,kind]);pointer=0x301000+slot*128;profile=0x310000+slot*128;types[slot+1]=kind
            image.write(0x128c8+slot*4,'<I',pointer);image.cpu.mem_write(pointer,bytes(49));image.cpu.mem_write(pointer,struct.pack('<3i',*position));image.cpu.mem_write(pointer+14,struct.pack('<H',heading));image.cpu.mem_write(pointer+36,struct.pack('<H',slot+1));image.cpu.mem_write(pointer+42,struct.pack('<I',profile));image.cpu.mem_write(pointer+47,bytes([flags]));image.cpu.mem_write(profile+31,bytes([allegiance]))
        selected=image.call(0x7c828,eax=wanted,edx=side);new_cursor=image.read(0x5d88,'<h')[0]
        image.cpu.mem_write(0x300a00,struct.pack('<'+'h'*(len(allowed)+1),*allowed,-1));ship=image.call(0x7cb5c,eax=0x300a00)
        index=lambda pointer:(pointer-0x301000)//128 if pointer else -1
        rows.append(['T',cursor,wanted,side,*player,len(contacts),len(allowed),*[v for contact in contacts for v in contact],*allowed]);expected.append([index(selected),new_cursor,index(ship)])
    anchors={}
    def anchor(im):
        handle=im.cpu.reg_read(r.UC_X86_REG_EAX)&65535;index=im.cpu.reg_read(r.UC_X86_REG_EBX)&65535
        values=anchors[handle]
        if index<len(values):im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EDX),struct.pack('<3h',*values[index]))
        im.cpu.reg_write(r.UC_X86_REG_EAX,int(index<len(values)));im.return_from()
    image.intercept(0xb7b90,'Supply SSD box centres, separately compared with native enumeration; native mobile selection/distance/ordering execute.',anchor)
    for case in range(2048):
        limit=rng.choice((0,1,1000,10000,32767,-1));wanted=55;player=[rng.randrange(-200000000,200000000),0,rng.randrange(-200000000,200000000)];contacts=[]
        image.write(0x128c8,'<50I',*([0]*50));types.clear();anchors.clear()
        for slot in rng.sample(range(50),rng.randrange(1,25)):
            position=[signed(player[0]+rng.randrange(-3000000,3000001)),0,signed(player[2]+rng.randrange(-3000000,3000001))];heading=rng.randrange(65536);flags=rng.choice((0,2,4,8,16));kind=rng.choice((55,55,56));points=[tuple(rng.randrange(-32768,32768) for _ in range(3)) for _ in range(rng.randrange(6))]
            contacts.append([slot,*position,heading,0,flags,kind,len(points),*[v for point in points for v in point]]);pointer=0x301000+slot*128;types[slot+1]=kind;anchors[slot+1]=points
            image.write(0x128c8+slot*4,'<I',pointer);image.cpu.mem_write(pointer,bytes(49));image.cpu.mem_write(pointer,struct.pack('<3i',*position));image.cpu.mem_write(pointer+14,struct.pack('<H',heading));image.cpu.mem_write(pointer+36,struct.pack('<H',slot+1));image.cpu.mem_write(pointer+47,bytes([flags]))
        image.cpu.mem_write(0x300a00,struct.pack('<3i',*player));image.cpu.mem_write(0x300b00,bytes(6));value=image.call(0x7ca24,eax=0x300b00,edx=0x300a00,ebx=limit&0xffffffff,ecx=wanted)
        index=(value-0x301000)//128 if value else -1
        rows.append(['M',limit,wanted,0,*player,len(contacts),0,*[v for contact in contacts for v in contact]]);expected.append([index,*struct.unpack('<3h',image.cpu.mem_read(0x300b00,6))])
    output=subprocess.run([str(args.build/'ground_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i][:15],a,b)
    if args.save_fixture:
        lines=[]
        for index,(row,values) in enumerate(zip(rows,expected)):
            if index%8:continue
            digest=14695981039346656037
            for val in values:
                for byte in struct.pack('<I',val&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            lines.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(lines));subprocess.run([str(args.build/'ground_probe'),str(args.save_fixture)],check=True)
    print('8192 native designator/intersection cases, 2048 locked camera cases, 4096 wrapped distance estimates and 4096 surface target selections agree')


if __name__=='__main__':main()
