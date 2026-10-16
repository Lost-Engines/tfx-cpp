#!/usr/bin/env python3
"""Check the original querying-projectile health callback with test-authored SSDs."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference


def program(health,impact,victim,opcode,lives):
    raw=bytearray(16);raw[0]=2 if victim else 0;raw[8]=3
    def emit(*words):raw.extend(struct.pack('<'+'H'*len(words),*words))
    def entry(index):struct.pack_into('<H',raw,10+index*2,(len(raw)-(10+index*2))//2)
    entry(0);emit(17,impact,18,health)
    if victim:emit(11,0,lives)
    emit(0);entry(1);emit(0);entry(2)
    if victim:
        emit(opcode,65526,65526,65526,10,10,10)
        if opcode==35:emit(0)
    emit(0)
    return bytes(raw)


def original(path,row):
    health,impact,cost,lives,opcode,ticks=row
    image=NativeReference(path/'TFX.DAT');image.cpu.mem_map(0x300000,0x20000)
    definitions=[0x300000,0x301000];instances=[0x310000,0x311000]
    image.intercept(0xc8568,'Resolve the two supplied SSD instances without host resources.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,instances[(im.cpu.reg_read(r.UC_X86_REG_EAX)&65535)-1]),im.return_from()))
    for index,raw in enumerate((program(health,impact,False,0,0),program(99,cost,True,opcode,lives))):
        image.cpu.mem_write(definitions[index],raw)
        image.write(0x1b250+index*4,'<I',definitions[index])
        image.write(0x20b98,'<I',definitions[index]);image.write(0x20b9c,'<I',instances[index])
        image.write(0x20ba0,'<I',image.native(0xb6c84))
        image.call(0xb54dc,eax=definitions[index]+10+struct.unpack_from('<h',raw,10)[0]*2)
        image.cpu.mem_write(instances[index],struct.pack('<H',index))
    digest=14695981039346656037
    for tick in range(ticks):
        image.call(0xb752c,eax=1,edx=(-20)&0xffffffff,ebx=0,ecx=0,stack=(20,0,0))
        image.call(0xb76a8,eax=2,edx=0,ebx=0,ecx=0)
        source=bytes(image.cpu.mem_read(instances[0],16));victim=bytes(image.cpu.mem_read(instances[1],18))
        values=[struct.unpack_from('<H',source,5)[0],int(bool(source[2]&16)),struct.unpack_from('<H',victim,16)[0],int(bool(victim[2]&16)),int(bool(victim[15]&1)),1]
        for value in values:
            for byte in struct.pack('<I',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
    return digest


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args();rng=random.Random(0xb79c0)
    rows=[[rng.choice((0,1,5,10,32767,65535)),rng.choice((0,1,10,32767)),rng.choice((0,1,5,65535)),rng.choice((0,1,10,32767)),rng.choice((13,35)),16] for _ in range(128)]
    expected=[original(args.data_dir,row) for row in rows]
    result=subprocess.run([str(args.build/'contact_tests')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),text=True,capture_output=True,check=True)
    actual=[int(v) for v in result.stdout.split()]
    assert len(actual)==len(expected)
    for row,a,b in zip(rows,actual,expected):assert a==b,(row,a,b)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(' '.join(map(str,row+[digest]))+'\n' for row,digest in zip(rows,expected)))
        subprocess.run([str(args.build/'contact_tests'),str(args.save_fixture)],check=True)
    print(len(rows)*16,'native mutual-contact damage updates agree, including zero cost, signed thresholds and word wrap')


if __name__=='__main__':main()
