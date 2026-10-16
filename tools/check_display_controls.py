#!/usr/bin/env python3
"""Compare MFD and radar-range key callbacks and draw-time normalization."""
import argparse
from pathlib import Path
import random
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
im=NativeReference(directory/'TFX.DAT');rng=random.Random(0x85d9c);cases=[];expected=[]
for action in range(5):
    for aircraft in range(3):
        for index in range(128):
            values=[rng.choice((0,1,2,3,4,5,6,7,8,9,32767,32768,65535)) for _ in range(5)]
            targets=index%2;category=(0,3,7,13)[index%4]
            cases.append([*values,action,aircraft,targets,category])
            left,centre,right,horizontal,bvr=values
            im.write(0x713a,'<3H',left,centre,right);im.write(0x7d7c,'<2H',horizontal,bvr)
            im.write(0x11b2a,'<H',aircraft);im.write(0x11b22,'<h',targets)
            im.write(0x93b0,'<h',0);im.write(0x13374,'<B',0);im.write(0x80b9,'<B',category)
            if action==4:
                im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
                im.cpu.emu_start(im.native(0x8041a),im.native(0x80453),count=100)
                assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x80453)
            else:im.call((0x85d9c,0x85dc4,0x85dec,0x861c0)[action])
            expected.append([*im.read(0x713a,'<3H'),*im.read(0x7d7c,'<2H')])
output=subprocess.check_output([str((args.build/'hud_probe').resolve()),str(directory),'yugosmap','--controls'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).splitlines()
assert len(output)==len(expected)
for row,got,want in zip(cases,output,expected):assert list(map(int,got.split()))==want,(row,got,want)
print(f'MFD/radar key callbacks and draw normalization agree in {len(cases)} native cases')
