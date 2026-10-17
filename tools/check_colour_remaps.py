#!/usr/bin/env python3
"""Compare native distance-remap rows and complete original coltab initialization.

Native CC019..CC040 executes with the retail C54F6(9) setup and supplied raw
camera depths. The original D7954 loader then runs through supplied archive I/O;
its complete 4,096-byte table is compared with the live C++ asset owner.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_environment import environment_image

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0xcc019);im.call(0xc54f6,stack=(9,));rows=[];expected=[];fixtures=[]
for case in range(16384):
 depth=((case//3-128)*(1<<25)+(case%3-1)) if case<768 else rng.randrange(-2147483648,2147483648)
 depth=((depth+2147483648)&4294967295)-2147483648;rows.append(depth)
 im.cpu.reg_write(r.UC_X86_REG_EDX,depth&0xffffffff);im.cpu.reg_write(r.UC_X86_REG_EBX,0);im.cpu.reg_write(r.UC_X86_REG_EAX,rng.randrange(4294967296));im.cpu.emu_start(im.native(0xcc019),im.native(0xcc040),count=100)
 value=im.cpu.mem_read(im.native(0x70aa4+0x51396),1)[0];expected.append(value)
 if case<256 or case%97==0:fixtures.append([depth,value])
actual=subprocess.check_output([str((a.build/'colour_remap_probe').resolve())],input=('\n'.join(map(str,rows))+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,value) in enumerate(zip(actual,expected)):assert int(line)==value,(case,rows[case],line,value)
image=environment_image(a.research,'yugos_n');image.call(0xd7954,limit=100000)
want=bytes(image.cpu.mem_read(image.data+0x24c9c,4096));got=subprocess.check_output([str((a.build/'colour_remap_probe').resolve()),'--assets',str(a.research/'installs/cd_1994_09/TFX')]);assert got==want
assert want[:256]==bytes(range(256));assert want[15*256:]!=bytes(range(256))
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('16384 original queued-model distance remap rows and all 4096 loaded colour-table indices agree, including signed-depth wrap, row boundaries, near identity and far remaps')
