#!/usr/bin/env python3
"""Compare complete original signed-anchor placement, including per-product rounding."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args();rng=random.Random(0xb81de)
    image=NativeReference(args.data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,4096)
    rows=[];expected=[]
    for index in range(4096):
        row=[*(rng.randrange(-2147483648,2147483648) for _ in range(3)),*(rng.randrange(65536) for _ in range(3)),*(rng.randrange(-32768,32768) for _ in range(3))]
        image.cpu.mem_write(0x300000,struct.pack('<3i',*row[:3]));image.cpu.mem_write(0x300100,struct.pack('<3h',*row[6:]))
        image.call(0xb81de,stack=(0x300000,*row[3:6],0x300100))
        rows.append(row);expected.append(list(struct.unpack('<3i',image.cpu.mem_read(0x300000,12))))
    result=subprocess.run([str(args.build/'anchor_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),text=True,capture_output=True,check=True)
    actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()]
    assert len(actual)==len(expected)
    for index,(a,b) in enumerate(zip(actual,expected)):assert a==b,(index,rows[index],a,b)
    if args.save_fixture:
        args.save_fixture.write_text(''.join(' '.join(map(str,row+output))+'\n' for row,output in zip(rows[:512],expected[:512])))
        subprocess.run([str(args.build/'anchor_probe'),str(args.save_fixture)],check=True)
    print(len(rows),'native muzzle/store anchor transforms agree, including wrap and signed product rounding')


if __name__=='__main__':main()
