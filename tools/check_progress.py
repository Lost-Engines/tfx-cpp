#!/usr/bin/env python3
"""Compare native target bookkeeping, completion and return/countdown termination.

Supplied target flags and counters stand at the combat boundary. This executes
original rule/score/termination routines, not complete missions or their UI.
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
    args=parser.parse_args();rng=random.Random(0x719a4)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    image.intercept(0xc8568,'Resolve supplied target instances; the original destroyed-flag reader executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300200+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*32),im.return_from()))
    def config(im):
        key=im.cpu.reg_read(r.UC_X86_REG_EAX)-im.data
        assert key in (0x200,0x208,0x210,0x218),hex(key)
        im.cpu.reg_write(r.UC_X86_REG_EAX,0x300800+(key-0x200)//2);im.return_from()
    image.intercept(0xb1334,'Supply score/outcome/status/Arcade parser variables; their writes are captured.',config)
    completion_audio=[]
    def music(im):
        cue=im.cpu.reg_read(r.UC_X86_REG_EAX);assert cue==3,cue
        completion_audio.append(cue);notices.extend([4,0]);im.return_from()
    def sound(im):
        sample=im.cpu.reg_read(r.UC_X86_REG_EAX);assert sample==41 and completion_audio==[3],(sample,completion_audio)
        completion_audio.clear();im.return_from()
    image.intercept(0xa5a9c,'Observe the original completion cue in event order.',music)
    image.intercept(0xa4dfc,'Verify completion cue/sample pairing and urgent sample 41.',sound)
    notices=[]
    def message(im):
        pointer=im.cpu.reg_read(r.UC_X86_REG_EAX)
        if pointer==im.data+0xa8:notices.extend([3,0])
        elif pointer==0x300700:notices.extend([2 if im.read(0x11b30,'<B')[0]==5 else 1,0])
        else:
            assert 0x300500<=pointer<0x300620 and (pointer-0x300500)%32==0,hex(pointer)
            notices.extend([0,(pointer-0x300500)//32])
        im.return_from()
    image.intercept(0x81198,'Capture target/timer radio notices; no host audio or text output.',message)
    image.intercept(0x81254,'Capture completion/protection notices; no front-end popup.',message)
    inputs=[];expected=[];fixtures=[]
    for case in range(512):
        count=case%10;kind=rng.choice((0,1,2,3,4,5,255));value=rng.choice((-1,0,1,2,3,100,1000));landed_start=case%2;timer=rng.choice((-1,0,1,100,1000));violations=rng.choice((0,0,1,2,-1));exit_ticks=rng.choice((0,0,1,540,1620,32767));critical=int(case%13==0)
        image.write(0x11b22,'<h',count);image.write(0x11b30,'<B',kind);image.write(0x11b31,'<i',value);image.write(0x11b35,'<I',0x300700);image.write(0x11b3c,'<B',landed_start)
        image.write(0x5c20,'<i',0);image.write(0x11b26,'<h',0);image.write(0x5d44,'<h',0);image.write(0xe708,'<i',timer);image.write(0xe75c,'<h',violations);image.write(0x5940,'<h',exit_ticks);image.write(0x593e,'<B',0);image.write(0x593a,'<h',0);image.write(0xe77c,'<B',critical);image.write(0x5c30,'<i',0);image.cpu.mem_write(image.data+0xe742,bytes(9));image.cpu.mem_write(0x300800,bytes(16))
        for index in range(count):
            image.write(0x5c4c+index*26,'<H',index+1);image.write(0x5c52+index*26,'<i',-1 if index%2 else 100+index*100);image.write(0x5c56+index*26,'<I',0x300500+index*32)
        control_rows=[];native_rows=[];time=0
        for frame in range(64):
            elapsed=rng.choice((0,1,4,10,55,540,1620,30000,65535));landed=int(frame%9==0);speed=rng.choice((0,1,100));arcade=case%2;enemy=rng.randrange(-1,5);allied=rng.choice((0,0,0,1,2));mobile=rng.randrange(-1,5);mask=rng.randrange(1<<count)
            row=[time,elapsed,landed,speed,arcade,enemy,allied,mobile,mask];control_rows.append(row)
            image.write(0x7618,'<I',time);image.write(0x13476,'<H',elapsed);image.write(0x8d3a,'<h',landed);image.write(0x13444,'<i',speed);image.write(0x5c24,'<i',enemy);image.write(0x5c28,'<i',allied);image.write(0x5c2c,'<i',mobile);image.cpu.mem_write(0x30080c,struct.pack('<I',arcade))
            for index in range(count):image.cpu.mem_write(0x300202+index*32,bytes([16 if mask&(1<<index) else 0]))
            notices.clear();completion_audio.clear();image.call(0x7188c)
            if not image.read(0x593e,'<B')[0]:image.call(0x719a4)
            image.call(0x71a9c)
            if image.read(0x5940,'<h')[0]:image.call(0x71b90)
            if image.read(0xe708,'<i')[0]!=-1:image.call(0x70d74)
            assert not completion_audio
            values=[image.read(0x5c20,'<i')[0],image.read(0x11b26,'<h')[0],image.read(0x5d44,'<h')[0],image.read(0xe708,'<i')[0],image.read(0x5c30,'<i')[0],image.read(0x5940,'<h')[0],image.read(0x593e,'<B')[0],image.read(0x593a,'<h')[0],*struct.unpack('<2i',image.cpu.mem_read(0x300804,8)),struct.unpack('<i',image.cpu.mem_read(0x300800,4))[0],len(notices)//2,*notices]
            native_rows.append(values);time=(time+elapsed)&0xffffffff
            if image.read(0x593a,'<h')[0]:break
        header=[len(control_rows),count,kind,value,landed_start,timer,violations,exit_ticks,critical]
        lines=[' '.join(map(str,header)),*[' '.join(map(str,row)) for row in control_rows]];inputs.extend(lines);expected.extend(native_rows)
        digest=14695981039346656037
        for values in native_rows:
            for val in values:
                for byte in struct.pack('<I',val&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixtures.extend([*lines,str(digest)])
    output=subprocess.run([str(args.build/'progress_probe')],input='\n'.join(inputs)+'\n',capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,a,b)
    if args.save_fixture:
        args.save_fixture.write_text('\n'.join(fixtures)+'\n');subprocess.run([str(args.build/'progress_probe'),str(args.save_fixture)],check=True)
    print(len(expected),'native mission-progress frames agree across 512 sequences: target credit, all rule kinds, strict timers, landing, termination and ordered completion cue/sample events')


if __name__=='__main__':main()
