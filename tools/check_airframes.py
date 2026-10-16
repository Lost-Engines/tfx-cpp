#!/usr/bin/env python3
"""Compare decoded aircraft store geometry with all three original initializers."""
import argparse
from pathlib import Path
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args()
image=NativeReference(args.data_dir/'TFX.DAT');image.call(0xde851)
expected=[]
for preset in (0x98234,0x97598,0x96918):
    image.call(preset)
    expected.append([image.read(at,'<Q')[0] for at in (0x142c8,0x14258,0x14850)]+[image.read(base+slot*8,'<Q')[0] for slot in range(10) for base in (0x13bd0,0x13c20,0x13c70)])
actual=subprocess.check_output([str((args.build/'airframe_probe').resolve()),str(args.data_dir/'TFX.DAT')],text=True).splitlines()
assert [list(map(int,line.split())) for line in actual]==expected
print('Aircraft moment, fuel capacity and all 30 mount vectors agree bit for bit with the native initializers')
