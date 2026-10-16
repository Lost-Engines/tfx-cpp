#!/usr/bin/env python3
"""Execute original Watcom FPU detection/reset and identify precision writes.

This is the real 0xde851 -> 0xde81e -> 0xea0fc startup branch, with unmodified
FNINIT, infinity comparison, FLDCW and stores. No dependencies are intercepted.
"""
import argparse
from pathlib import Path
import struct
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
assert im.read(0xe084,'<H')[0]==0x127f
assert im.read(0xacc8,'<B')[0]==0
im.call(0xde851)
assert im.cpu.reg_read(r.UC_X86_REG_FPCW)==0x127f
assert im.read(0xacc8,'<B')[0]==3 and im.read(0xacc9,'<B')[0]==3
assert (im.cpu.reg_read(r.UC_X86_REG_FPCW)>>8)&3==2
print('Original Watcom startup agrees: detected 387 path, CW 0x127f, nearest rounding, 53-bit arithmetic precision; no intercepted dependencies')
