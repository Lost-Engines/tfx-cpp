#!/usr/bin/env python3
"""Check native air/mobile hit credit and ordering with supplied collision outcomes."""
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
    args=parser.parse_args();rng=random.Random(0x7846d)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    image.intercept(0xc8568,'Resolve supplied actor SSD; its native destroyed-flag reader executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300500),im.return_from()))
    def contact(im):im.cpu.mem_write(0x300502,bytes([16]));im.return_from()
    image.intercept(0xb76a8,'Supply a newly fatal swept contact; world/SSD collision is independently checked.',contact)
    actor_type=[0]
    image.intercept(0xb7a3c,'Supply the victim definition type used by the authored mission filter.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,actor_type[0]&0xffffffff),im.return_from()))
    image.intercept(0x78274,'Record the later fatal-aircraft boundary; its random/ejection/retirement logic is independently checked.',lambda im:im.return_from())
    image.intercept(0xb1334,'Supply ordinary permission/Arcade/training eligibility for aircraft credit.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300600),im.return_from()))
    for address in (0xa5a9c,0x81254):image.intercept(address,'Radio/music and orders-warning output do not change the counters under comparison.',lambda im:im.return_from())
    image.write(0xac74,'<I',image.native(0x75954)) # Absent sound output; caller cleans its stack.
    offsets=(0x5c14,0x5c34,0x5c38,0x5c24,0x5c28,0x5c2c)
    rows=[];expected=[]
    for case in range(4096):
        surface=case%3==0;hostile=case%2;player=rng.randrange(2);authorised=rng.randrange(2);kind=rng.choice((-1,0,1,10,30,50,63));filter=rng.choice((-1,0,1,10,30,50,63));low=rng.randrange(65536);high=rng.randrange(65536);violations=rng.choice((-32768,0,1,32767))
        counters=[rng.choice((-2147483648,-1,0,1,2147483647)) for _ in offsets];rows.append([int(surface),hostile,player,authorised,kind,filter,low,high,violations,*counters]);actor_type[0]=kind
        for base in (0x11034,0x10f6c,0x128c8):image.write(base,'<50I',*([0]*50))
        image.write(0x128c8 if surface else 0x11034 if hostile else 0x10f6c,'<I',0x300300)
        image.cpu.mem_write(0x300300,bytes(128));image.cpu.mem_write(0x300502,bytes([0]))
        image.cpu.mem_write(0x300324 if surface else 0x30032a,struct.pack('<H',1))
        if surface:image.cpu.mem_write(0x30032e,struct.pack('<H',0x200 if hostile else 0))
        for offset,val in zip(offsets,counters):image.write(offset,'<i',val)
        image.write(0x11b28,'<h',filter);image.write(0x11b2c,'<h',filter);image.write(0x10f20,'<I',0x300100);image.write(0x10f24,'<I',image.data+0x10f28 if player else 0)
        image.cpu.mem_write(0x300126,struct.pack('<i',256));image.write(0x13476,'<H',4);image.write(0xe75c,'<h',violations);image.write(0xe781,'<B',0);image.write(0x11104,'<I',0);image.write(0x11108,'<I',0)
        image.cpu.mem_write(0x300600,struct.pack('<I',authorised));image.cpu.mem_write(image.native(0xc9894),struct.pack('<2H',low,high))
        image.call(0x7c418 if surface else 0x782f8 if hostile else 0x784d0)
        new_random=struct.unpack('<2H',image.cpu.mem_read(image.native(0xc9894),4))
        cue=(0x46 if new_random[1]&1 else 0x22) if not surface and hostile and player else 0
        expected.append([*[image.read(offset,'<i')[0] for offset in offsets],image.read(0xe75c,'<h')[0],*new_random,cue,int(not hostile)])
    output=subprocess.run([str(args.build/'credit_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),text=True,capture_output=True,check=True)
    actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i],a,b)
    if args.save_fixture:
        lines=[]
        for row,values in zip(rows,expected):
            digest=14695981039346656037
            for value in values:
                for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            lines.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(lines));subprocess.run([str(args.build/'credit_probe'),str(args.save_fixture)],check=True)
    print('4096 native aircraft/mobile credit cases agree: type filters, permission, ownership, random order, signed counters and violations')


if __name__=='__main__':main()
