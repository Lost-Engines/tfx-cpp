#!/usr/bin/env python3
"""Compare the native configuration caller's detail-bit updates, preserving other flags."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0x94d6f)
rows=[(rng.randrange(65536),[0,1,2,rng.randrange(3,256)][i%4]) for i in range(4096)]
actual=list(map(int,subprocess.check_output([str((a.build/'detail_status_probe').resolve())],input=('\n'.join(f'{status} {detail}' for status,detail in rows)+'\n').encode()).split()))
fixtures=[]
for index,((status,detail),value) in enumerate(zip(rows,actual)):
 im.cpu.mem_write(im.native(0x70aa4+0x47c82),struct.pack('<H',status));im.write(0x8864,'<B',detail)
 im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK)
 im.cpu.mem_write(im.STACK-4,bytes([(detail+1)&255]))
 im.cpu.emu_start(im.native(0x94d6f),im.native(0x94daf),count=100)
 assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x94daf)
 expected=struct.unpack('<H',im.cpu.mem_read(im.native(0x70aa4+0x47c82),2))[0]
 assert value==expected,(index,status,detail,value,expected)
 if index<128:fixtures.append(f'{status} {detail} {expected}')
assert len(actual)==len(rows)
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(rows)} original detail-setting caller cases agree, retaining night and all unrelated shape-status bits')
