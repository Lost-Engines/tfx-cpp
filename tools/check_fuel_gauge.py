#!/usr/bin/env python3
"""Compare the outer player callback's fuel-gauge and burn smoothing arithmetic."""
import argparse
from pathlib import Path
import random
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();im=NativeReference(args.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0x8fa23)
cases=[(before,burn,after) for before in (-32768,0,800,9999,32767) for burn in (-32768,0,2,10,32767) for after in (-32768,0,799,800,9999,32767)]
cases.extend(tuple(rng.randrange(-32768,32768) for _ in range(3)) for _ in range(4096))
expected=[]
for before,burn,after in cases:
    im.write(0x6c3a,'<2h',burn,after);im.cpu.reg_write(r.UC_X86_REG_EBX,before&65535)
    im.cpu.emu_start(im.native(0x8fa23),im.native(0x8fa69),count=100)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8fa69)
    smoothed,reading=im.read(0x6c3a,'<2h');expected.append([reading,smoothed])
output=subprocess.check_output([str((args.build/'fuel_gauge_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).splitlines()
assert len(output)==len(expected)
for row,got,want in zip(cases,output,expected):assert list(map(int,got.split()))==want,(row,got,want)
print(f'Fuel gauge and burn smoothing agree in {len(cases)} native cases')
