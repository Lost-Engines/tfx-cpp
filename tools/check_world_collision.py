#!/usr/bin/env python3
"""Compare complete native terrain-cell selection, wrapping, rotation and SSD contacts."""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from unicorn import x86_const as r
from native_reference import NativeReference


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    args=parser.parse_args()
    data_dir=args.research/'installs/cd_1994_09/TFX'
    text=(args.research/'analysis/maps/data.js').read_text()
    metadata=json.loads(text[text.index('=')+1:].strip().removesuffix(';'))
    by_name={name:obj for obj in metadata['objects'].values() for name in obj['names']}
    image=NativeReference(data_dir/'TFX.DAT')
    image.cpu.mem_map(0x300000,0x30000)
    image.cpu.mem_map(0x400000,0x20000)
    raw_by_name={}
    initial_by_name={}
    definition,instance=0x300000,0x310000
    selected=[]
    collisions=0
    choices=[]
    world=None
    def bind(im):
        im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EAX),struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EDX)))
        im.return_from()
    image.intercept(0xb4d3c,'Symbolic model binding; polygon drawing is outside this collision test.',bind)
    def resolve(im):
        handle=im.cpu.reg_read(r.UC_X86_REG_EAX)&65535
        index=handle-1
        x,row=divmod(index,200)
        z=199-row
        tile=world['tiles'][world['cells'][z*200+x]]
        name=choices[index]
        selected.append(name)
        state=bytearray(initial_by_name[name])
        state[2]|=(tile['rotation']>>14)<<5
        im.cpu.mem_write(definition,raw_by_name[name])
        im.cpu.mem_write(instance,bytes(state))
        im.write(0x1b250,'<I',definition)
        im.cpu.reg_write(r.UC_X86_REG_EAX,instance)
        im.return_from()
    image.intercept(0xc8568,'Resolve the selected grid handle to a fresh independently initialised SSD instance.',resolve)
    def collision(im):
        nonlocal collisions
        collisions+=1
        im.return_from()
    image.intercept(0xb7a30,'Record solid contacts; damage to the querying aircraft is outside the world query.',collision)
    for obj in metadata['objects'].values():
        if not obj['names']:continue
        raw=(args.research/'extracted/cd_1994_09/resources'/obj['path']).read_bytes()
        image.cpu.mem_write(definition,raw)
        image.cpu.mem_write(instance,bytes(65536))
        image.write(0x20b98,'<I',definition);image.write(0x20b9c,'<I',instance)
        image.write(0x20ba0,'<I',image.native(0xb6c84))
        image.call(0xb54dc,eax=definition+obj['entries'][0])
        initial=bytes(image.cpu.mem_read(instance,16+29*obj['part_count']+obj['custom_bytes']))
        for name in obj['names']:
            raw_by_name[name]=raw
            initial_by_name[name]=initial
    high=bytes((index+1)>>8 for index in range(40000))
    low=bytes((index+1)&255 for index in range(40000))
    image.cpu.mem_write(0x400000,high);image.cpu.mem_write(0x410000,low)
    image.write(0x18f40,'<I',0x400000);image.write(0x18f50,'<I',0x410000)
    image.write(0xaac8,'<I',0) # The requested world is already loaded, so b098c performs no host I/O.
    image.write(0xac3c,'<I',image.native(0xb7a30))
    image.write(0x20c4c,'<BB',1,1);image.write(0x20c46,'<H',0)
    rng=random.Random(0xb0cbc)
    total=0
    for name in ('yugos_n','colum_n','libya_d','somal_d'):
        world=next(w for w in metadata['environments'] if w['name']==name)
        image.cpu.mem_write(image.native(0x70aa4+0x47c82),struct.pack('<H',128 if 'night' in world['config'].lower().split() else 0))
        choices=[]
        low_seed,high_seed=0x5926,0x3141
        for x in range(200):
            for row in range(200):
                tile=world['tiles'][world['cells'][(199-row)*200+x]]
                value=high_seed+low_seed;high_seed=value&65535;low_seed=(low_seed+high_seed+(value>65535))&65535
                choices.append(tile['variants'][high_seed%len(tile['variants'])])
        requests=[]
        for n in range(1200):
            if n<200:
                x=rng.choice((-2049,-2048,-1,0,409599,409600,411648));z=rng.choice((-2049,-1,0,409599,409600,411648))
            else:x=rng.randrange(409600);z=rng.randrange(409600)
            y=rng.choice((-1200,-500,-100,-20,-10,-5,0,1,30))
            movement=[x+rng.randrange(-100,101),y+rng.randrange(-30,31),z+rng.randrange(-100,101),x,y,z]
            requests.append(movement)
        expected=[]
        for movement in requests:
            selected.clear();collisions=0
            image.write(0x20b80,'<6H',*[v&65535 for v in movement])
            for at,fmt,value in [(0xabe8,'<B',0),(0xabea,'<B',0),(0xabf2,'<h',0),(0xabec,'<h',-1),(0xabee,'<h',0)]:image.write(at,fmt,value)
            x,y,z=movement[3:]
            image.call(0xb0cbc,eax=0,edx=x&0xffffffff,ebx=y&0xffffffff,ecx=z&0xffffffff,stack=(0,))
            expected.append([collisions,image.read(0xabe8,'<B')[0],image.read(0xabea,'<B')[0],image.read(0xabf2,'<h')[0],image.read(0xabec,'<h')[0],image.read(0xabee,'<h')[0]])
        result=subprocess.run([str(args.build/'world_probe'),str(data_dir),name],input=''.join(' '.join(map(str,row))+'\n' for row in requests),text=True,capture_output=True,check=True)
        actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()]
        assert len(actual)==len(expected)
        for i,(a,b) in enumerate(zip(actual,expected)):
            assert a==b,(name,i,requests[i],a,b)
        total+=len(expected)
        print(name,len(expected),'native terrain queries agree',flush=True)
    print(total,'native world collision queries passed, including map seams and all quarter turns')


if __name__=='__main__':main()
