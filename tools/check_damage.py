#!/usr/bin/env python3
"""Check native player system damage and intermittent-fault recovery bit for bit."""
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
    args=parser.parse_args();rng=random.Random(0x8f460)
    image=NativeReference(args.data_dir/'TFX.DAT');image.call(0xde851);notifications=[]
    def notify(im):
        assert im.cpu.reg_read(r.UC_X86_REG_EDX)==13
        notifications.append(13);im.return_from()
    image.intercept(0xb52d4,'Capture player SSD damage entry 13; the system/random/accumulation calculation executes unmodified.',notify)
    rows=[];expected=[]
    for case in range(8192):
        severity=rng.choice((-32768,-1,0,1,2,5,10,49,50,99,100,200,32767,32768,65535,65536));invulnerable=int(case%4==0);elapsed=rng.choice((0,1,4,10,55,1080,1081,30000,65535));low=rng.randrange(65536);high=rng.randrange(65536)
        accumulated=struct.unpack('<Q',struct.pack('<d',rng.uniform(-100,100)))[0];display_selection=rng.randrange(-32768,32768)
        if case < 4:
            severity=(40,80,97,80)[case];invulnerable=0
            accumulated=struct.unpack('<Q',struct.pack('<d',(0,.2,.6,1.1)[case]))[0]
        conditions=[rng.choice((0,1,2,11,14,255)) for _ in range(12)];repair=[rng.choice((0,1,1079,1080,1081,32767,65535)) for _ in range(12)]
        rows.append([severity,invulnerable,elapsed,low,high,accumulated,display_selection,*conditions,*repair])
        image.write(0x13250,'<H',invulnerable);image.write(0x8e18,'<Q',accumulated);image.write(0x713e,'<h',display_selection);image.write(0x7d70,'<12B',*conditions);image.write(0x1328c,'<12H',*repair);image.write(0x13476,'<H',elapsed)
        image.write(0xabe9,'<B',(case>>2)&1);image.write(0xe784,'<B',(case>>3)%8)
        image.cpu.mem_write(image.native(0xc9894),struct.pack('<2H',low,high));notifications.clear()
        image.call(0x8f460,eax=severity&0xffffffff);image.call(0x871d4)
        expected.append([*struct.unpack('<2H',image.cpu.mem_read(image.native(0xc9894),4)),image.read(0x8e18,'<Q')[0],image.read(0x713e,'<H')[0],len(notifications),*image.read(0x7d70,'<12B'),*image.read(0x1328c,'<12H')])
    result=subprocess.run([str(args.build/'damage_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i],a,b)
    if args.save_fixture:
        lines=[]
        for row,values in zip(rows,expected):
            digest=14695981039346656037
            for value in values:
                for byte in struct.pack('<Q',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            lines.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(lines));subprocess.run([str(args.build/'damage_probe'),str(args.save_fixture)],check=True)
    print('8192 native damage/repair cases agree: all system slots, shared random state, signed damage, stored double bits, repair-clock wrapping and independent ejection/pilot phases')


if __name__=='__main__':main()
