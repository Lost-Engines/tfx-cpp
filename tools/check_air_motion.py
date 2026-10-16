#!/usr/bin/env python3
"""Compare native bank-coupled aircraft motion and air-controller primitives."""
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
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args()
    data_dir=args.research/'installs/cd_1994_09/TFX'
    text=(args.research/'analysis/entities/data.js').read_text()
    profiles=[p for p in json.loads(text[text.index('=')+1:].strip().removesuffix(';'))['records'] if p['opcode']==14]
    image=NativeReference(data_dir/'TFX.DAT')
    image.cpu.mem_map(0x300000,0x20000)
    state,profile_at=0x300000,0x310000
    image.write(0xac58,'<i',-16384);image.write(0xac5c,'<i',0)
    events=[]
    def event(im):
        events.append(im.cpu.reg_read(r.UC_X86_REG_EDX)&65535)
        im.return_from()
    image.intercept(0xb52d4,'Record afterburner SSD events; the instance VM is checked separately.',event)
    rng=random.Random(0x77f50)
    cases,expected=[],[]
    functions=(0x75dfc,0x75f4c,0x75e94,0x75fb4,0x75ee0,0x75dc0,0x77f50,0xa4c20,0x76370)
    def capture(raw,action,model,values):
        x,y,z,pitch,heading,bank,speed,rp,rh,rb,acceleration,ticks,flags,requested=values
        position=[x,y,z];angles=[pitch,heading,bank];rates=[rp,rh,rb]
        memory=bytearray(68)
        struct.pack_into('<3i3Hi3hih',memory,0,*position,*angles,speed,*rates,acceleration,ticks)
        struct.pack_into('<I',memory,60,profile_at)
        struct.pack_into('<H',memory,66,flags)
        image.cpu.mem_write(state,bytes(memory));image.cpu.mem_write(profile_at,raw)
        image.write(0x1347a,'<B',model)
        events.clear()
        result=image.call(functions[action],eax=struct.unpack_from('<H',raw,44)[0] if action==7 else state,edx=(position[1] if action==7 else requested)&0xffffffff)
        memory=bytes(image.cpu.mem_read(state,68))
        value=0
        if action in (0,7):value=result&65535
        elif action==3:value=result&65535
        elif action==4:value=struct.unpack('<h',struct.pack('<H',result&65535))[0]
        elif action==6:
            assert len(events)<=1
            value=events[0] if events else 0
        return [value,*struct.unpack_from('<3i3Hi3hih',memory),struct.unpack_from('<H',memory,66)[0]]
    for index in range(9216):
        profile=rng.choice(profiles);raw=bytes.fromhex(profile['hex'])
        action=index%9;model=rng.choice((0,1,2,6))
        position=[rng.randrange(-100000000,100000001),rng.randrange(-6000000,100001),rng.randrange(-100000000,100000001)]
        angles=[rng.randrange(65536) for _ in range(3)]
        speed=rng.randrange(1800)<<16
        rates=[rng.randrange(-1000,1001) for _ in range(3)]
        acceleration=rng.randrange(-300000,300001)
        ticks=rng.randrange(1,32768) if action==6 else rng.randrange(-55,101)
        flags=rng.randrange(65536)
        if action in (2,3):requested=rng.choice((-32768,-29120,-25480,-91,-90,0,90,91,25480,29120,32767,rng.randrange(-32768,32768)))
        elif action==1:requested=rng.randrange(2000)<<16
        else:requested=rng.randrange(-10000000,10000001)
        row=[profile['id'],action,model,*position,*angles,speed,*rates,acceleration,ticks,flags,requested]
        cases.append(row)
        expected.append(capture(raw,action,model,row[3:]))
    result=subprocess.run([str(args.build/'air_motion_probe'),str(data_dir)],input=''.join(' '.join(map(str,row))+'\n' for row in cases),text=True,capture_output=True,check=True)
    actual=[[int(v) for v in row.split()] for row in result.stdout.splitlines()]
    assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):
        assert a==b,(i,cases[i],'C++',a,'native',b)
    print(f'{len(profiles)} aircraft profiles; {len(cases)} native steering, envelope, altitude, speed and banked-motion cases agree')
    # Replayable cases use test-authored parameters and envelopes rather than copying game resources.
    image.cpu.mem_write(image.data+0x93b4,bytes((i*37+11)%173 for i in range(1140)))
    synthetic,outputs,fixtures=[],[],[]
    for index in range(576):
        action=index%9;model=rng.choice((0,1,2,6))
        performance=[rng.randrange(100001),rng.randrange(100001),rng.randrange(8),rng.randrange(65536),rng.randrange(201),rng.randrange(500,3001),rng.randrange(5001),rng.randrange(10000,65001),rng.randrange(500,2501),rng.randrange(1,701)]
        raw=bytearray(74);raw[0]=14
        struct.pack_into('<2i7H',raw,36,*performance[:9])
        struct.pack_into('<h',raw,62,performance[9])
        values=list(cases[index][3:])
        values[1]=rng.randrange(-2100000,110001)
        values[6]=rng.choice((0,112,113,1461,1462,1463,rng.randrange(1800)))<<16
        if action==6:values[11]=rng.randrange(1,32768)
        row=[action,model,*performance,*values]
        synthetic.append(row)
        output=capture(bytes(raw),action,model,values)
        outputs.append(output)
        digest=14695981039346656037
        for value in output:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixtures.append(' '.join(map(str,row+[digest]))+'\n')
    result=subprocess.run([str(args.build/'air_motion_probe'),'--synthetic'],input=''.join(' '.join(map(str,row))+'\n' for row in synthetic),text=True,capture_output=True,check=True)
    observed=[[int(v) for v in row.split()] for row in result.stdout.splitlines()]
    assert observed==outputs,next(((i,a,b) for i,(a,b) in enumerate(zip(observed,outputs)) if a!=b),None)
    if args.save_fixture:args.save_fixture.write_text(''.join(fixtures))
    print('576 additional native synthetic cases agree; asset-free fixture available')


if __name__=='__main__':main()
