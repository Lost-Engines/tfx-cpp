#!/usr/bin/env python3
"""Verify persistent native radar scans/cycling and aircraft seeker acquisition.

Projection is supplied at its native graphics boundary; this is not a proof of
camera projection, complete radar drawing, or ground/designator controllers.
"""
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
    args=parser.parse_args();rng=random.Random(0x93328)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,0x10000)
    for file in (0x81198,0xa4e80,0xa5a9c,0xa4fb4,0xa5008):image.intercept(file,'Radio/lock-tone output; no aircraft/radar/reticle state changes at this output boundary.',lambda im:im.return_from())
    projected=[160,100]
    def project(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);address=struct.unpack('<I',im.cpu.mem_read(sp+16,4))[0]
        im.cpu.mem_write(address,struct.pack('<2h',*projected));im.return_from(stack_bytes=16)
    image.intercept(0xc5759,'Supply screen projection at the graphics boundary; lock eligibility and reticle movement execute unmodified.',project)
    image.cpu.mem_write(image.native(0x70aa4+0x47736),struct.pack('<2h',160,100))
    image.write(0x76c8,'<I',image.data+0x12f34);image.write(0x76cc,'<I',image.data+0x12f84);image.call(0x82744)
    for base,start in ((0x11034,0),(0x10f6c,8)):
        image.write(base,'<50I',*[0x301000+(start+i)*128 if i<8 else 0 for i in range(50)])
    ptr_to_id={0x301000+i*128:i for i in range(16)}
    rows=[];expected=[]
    for frame in range(1024):
        player=[(frame*83)%50000-25000,-1000,(frame*97)%50000-25000]
        actors=[]
        for pool in range(2):
            for i in reversed(range(8)):
                actor=pool*8+i;dx=rng.choice((-33659,-33000,-32999,-16499,0,16499,32999,33000,33659)) if frame%3==0 else rng.randrange(-40000,40001)
                dz=rng.randrange(-35000,35001);flags=256 if rng.randrange(7)==0 else rng.choice((0,1,8,128))
                pos=[(player[0]+dx)*256,-256000,(player[2]+dz)*256]
                actors.append([actor,*pos,flags]);address=0x301000+actor*128
                image.cpu.mem_write(address,struct.pack('<3i',*pos));image.cpu.mem_write(address+66,struct.pack('<H',flags))
        for addr,val in zip((0x13424,0x13430,0x1343c),player):image.write(addr,'<i',val)
        cycle=int(frame%11==0);image.call(0x836ac)
        if cycle:image.call(0x828b0)
        slots=image.read(image.read(0x76c8,'<I')[0]-image.data,'<20I');selected=image.read(0x11108,'<I')[0]
        rows.append(['R',*player,len(actors),cycle,*[v for actor in actors for v in actor]])
        expected.append([image.read(0x76d0,'<h')[0],ptr_to_id.get(selected,-1),*[ptr_to_id.get(p,-1) for p in slots]])
    for case in range(4096):
        flags=3 if case%3 else rng.randrange(128);category=rng.choice((0,1,2,4,5,6,9,10,14));role=rng.choice((0,1,6));klass=rng.randrange(4);ticks=rng.choice((0,1,4,10,55,30000,65535))
        minimum=rng.choice((0,100,1000));distance=rng.choice((3000,20000,65535,100000));position=[rng.randrange(-30000,30001),rng.randrange(-4000,0),rng.randrange(-30000,30001)];angles=[rng.randrange(65536),rng.randrange(65536)]
        if case%2:
            target=[position[0]*256,position[1]*256,(position[2]+rng.randrange(100,20000))*256];angles=[0,0]
        else:target=[rng.randrange(-100000,100001)*256,rng.randrange(-6000,0)*256,rng.randrange(-100000,100001)*256]
        target_heading=rng.randrange(65536);reticle=[rng.randrange(-1000,1001)*256,rng.randrange(-1000,1001)*256];projected[:]=[rng.randrange(-1000,1001),rng.randrange(-1000,1001)]
        lt=rng.choice((0,1,500,30000));at=rng.choice((-1,0,10,500));row=['L',flags,category,role,klass,ticks,minimum,distance,*position,*angles,*target,target_heading,*reticle,*projected,lt,at]
        image.write(0x93b0,'<h',0);image.write(0x13374,'<2B',1,1)
        for off,fmt,val in ((0x809c+48+20,'<B',role),(0x809c+48+29,'<B',category),(0x809c+48+33,'<h',minimum),(0x809c+48+35,'<i',distance),(0x7140,'<B',int(not(flags&16))),(0x12f26,'<B',int(bool(flags&32))),(0x13476,'<H',ticks)):image.write(off,fmt,val)
        for address,value in zip((0x13424,0x13430,0x1343c),position):image.write(address,'<i',value)
        image.write(0x86c8,'<3H',*angles,0);image.write(0x11108,'<I',0x300200 if flags&1 else 0)
        image.write(0x76c8,'<I',image.data+0x12f34);image.write(0x12f34,'<20I',0x300200 if flags&2 else 0,*([0]*19));image.write(0x76d0,'<h',0)
        image.cpu.mem_write(0x300200,struct.pack('<3i',*target));image.cpu.mem_write(0x30020e,struct.pack('<H',target_heading));image.cpu.mem_write(0x30023c,struct.pack('<I',0x300400));image.cpu.mem_write(0x30041f,bytes([klass]))
        for offset,bit in ((0x135c8,4),(0x135d0,8)):image.write(offset,'<I',0x300200 if flags&bit else 0)
        image.write(0x135c0,'<2i',*reticle);image.write(0x135cc,'<2h',11,12);image.write(0x135d4,'<2h',lt,at);image.write(0x8860,'<B',int(bool(flags&64)))
        image.call(0x93328)
        values=[int(bool(image.read(a,'<I')[0])) for a in (0x11108,0x135c8,0x135d0)]
        values.extend([*image.read(0x135c0,'<2i'),*image.read(0x135cc,'<2h'),*image.read(0x135d4,'<2h'),image.read(0x8860,'<B')[0]])
        rows.append(row);expected.append(values)
    result=subprocess.run([str(args.build/'sensors_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i],a,b)
    if args.save_fixture:
        fixtures=[]
        for row,values in zip(rows,expected):
            digest=14695981039346656037
            for value in values:
                for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            fixtures.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(fixtures));subprocess.run([str(args.build/'sensors_probe'),str(args.save_fixture)],check=True)
    print('1024 persistent radar frames and 4096 seeker acquisition/lock states agree with native execution')


if __name__=='__main__':main()
