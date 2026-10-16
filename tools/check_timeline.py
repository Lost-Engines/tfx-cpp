#!/usr/bin/env python3
"""Compare mission message/event scheduling with original 2.05 frame boundaries."""
import argparse
from pathlib import Path
import random
import struct
import subprocess

from unicorn import x86_const as r
from native_reference import NativeReference


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args()
    image=NativeReference(args.data_dir/'TFX.DAT')
    messages,events=[],[]
    def message(im):
        messages.append(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)
        im.return_from()
    image.intercept(0x81198,'Record message delivery; font drawing and display lifetime are separate HUD consumers.',message)
    def event(im):
        index=im.cpu.reg_read(r.UC_X86_REG_EAX)-256
        assert im.cpu.reg_read(r.UC_X86_REG_EDX)==index
        events.append(index)
        im.return_from()
    image.intercept(0xb52d4,'Record a resolved scenery event; SSD execution has separate native corpus checks.',event)
    image.intercept(0xb4f44,'Player SSD state refresh after event polling is outside scheduling.',lambda im:im.return_from())
    rng=random.Random(0x70e44)
    cases,expected,fixtures=[],[],[]
    for index in range(64):
        start=rng.choice((0,1,53,54,0x7fffffef,0x80000000,0xffffffef))
        clock=rng.getrandbits(32)
        times=[(start+rng.randrange(-60,400))&0xffffffff for _ in range(26)]
        times[:8]=[0,1,2,54,start,(start+2)&0xffffffff,0x80000000,0xffffffff]
        steps=[rng.choice((0,1,2,7,18,54,65535)) for _ in range(64)]
        header=[10,16,64,start,clock,*times,*steps]
        cases.append(header)
        image.write(0x11b42,'<BB',10,16)
        for i,time in enumerate(times[:10]):image.write(0x11ac8+9*i,'<IIB',time,i+1,0)
        for i,time in enumerate(times[10:]):image.write(0x11874+11*i,'<3BIHBB',i,0,0,time,i+256,0,0)
        image.write(0x7618,'<I',start)
        values=[]
        for ticks in steps:
            messages.clear();events.clear()
            image.call(0x71b40)
            elapsed=(image.read(0x7618,'<I')[0]+ticks)&0xffffffff
            image.write(0x7618,'<I',elapsed)
            image.call(0x70e44)
            values.extend([elapsed,(elapsed+clock)&0xffffffff,len(messages),*messages,len(events),*events])
        expected.append(values)
        digest=14695981039346656037
        for value in values:
            for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixtures.append(' '.join(map(str,header+[digest]))+'\n')
    result=subprocess.run([str(args.build/'timeline_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in cases),text=True,capture_output=True,check=True)
    actual=[[int(v) for v in row.split()] for row in result.stdout.splitlines()]
    assert actual==expected,next(((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
    if args.save_fixture:args.save_fixture.write_text(''.join(fixtures))
    print('4096 native mission frame boundaries agree: authored order, equality, zero steps, unsigned time and wrapping')


if __name__=='__main__':main()
