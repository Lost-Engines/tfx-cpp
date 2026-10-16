#!/usr/bin/env python3
"""Compare native keyboard cannon gating, ammunition, muzzles and random effects."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args();rng=random.Random(0x86898)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    image.write(0x1b23c,'<I',0x300000)
    # Player physics is a supplied boundary; cannon reads the resulting pose and system fields below.
    image.write(0x12bcc,'<I',image.native(0x75954))
    for address in (0x862f4,0x86458,0x838dc,0x83970,0x86820):image.intercept(address,'Unrelated keyboard/menu/camera acquisition; Space and the weapon eligibility fields are supplied.',lambda im:im.return_from())
    image.intercept(0xb1334,'Supply the ordinary Arcade/training configuration value.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300100),im.return_from()))
    image.intercept(0xa4ef8,'Cannon sound output does not change ammunition or release geometry.',lambda im:im.return_from())
    image.write(0xa3f4,'<h',-1) # Optional external output device is absent; its native callback executes and returns normally.
    shots=[]
    def release(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP)
        heading,roll,speed,weapon,target,owner=struct.unpack('<6I',im.cpu.mem_read(sp+4,24))
        assert target==0 and owner==im.data+0x10f28
        position=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]
        shots.extend([*position,im.cpu.reg_read(r.UC_X86_REG_ECX)&65535,heading&65535,roll&65535,struct.unpack('<i',struct.pack('<I',speed))[0],weapon]);im.return_from(stack_bytes=24)
    image.intercept(0xa2f84,'Record cannon releases; the projectile constructor/population has independent full native comparisons.',release)
    fixtures=[];total=0
    for synthetic in (False,True):
        if synthetic:image.cpu.mem_write(image.data+0x8690,struct.pack('<6h',192,640,-2048,-192,640,-2048))
        rows=[];expected=[]
        for case in range(4096 if not synthetic else 1024):
            plane=case%3;flags=15 if case%2 else rng.randrange(512)
            ammo=rng.choice((-1,0,1,9,10,20,1760));barrel=case%2
            position=[rng.randrange(-20000000,20000001) for _ in range(3)]
            angles=[rng.randrange(65536) for _ in range(3)];speed=rng.randrange(-32768,32768)
            row=[plane,flags,ammo,barrel,*position,*angles,speed];rows.append(row)
            image.cpu.mem_write(0x300039,bytes([int(bool(flags&1))]));image.write(0x7140,'<B',int(not(flags&2)))
            image.write(0x11b2a,'<H',plane);image.write(0x16e9a,'<h',ammo);image.write(0x16e96,'<H',barrel)
            # These first two availability checks really read FLP and COM, respectively.
            for address,bit,fmt in ((0x7d71,4,'<B'),(0x7d70,8,'<B'),(0x13b04,16,'<B'),(0xabe9,32,'<B'),(0x12c04,64,'<H'),(0x86ce,128,'<B'),(0x8d3a,256,'<H')):image.write(address,fmt,int(bool(flags&bit)))
            for address,value in zip((0x13424,0x13430,0x1343c),position):image.write(address,'<i',value)
            image.write(0x86c8,'<3H',*angles);image.write(0x13444,'<i',speed)
            image.cpu.mem_write(image.native(0xc9894),struct.pack('<2H',0x5926,0x3141))
            shots.clear();image.call(0x86898,limit=300000)
            expected.append([image.read(0x16e9a,'<h')[0],image.read(0x16e96,'<H')[0],*struct.unpack('<2H',image.cpu.mem_read(image.native(0xc9894),4)),int(bool(shots)),*shots])
        result=subprocess.run([str(args.build/'cannon_probe'),'--synthetic' if synthetic else str(args.data_dir)],input=''.join(' '.join(map(str,row))+'\n' for row in rows),text=True,capture_output=True,check=True)
        actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()]
        assert len(actual)==len(expected)
        for index,(a,b) in enumerate(zip(actual,expected)):assert a==b,(synthetic,index,rows[index],a,b)
        if synthetic:
            for row,values in zip(rows,expected):
                digest=14695981039346656037
                for value in values:
                    for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
                fixtures.append(' '.join(map(str,row+[digest]))+'\n')
        total+=len(rows);print(len(rows),'synthetic' if synthetic else 'retail-mount','native keyboard cannon cases agree',flush=True)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(fixtures))
        subprocess.run([str(args.build/'cannon_probe'),'--check',str(args.save_fixture)],check=True)
    print(total,'native keyboard cannon states verified')


if __name__=='__main__':main()
