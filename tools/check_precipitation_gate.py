#!/usr/bin/env python3
"""Compare the original frame's storm/height/view/speed precipitation gate.

The frame fragment executes unchanged through its call/skip merge at 0x72316.
The rain painter is an observed output boundary, checked separately pixelwise.
"""
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
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x722c2);draws=[]
def observe(image):
 draws.append(struct.unpack('<h',struct.pack('<H',image.cpu.reg_read(r.UC_X86_REG_EAX)&65535))[0]);image.return_from()
im.intercept(0x78d8c,'Observe the native frame rain request, independently checked through its complete VGA pixel consumer.',observe)
rows=[];expected=[];fixtures=[]
for case in range(8192):
 enabled=rng.choice((0,1,2,255));storm=rng.choice((0,1,2,255));layer=rng.choice((-32768,-2400,-1,0,32767))
 y=rng.choice((float(layer-1),float(layer),float(layer+1),float('nan'),float('inf'),float('-inf'))) if case<2048 else rng.uniform(-40000,40000)
 height=struct.unpack('<I',struct.pack('<f',y))[0]
 view=rng.randrange(29);speed=rng.choice((-2147483648,-1000,-201,-200,-1,0,1,399,400,401,65535,65536,2147483647)) if case<2048 else rng.randrange(-2147483648,2147483648)
 row=[enabled,storm,layer,height,view,speed];rows.append(row)
 im.write(0x8f31,'<B',enabled);im.write(0x8f33,'<B',storm);im.write(0xe75a,'<h',layer);im.write(0x13428,'<I',height);im.write(0x87b6,'<h',view);im.write(0x13444,'<i',speed)
 draws.clear();im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x722c2),im.native(0x72316),count=1000)
 assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x72316);assert len(draws)<=1
 value=draws[0] if draws else 65536;expected.append(value)
 if case<128 or case%67==0:fixtures.append(row+[value])
actual=subprocess.check_output([str((a.build/'precipitation_probe').resolve()),'--gate'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows)
for case,(line,value) in enumerate(zip(actual,expected)):assert int(line)==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 original main-frame precipitation gates agree: realism toggle, storm, strict player/cloud height including unordered values, excluded views, signed speed division and narrowed request count')
