#!/usr/bin/env python3
"""Compare aircraft routes, formation and optional combat in controlled native contexts."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from unicorn import x86_const as r, UC_HOOK_CODE
from native_reference import NativeReference


def dataset(path):
    text=path.read_text()
    return json.loads(text[text.index('=')+1:].strip().removesuffix(';'))


def original(data_dir,raw,profiles,ticks,intact,formation=None,combat=None,manoeuvres=(),damage_tick=0,warning_log=None,collision_damage=False):
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
    if combat is None:
        image.intercept(0x76ba4,'Explicit no-air-combat-acquisition context; waypoint, formation and all numerical control execute normally.',scan)
    else:
        image.cpu.hook_add(UC_HOOK_CODE,lambda cpu,*_:requests.append([registry[cpu.reg_read(r.UC_X86_REG_EBX)],0]),begin=image.native(0x76c4b),end=image.native(0x76c4b))
        image.write(0x10f28,'<3i3Hi',*combat[:7])
        image.write(0x11b2a,'<H',combat[7]);image.write(0x5a12,'<H',combat[8]);image.write(0xac90,'<B',combat[9])
        incoming=combat[10]
        for pointer,index in registry.items():
            if not incoming:continue
            x,y,z=struct.unpack('<3i',image.cpu.mem_read(pointer,12))
            threat=0x310000+index*32
            image.cpu.mem_write(threat+6,struct.pack('<Bx3i',incoming%3,x+(300000 if incoming%2 else -300000),y,z+200000))
            image.cpu.mem_write(pointer+52,struct.pack('<I',threat))
        banks=[[],[],[]];manoeuvre_pointers=[];cursor=0x312000
        for raw_sequence in manoeuvres:
            image.cpu.mem_write(cursor,raw_sequence);manoeuvre_pointers.append(cursor);banks[raw_sequence[0]].append(cursor);cursor+=len(raw_sequence)+16
        for bank,count,table in zip(banks,(0x5974,0x5972,0x5970),(0x10e70,0x10dd0,0x10d30)):
            image.write(count,'<H',len(bank))
            if bank:image.cpu.mem_write(image.data+table,struct.pack('<'+'I'*len(bank),*bank))
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
        if combat is not None:requests[-1].append(100 if target==im.data+0x10f28 else registry.get(target,-1))
        im.return_from(stack_bytes=24)
    image.intercept(0xa2f84,'Record projectile releases; projectile simulation and impact damage are outside this route comparison.',weapon)
    if combat is not None:
        for address,kind in ((0x763fc,0),(0x76398,1)):
            def warning(im,kind=kind):
                target=im.cpu.reg_read(r.UC_X86_REG_EAX)
                if target==im.data+0x10f28 or kind==1:
                    identity_target=100 if target==im.data+0x10f28 else registry[target]
                    requests.append([identity(im),5,identity_target,kind])
                    if warning_log is not None:warning_log.append((identity_target,kind))
                im.return_from()
            image.intercept(address,'Record warning notification; permission/audio delivery is checked separately from actor movement.',warning)
        for address,kind in ((0xa3588,0),(0xa353c,1)):
            def countermeasure(im,kind=kind):
                strength=struct.unpack('<h',struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EDX)&65535))[0]
                requests.append([registry[im.cpu.reg_read(r.UC_X86_REG_EAX)],6,kind,strength]);im.return_from()
            image.intercept(address,'Record countermeasure request; incoming threat is externally supplied and held fixed.',countermeasure)
    if damage_tick:
        image.write(0xac74,'<I',image.native(0x75954)) # Declared sound-output boundary: original empty callback.
        image.intercept(0x7da20,'Supply an ordinary non-water ground impact effect.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,8),im.return_from()))
        def impact(im):
            position=struct.unpack('<3i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),12))
            requests.append([identity(im),4,*position,im.cpu.reg_read(r.UC_X86_REG_EDX)]);im.return_from()
        image.intercept(0x7b144,'Capture the separately rendered aircraft ground-impact effect.',impact)
    records=[];cursor=0
    while True:
        size=struct.unpack_from('<H',raw,cursor)[0];cursor+=2
        if not size:break
        records.append((cursor,size));cursor+=size
    output=[]
    for tick in range(ticks):
        requests.clear()
        if damage_tick and tick==damage_tick:
            for pointer,index in sorted(registry.items(),key=lambda item:item[1]):
                image.write(0x5a10,'<H',int(index>=50));image.write(0x11118,'<h',index%50)
                previous_random=bytes(image.cpu.mem_read(image.native(0xc9894),4))
                image.call(0x785ec if collision_damage else 0x78274,eax=pointer)
                if collision_damage:assert bytes(image.cpu.mem_read(image.native(0xc9894),4))==previous_random
        image.call(0x78064,limit=2000000);image.call(0x78084,limit=2000000)
        values=[]
        for pointer,index in sorted(registry.items(),key=lambda item:item[1]):
            body=bytes(image.cpu.mem_read(pointer,68))
            values.extend([index,*struct.unpack_from('<3i3Hi3hihhI',body),struct.unpack_from('<I',body,44)[0]-0x300000,struct.unpack_from('<H',body,66)[0],*body[40:42]])
            if combat is not None:
                target,incoming,sequence=struct.unpack_from('<3I',body,48)
                program=-1;address=-1
                if sequence:
                    program=max(i for i,p in enumerate(manoeuvre_pointers) if p<=sequence);address=sequence-manoeuvre_pointers[program]
                values.extend([100 if target==image.data+0x10f28 else registry.get(target,-1),program,address,*body[64:66]])
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
    parser.add_argument('--combat',action='store_true')
    parser.add_argument('--damage-tick',type=int,default=0)
    parser.add_argument('--collision-damage',action='store_true')
    parser.add_argument('--incoming',type=int,default=0)
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
        if args.combat:
            struct.pack_into('<H',raw_profile,46,18000)
            struct.pack_into('<H',raw_profile,60,4)
            struct.pack_into('<5H',raw_profile,64,2,4,8000,8,40)
            profile_file=struct.pack('<2H',0,1)+raw_profile+bytes(4)
            synthetic_profiles=[{'offset':4,'hex':bytes(raw_profile).hex()}]
            manoeuvres=[]
            for category in (0,1):
                header=bytearray(16);header[0]=category
                manoeuvres.append(bytes(header)+struct.pack('<BbbbbB',60,-90,20,60,5,3)+struct.pack('<BbbbbB',90,30,-20,-60,-5,4)+bytes(1))
            fixtures=[]
            for scenario in range(12):
                code=group(2,1,12000,500)
                loop=len(code);code+=command(13,500)+command(11,12000)
                at=len(code);code+=command(1,at-loop,10,20,at-loop)
                raw=struct.pack('<H',len(code))+code+bytes(2)
                combat=[10*524288+262144+(300000 if scenario%3==2 else 0),-12000*32,10*524288+262144+(2500000 if scenario%4==0 else 100000),0,32768 if scenario%2 else 0,0,400<<16,scenario%3,0,int(scenario!=8),scenario-8 if scenario>=9 else 0]
                ticks=4096
                observed,count=original(data_dir,raw,synthetic_profiles,ticks,0,formation,combat,manoeuvres,args.damage_tick,collision_damage=args.collision_damage)
                digest=14695981039346656037
                for sample,_ in observed:
                    for byte in struct.pack('<Q',sample):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
                fixtures.append(f"{ticks} 0 {profile_file.hex()} {raw.hex()} {formation.hex()} {','.join(m.hex() for m in manoeuvres)} {' '.join(map(str,combat))}{(' '+str(args.damage_tick)) if args.damage_tick else ''} {digest}\n")
                print('Synthetic combat sequence',scenario,count,'actors',ticks,'ticks captured',flush=True)
            if not args.save_fixture:raise ValueError('--synthetic --combat requires --save-fixture')
            args.save_fixture.write_text(''.join(fixtures))
            subprocess.run([str(args.build/'air_combat_tests'),str(args.save_fixture),*(['--collision' if args.collision_damage else '--death'] if args.damage_tick else [])],check=True)
            return
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
    manoeuvres=[]
    if args.combat:
        catalog=json.loads((args.research/'analysis/resources/catalog.json').read_text())['entries']
        by_name={name:e for e in catalog for name in e['recovered_names']+e['candidate_names']}
        for name in (args.research/'extracted/cd_1994_09/resources/cbn.dir').read_text().split():
            manoeuvres.append((args.research/'extracted/cd_1994_09/resources'/by_name['cbn/'+name]['path']).read_bytes())
    for number,program in enumerate(programs):
        name=program['names'][0] if program['names'] else program['id']
        combat=None
        if args.combat:
            # A stationary supplied player, near the first air group. This is a controlled AI test, not a complete flight session.
            group=next((bytes.fromhex(record["raw_hex"]) for record in program["records"] if record["type"]==14),None)
            x,z=struct.unpack_from("<2h",group,3) if group else (10,10)
            combat=[x*524288+262144,-300000,z*524288+600000,0,0,0,400<<16,number%3,0,1,args.incoming]
        native,count=original(data_dir,(args.research/'extracted/cd_1994_09/resources'/program['path']).read_bytes(),profiles,args.ticks,args.intact,combat=combat,manoeuvres=manoeuvres,damage_tick=args.damage_tick,collision_damage=args.collision_damage)
        request=f'{name} {args.ticks} {args.intact}'+(' '+' '.join(map(str,combat)) if combat else '')+'\n'
        flags=(['--combat'] if args.combat else [])+(['--damage',str(args.damage_tick)] if args.damage_tick else [])+(['--collision'] if args.collision_damage else [])
        result=subprocess.run([str(args.build/'air_probe'),str(data_dir),*flags],input=request,text=True,capture_output=True)
        if result.returncode:raise RuntimeError((name,result.stderr))
        observed=[int(v) for v in result.stdout.split()]
        assert len(observed)==len(native),(name,len(observed),len(native))
        for tick,(actual,(expected,values)) in enumerate(zip(observed,native)):
            if actual!=expected:
                detail=subprocess.run([str(args.build/'air_probe'),str(data_dir),*flags,'--verbose'],input=request,text=True,capture_output=True,check=True)
                actual_values=[int(v) for v in detail.stdout.splitlines()[tick].split()]
                first=next((i for i,(a,b) in enumerate(zip(actual_values,values)) if a!=b),'length')
                raise AssertionError((name,tick,first,'C++',actual_values,'native',values))
        total+=count*args.ticks
        if number%16==0:print(name,count,'actors,',args.ticks,'ticks agree',flush=True)
    print(len(programs),'programs;',total,'native aircraft updates agree in the declared', 'combat' if args.combat else 'noncombat','context')


if __name__=='__main__':main()
