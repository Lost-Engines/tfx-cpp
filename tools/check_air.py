#!/usr/bin/env python3
"""Compare aircraft waypoint/formation updates in a declared noncombat context."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from unicorn import x86_const as r
from native_reference import NativeReference


def dataset(path):
    text=path.read_text()
    return json.loads(text[text.index('=')+1:].strip().removesuffix(';'))


def original(data_dir,raw,profiles,ticks,intact,formation=None):
    image=NativeReference(data_dir/'TFX.DAT')
    image.cpu.mem_map(0x300000,0x50000)
    image.cpu.mem_write(0x300000,raw)
    heap=0x330000
    def allocate(im):
        nonlocal heap
        size=im.cpu.reg_read(r.UC_X86_REG_EAX)
        assert heap+size<0x350000
        im.cpu.reg_write(r.UC_X86_REG_EAX,heap);heap+=(size+15)&~15;im.return_from()
    image.intercept(0xc90ec,'Bounded allocation; native actor initialisation and formation copying execute unchanged.',allocate)
    image.intercept(0xb4d98,'Scenery resource boundary; each actor gets a synthetic handle.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,1),im.return_from()))
    image.intercept(0x75228,'Player route conversion is separately verified; no player autopilot is executed in this test.',lambda im:im.return_from())
    for index,profile in enumerate(profiles):
        address=0x320000+profile['offset']
        image.cpu.mem_write(address,bytes.fromhex(profile['hex']))
        image.write(0x127ec+index*4,'<I',address)
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    if formation is not None:image.cpu.mem_write(image.data+0x5984,formation)
    image.write(0x1347a,'<B',0)
    image.call(0x75690,eax=0x300000,limit=2000000)
    registry={}
    for base,start in [(0x11034,0),(0x10f6c,50)]:
        for slot in range(50):
            pointer=image.read(base+slot*4,'<I')[0]
            if pointer:registry[pointer]=start+slot
    requests=[]
    def scan(im):
        requests.append([registry[im.cpu.reg_read(r.UC_X86_REG_EAX)],0])
        im.cpu.reg_write(r.UC_X86_REG_EAX,0);im.return_from()
    image.intercept(0x76ba4,'Explicit no-air-combat-acquisition context; waypoint, formation and all numerical control execute normally.',scan)
    image.intercept(0xb0d80,'Supplied ground-target existence; world lookup has separate native checks.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,1 if intact else 65535),im.return_from()))
    image.intercept(0xb6e88,'All supplied ground targets are intact.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
    def identity(im):
        pool=0x10f6c if im.read(0x5a10,'<H')[0]==1 else 0x11034
        return im.read(0x11118,'<h')[0]+(50 if pool==0x10f6c else 0)
    def visual(im):
        requests.append([identity(im),1,im.cpu.reg_read(r.UC_X86_REG_EDX)&65535]);im.return_from()
    image.intercept(0xb52d4,'Record SSD requests without drawing or mutating the independently tested instance VM.',visual)
    def radio(im):
        pointer=im.cpu.reg_read(r.UC_X86_REG_EAX)
        text=bytes(im.cpu.mem_read(pointer,40)).split(b'\0',1)[0]
        requests.append([identity(im),2,len(text),*text]);im.return_from()
    image.intercept(0x81198,'Record authored radio delivery; display and speech are separate consumers.',radio)
    def weapon(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP)
        heading,roll,speed,weapon,target,owner=struct.unpack('<6I',im.cpu.mem_read(sp+4,24))
        position=[struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]
        pitch=im.cpu.reg_read(r.UC_X86_REG_ECX)&65535
        speed=struct.unpack('<h',struct.pack('<H',speed&65535))[0]
        requests.append([registry[owner],3,*position,pitch,heading&65535,roll&65535,speed,weapon&65535,*struct.unpack('<3i',im.cpu.mem_read(target,12))])
        im.return_from(stack_bytes=24)
    image.intercept(0xa2f84,'Record projectile releases; projectile simulation and impact damage are outside this route comparison.',weapon)
    records=[];cursor=0
    while True:
        size=struct.unpack_from('<H',raw,cursor)[0];cursor+=2
        if not size:break
        records.append((cursor,size));cursor+=size
    output=[]
    for tick in range(ticks):
        requests.clear()
        image.call(0x78064,limit=2000000);image.call(0x78084,limit=2000000)
        values=[]
        for pointer,index in sorted(registry.items(),key=lambda item:item[1]):
            body=bytes(image.cpu.mem_read(pointer,68))
            values.extend([index,*struct.unpack_from('<3i3Hi3hihhI',body),struct.unpack_from('<I',body,44)[0]-0x300000,struct.unpack_from('<H',body,66)[0],*body[40:42]])
        for at,size in records:values.extend(image.cpu.mem_read(0x300000+at,size))
        values.append(len(requests))
        for request in requests:values.extend(request)
        digest=14695981039346656037
        for value in values:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        output.append((digest,values))
    return output,len(registry)


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--ticks',type=int,default=128)
    parser.add_argument('--program')
    parser.add_argument('--intact',type=int,default=0)
    parser.add_argument('--synthetic',action='store_true')
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args()
    data_dir=args.research/'installs/cd_1994_09/TFX'
    profiles=dataset(args.research/'analysis/entities/data.js')['records']
    programs=json.loads((args.research/'analysis/waypoints/programs.json').read_text())['programs']
    if args.program:programs=[p for p in programs if any(args.program in n for n in p['names'])]
    if args.synthetic:
        raw_profile=bytearray(74);raw_profile[0]=14
        raw_profile[1:5]=b'TEST';raw_profile[21:25]=b'test'
        struct.pack_into('<H',raw_profile,32,42)
        struct.pack_into('<2i7H',raw_profile,36,10000,12000,0,18000,80,1000,0,60000,500)
        struct.pack_into('<h',raw_profile,62,180)
        profile_file=struct.pack('<2H',0,1)+raw_profile+bytes(4)
        synthetic_profiles=[{'offset':4,'hex':bytes(raw_profile).hex()}]
        formation=b''.join(struct.pack('<H3i',i*4096,8192 if i else 0,4096 if i else 0,-800*i) for i in range(10))
        def command(op,*words):return bytes([op])+struct.pack('<'+'H'*len(words),*[v&65535 for v in words])
        def group(count,airborne,altitude,speed):return command(14,count,10,10,42,airborne,altitude,speed,0,0,90 if not airborne else 0,0,0)
        cases=[]
        code=group(2,0,0,0)+command(3,0,2)+command(6,0)+b'GROUP READY'+bytes(29)+command(4,90,200,100)
        loop=len(code);code+=command(11,5000)+command(13,400)
        at=len(code);code+=command(2,14,10,at-loop)+bytes([0])
        cases.append((12000,0,code))
        code=group(3,1,12000,400)+command(6,0)+b'FORMATION CHECK'+bytes(25)
        loop=len(code);code+=command(13,700)+command(11,10000)
        at=len(code);code+=command(1,at-loop,20,20,at-loop)
        cases.append((12000,0,code))
        code=group(1,1,3000,400);loop=len(code)
        code+=command(12,10,12,8,3,20000,0x0403,0,0,0,0,0,0)
        code+=command(5,10,12,0,0,0,0,0,0)+command(10,10,12,0,0,0,0,0,0,8)
        at=len(code);code+=command(1,at-loop,10,12,at-loop)
        cases.append((12000,1,code))
        # A deliberately incompatible profile tests the shipped cross-record-read behaviour without copying game data.
        code=group(1,1,30000,500);loop=len(code)
        code+=command(11,30000)+command(13,500)
        at=len(code);code+=command(1,at-loop,20,20,at-loop)
        cases.append((512,0,code))
        fixtures=[]
        for index,(ticks,intact,code) in enumerate(cases):
            fixture_profile=profile_file
            fixture_records=synthetic_profiles
            if index==3:
                short=bytearray(raw_profile[:46]);short[0]=16
                following=bytearray(raw_profile);struct.pack_into('<H',following,32,43)
                fixture_profile=struct.pack('<2H',0,2)+short+following+bytes(4)
                fixture_records=[{'offset':4,'hex':bytes(short).hex()},{'offset':50,'hex':bytes(following).hex()}]
            raw=struct.pack('<H',len(code))+code+bytes(2)
            observed,count=original(data_dir,raw,fixture_records,ticks,intact,formation)
            digest=14695981039346656037
            for sample,_ in observed:
                for byte in struct.pack('<Q',sample):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            fixtures.append(f'{ticks} {intact} {fixture_profile.hex()} {raw.hex()} {formation.hex()} {digest}\n')
            print('Synthetic air sequence',index,count,'actors',ticks,'ticks captured',flush=True)
        if not args.save_fixture:raise ValueError('--synthetic requires --save-fixture')
        args.save_fixture.write_text(''.join(fixtures))
        subprocess.run([str(args.build/'air_tests'),str(args.save_fixture)],check=True)
        return
    total=0
    for number,program in enumerate(programs):
        name=program['names'][0] if program['names'] else program['id']
        native,count=original(data_dir,(args.research/'extracted/cd_1994_09/resources'/program['path']).read_bytes(),profiles,args.ticks,args.intact)
        request=f'{name} {args.ticks} {args.intact}\n'
        result=subprocess.run([str(args.build/'air_probe'),str(data_dir)],input=request,text=True,capture_output=True)
        if result.returncode:raise RuntimeError((name,result.stderr))
        observed=[int(v) for v in result.stdout.split()]
        assert len(observed)==len(native),(name,len(observed),len(native))
        for tick,(actual,(expected,values)) in enumerate(zip(observed,native)):
            if actual!=expected:
                detail=subprocess.run([str(args.build/'air_probe'),str(data_dir),'--verbose'],input=request,text=True,capture_output=True,check=True)
                actual_values=[int(v) for v in detail.stdout.splitlines()[tick].split()]
                first=next((i for i,(a,b) in enumerate(zip(actual_values,values)) if a!=b),'length')
                raise AssertionError((name,tick,first,'C++',actual_values,'native',values))
        total+=count*args.ticks
        if number%16==0:print(name,count,'actors,',args.ticks,'ticks agree',flush=True)
    print(len(programs),'programs;',total,'native aircraft updates agree in the declared noncombat context')


if __name__=='__main__':main()
