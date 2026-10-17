#!/usr/bin/env python3
"""Compare native player loss/impact termination while supplying graphical effects."""
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
    args=parser.parse_args();rng=random.Random(0x7d270)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    fatal=[0];events=[]
    image.intercept(0xb6e88,'Supply whether the current aircraft SSD has been destroyed.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,fatal[0]),im.return_from()))
    image.intercept(0xb1334,'Supply outcome/status parser variables and capture their writes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300700 if im.cpu.reg_read(r.UC_X86_REG_EAX)==im.data+0x1450 else 0x300704),im.return_from()))
    for address in (0x75030,0x8fd84,0xcccc4,0xccf4c):image.intercept(address,'Graphical, camera or sound output outside the loss/termination state capture.',lambda im:im.return_from())
    image.intercept(0xb52d4,'Capture player SSD events; loss flags and countdown execute unmodified.',lambda im:(events.append(im.cpu.reg_read(r.UC_X86_REG_EDX)),im.return_from()))
    image.intercept(0xb0d80,'Supply the ordinary terrain cell used for the impact lookup.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,1),im.return_from()))
    image.intercept(0x7da20,'Supply an ordinary impact appearance; water/aftermath rendering is outside this capture.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
    image.write(0xac74,'<I',image.native(0x75954))
    sample_requests=[]
    def sample(im):
        sp=im.cpu.reg_read(r.UC_X86_REG_ESP);priority=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0];ids=[];cursor=sp+8
        while True:
            descriptor=struct.unpack('<I',im.cpu.mem_read(cursor,4))[0];cursor+=4
            if not descriptor:break
            assert len(ids)<8 and (descriptor-im.data-0x9860)%26==0
            ids.append((descriptor-im.data-0x9860)//26)
        sample_requests.append([priority,len(ids),*ids]);im.return_from()
    image.intercept(0x75954,'Observe actual sample priority and descriptor sequence; 0xa4f2c executes unchanged.',sample)
    music_requests=[]
    image.intercept(0xa5a9c,'Observe the aircraft-loss cue at the original first-loss boundary.',lambda im:(music_requests.append(im.cpu.reg_read(r.UC_X86_REG_EAX)),im.return_from()))
    rows=[];expected=[]
    for case in range(4096):
        ejected=rng.randrange(2);impact=rng.randrange(2);ticks=rng.choice((-32768,-1,0,1,199,200,32767));fatal[0]=rng.randrange(2);collision=rng.randrange(2);elapsed=rng.choice((0,1,4,55,199,200,201,32767,65535));invulnerable=rng.randrange(2)
        height=rng.choice((-32768,-1000,-201,-200,-199,0,1000))
        rows.append([ejected,impact,ticks,fatal[0],collision,elapsed,invulnerable,height]);events.clear();music_requests.clear();sample_requests.clear()
        image.write(0xe76c,'<H',2 if impact else 1);image.write(0x12bfc,'<H',2);image.write(0x12bfa,'<H',4);image.write(0x12c00,'<H',3);image.write(0x12c02,'<h',ticks);image.write(0x12c04,'<h',collision);image.write(0x86ce,'<B',ejected);image.write(0x13250,'<H',invulnerable);image.write(0xe784,'<B',0);image.write(0xe774,'<H',0);image.write(0x13476,'<H',elapsed);image.write(0x593a,'<h',0);image.write(0x13430,'<i',height);image.cpu.mem_write(0x300700,bytes(8))
        image.call(0x7d270)
        assert music_requests==([1] if 21 in events else []),(case,music_requests,events)
        expected.append([image.read(0x86ce,'<B')[0],int(image.read(0xe76c,'<H')[0]==2),image.read(0x12c02,'<h')[0],image.read(0x593a,'<h')[0],*struct.unpack('<2i',image.cpu.mem_read(0x300700,8)),int(21 in events),len(sample_requests),*[v for request in sample_requests for v in request]])
    output=subprocess.run([str(args.build/'death_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i],a,b)
    if args.save_fixture:
        lines=[]
        for row,values in zip(rows,expected):
            digest=14695981039346656037
            for value in values:
                for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            lines.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(lines));subprocess.run([str(args.build/'death_probe'),str(args.save_fixture)],check=True)
    print('4096 native player-loss/impact transitions agree, including invulnerability, repeated loss, zero/negative countdowns, word wrapping and exact airborne/impact/mayday sample sequences')


if __name__=='__main__':main()
