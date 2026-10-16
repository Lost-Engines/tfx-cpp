#!/usr/bin/env python3
"""Compare the original view/night palette selector and retained upload latches.

Runs the unmodified selection tail at 0x73b76 with its caller's saved-register
stack supplied. Hardware palette upload is observed without performing I/O;
altitude/flash/blackout palette generation is outside this selector boundary.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--write-fixture',type=Path)
a=parser.parse_args();fixtures=[];im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');uploads=[]
def upload(image):
    pointer,=struct.unpack('<I',image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_ESP)+4,4))
    assert pointer in (image.data+0xf988,image.data+0xea88),hex(pointer)
    uploads.append(int(pointer==image.data+0xea88));image.return_from()
im.intercept(0xc770c,'Observe selected palette at the hardware-upload boundary; no VGA I/O',upload)
rng=random.Random(0x73b76);cases=[]
for view in range(29):
    for flags in range(64):
        cases.append([1,flags&1,(flags>>1)&1,view,(flags>>2)&1,(flags>>3)&1,(flags>>4)&1,(flags>>5)&1])
for index in range(4096):cases.append([0,int(index%13==0),0,rng.randrange(29),rng.randrange(2),rng.randrange(2),rng.randrange(2),rng.randrange(2)])
output=subprocess.check_output([str((a.build/'palette_selection_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for index,(row,line) in enumerate(zip(cases,output)):
    reset,dirty,infrared,view,projectiles,available,night,night_vision=row
    if reset:im.write(0x5950,'<B',dirty);im.write(0x5955,'<B',infrared)
    elif dirty:im.write(0x5950,'<B',1)
    initial_dirty,=im.read(0x5950,'<B');initial_infrared,=im.read(0x5955,'<B')
    im.write(0x87b6,'<h',view);im.write(0x16e78,'<I',projectiles);im.write(0xe774,'<H',available);im.write(0x5953,'<B',night_vision)
    im.cpu.mem_write(im.native(0x70aa4+0x47c82),struct.pack('<H',128 if night else 0))
    # Original epilogue restores EBP, ESI, ECX and EBX before returning.
    im.cpu.mem_write(im.STACK,struct.pack('<5I',0,0,0,0,im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    uploads.clear();im.cpu.emu_start(im.native(0x73b76),im.RETURN,count=2000)
    assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.RETURN
    expected=[uploads[0] if uploads else -1,*im.read(0x5950,'<B'),*im.read(0x5955,'<B')]
    if (index<1856 and index%64 in (0,4,8,12,16,24,32,40,48,60,61,62,63)) or index>=len(cases)-64:fixtures.append([1,initial_dirty,initial_infrared,*row[3:],*expected])
    assert len(uploads)<=1
    assert list(map(int,line.split()))==expected,(index,row,line,expected)
if a.write_fixture:a.write_fixture.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'Native view/night palette requests and retained upload latches agree in {len(cases)} updates across all 29 views')
