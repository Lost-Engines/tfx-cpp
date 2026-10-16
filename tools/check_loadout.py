#!/usr/bin/env python3
"""Compare default fits, both pylon selectors and player store release with DOS 2.05."""
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
    args=parser.parse_args();rng=random.Random(0x8b9c4)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    image.write(0xa3f4,'<h',-1) # Absent optional output device: execute its native return path.
    for file in (0xa4f10,0xb52d4):image.intercept(file,'Sound output and player SSD bay-open notification; neither changes pylon inventory.',lambda im:im.return_from())
    image.write(0xac74,'<I',image.native(0x75954)) # Empty output callback; the native caller removes its four arguments.
    image.intercept(0xb1334,'Supply Arcade/simulator configuration values at the release boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300100 if im.cpu.reg_read(r.UC_X86_REG_EAX)==im.data+0x2148 else 0x300104),im.return_from()))
    shots=[]
    def release(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP)
        heading,roll,speed,weapon,target,owner=struct.unpack('<6I',im.cpu.mem_read(sp+4,24))
        assert target==0x300600 and owner==im.data+0x10f28
        xyz=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]
        shots.extend([*xyz,im.cpu.reg_read(r.UC_X86_REG_ECX)&65535,heading&65535,roll&65535,struct.unpack('<i',struct.pack('<I',speed))[0],weapon]);im.return_from(stack_bytes=24)
    image.intercept(0xa2f84,'Capture released store geometry and type; projectile construction is checked independently.',release)
    model_base=image.native(0x70aa4+0x47c94)
    def inventory():
        values=[]
        for slot in range(10):
            values.extend([*image.read(0x13374+slot*2,'<2B'),int(struct.unpack('<H',image.cpu.mem_read(model_base+slot*2,2))[0]!=65535)])
        return values
    total=0;fixtures=[]
    for synthetic in (False,True):
        if synthetic:
            image.write(0x809c+255*48+20,'<B',6);image.write(0x809c+255*48+29,'<B',7)
            for plane,base in enumerate((0x7dd0,0x7ec0,0x7e48)):
                for fit in range(6):image.write(base+fit*10,'<5h',*[(plane*7+fit*3+pair)%24-1 for pair in range(5)])
            for index in range(27):
                image.write(0x809c+index*48+20,'<B',6 if index%3==2 else index%2)
                image.write(0x809c+index*48+29,'<B',(index*7)%15)
            for plane,base in enumerate((0x8654,0x8618,0x85dc)):
                for slot in range(10):image.write(base+slot*6,'<3h',-800+slot*200,200+plane*128,slot*64)
        rows=[];expected=[]
        image.write(0x132a8,'<27h',*[100+i for i in range(27)])
        for plane,count in enumerate((6,6,6) if synthetic else (12,6,12)):
            for fit in range(count):
                image.write(0x11b2a,'<H',plane);image.write(0x11b40,'<B',fit)
                image.call(0x8978c)
                rows.append(['D',plane,fit]);expected.append(inventory())
        for case in range(4096 if not synthetic else 2048):
            command='F' if case%3==0 else 'S';plane=case%3;selected=rng.randrange(-1,11) if command=='S' else rng.randrange(-1,10)
            gun_role=rng.choice((0,1,6));guns=rng.randrange(2)
            stores=[(rng.randrange(27) if rng.randrange(4) else 255,rng.randrange(3)) for _ in range(10)]+[(0,0)]
            stores=[(w,0 if w==255 else count) for w,count in stores]
            if command=='F' and selected>=0:stores[selected]=(rng.randrange(27),rng.randrange(3))
            row=[command,plane,selected,gun_role,guns,*[v for pair in stores for v in pair]]
            image.write(0x11b2a,'<H',plane);image.write(0x93b0,'<h',selected);image.write(0x7140,'<B',int(not guns));image.write(0x16e98,'<h',-1)
            image.write(0x809c+20,'<B',gun_role)
            for slot,(weapon,count) in enumerate(stores):image.write(0x13374+slot*2,'<2B',weapon,count)
            image.cpu.mem_write(model_base,struct.pack('<10H',*[100+i for i in range(10)]))
            image.write(0x11108,'<I',111);image.write(0x8840,'<I',222);image.write(0x135c8,'<I',333);image.write(0x135d0,'<I',0x300600)
            shots.clear()
            if command=='S':
                role=rng.choice((0,1,6));different=rng.randrange(2);row.extend([role,different])
                result=image.call(0x8b9c4 if different else 0x8bba0,eax=role)
                image.write(0x93b0,'<H',result&65535)
                prefix=[]
            else:
                flags=0 if case%2 else rng.randrange(16);position=[rng.randrange(-20000000,20000001) for _ in range(3)];angles=[rng.randrange(65536) for _ in range(3)];speed=rng.randrange(-32768,32768)
                row.extend([flags,*position,*angles,speed])
                image.write(0x12c04,'<H',int(bool(flags&1)));image.write(0x86ce,'<B',int(bool(flags&2)));image.write(0xabe9,'<B',int(bool(flags&4)));image.write(0x9170,'<H',0)
                image.cpu.mem_write(0x300100,struct.pack('<2I',int(bool(flags&8)),0))
                for address,value in zip((0x13424,0x13430,0x1343c),position):image.write(address,'<i',value)
                image.write(0x86c8,'<3H',*angles);image.write(0x13444,'<i',speed)
                image.call(0x8bd8c)
                prefix=[int(bool(shots)),*shots]
            tracking=[image.read(a,'<I')[0] for a in (0x8840,0x135c8,0x135d0)]
            assert all(tracking) or not any(tracking),tracking
            rows.append(row);expected.append([*prefix,image.read(0x93b0,'<h')[0],int(image.read(0x7140,'<B')[0]==0),image.read(0x16e98,'<h')[0],int(image.read(0x11108,'<I')[0]==0),int(not any(tracking)),*inventory()])
        output=subprocess.run([str(args.build/'loadout_probe'),'--synthetic' if synthetic else str(args.data_dir)],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
        actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()]
        assert len(actual)==len(expected),(len(actual),len(expected))
        for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(synthetic,i,rows[i],a,b)
        if synthetic:
            for row,values in zip(rows,expected):
                digest=14695981039346656037
                for value in values:
                    for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
                fixtures.append(' '.join(map(str,row+[digest]))+'\n')
        total+=len(rows);print(len(rows),'synthetic' if synthetic else 'retail','native pylon cases agree',flush=True)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(fixtures));subprocess.run([str(args.build/'loadout_probe'),'--check',str(args.save_fixture)],check=True)
    print(total,'default fits, type changes, automatic pylon advances and release states verified')


if __name__=='__main__':main()
