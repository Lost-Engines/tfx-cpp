#!/usr/bin/env python3
"""Compare a real factory's collision/animation/draw emissions with native SSDs.

The C++ scene uses retail terrain, a supplied damaging point and real effect
models. Native initialization, collision bytecode, persistent parameter streams,
draw bytecode and placed emission helpers execute. Resource/model drawing,
the separate querying object's response and allocation output are boundaries.
This is a controlled scene comparison, not a complete mission or pixel trace.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();data=a.research/'installs/cd_1994_09/TFX'
run=subprocess.run([str((a.build/'effect_scene_probe').resolve()),str(data)],capture_output=True,text=True,check=True)
lines=run.stdout.splitlines();name,heading,*numbers=lines[0].split();heading=int(heading);origin=list(map(int,numbers[:3]));point=list(map(int,numbers[3:6]));reference=list(map(int,numbers[6:9]));actual=[list(map(int,line.split())) for line in lines[1:]]
raw=(a.research/'extracted/cd_1994_09/resources/ss'/f'{name}.ssd').read_bytes();parts=raw[1];flags=int.from_bytes(raw[4:6],'little');table=10+raw[9]*6
entries=[table+i*2+struct.unpack_from('<h',raw,table+i*2)[0]*2 for i in range(raw[8])]
im=NativeReference(data/'TFX.DAT');im.cpu.mem_map(0x300000,0x20000);definition,instance=0x300000,0x310000;im.cpu.mem_write(definition,raw)
for part in range(parts):im.cpu.mem_write(instance+16+29*part+9,b'\xff\xff')
im.write(0x20b98,'<I',definition);im.write(0x20b9c,'<I',instance);im.write(0x20ba0,'<I',im.native(0xb6c84));im.write(0x20c4a,'<H',0);im.write(0x1b250,'<I',definition)
def bind(im):im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EAX),struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EDX)));im.return_from()
im.intercept(0xb4d3c,'Supply stable symbolic model handles; resource geometry does not affect SSD state.',bind)
im.intercept(0xc8568,'Resolve the single controlled factory instance.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,instance),im.return_from()))
for file in (0xb635c,0xb6438,0xb65b0,0xb668c,0xb6810,0xb68dc,0xb6a44):
 im.intercept(file,'Observe the independently checked model-part draw boundary without loading the native rasterizer.',lambda im:im.return_from())
im.intercept(0xb7a30,'The separate querying projectile is outside this controlled factory SSD comparison.',lambda im:im.return_from())
im.write(0xac3c,'<I',im.native(0xb7a30))
im.cpu.emu_start(im.native(0x7589a),im.native(0x758b8),count=3)
assert im.read(0xabf4,'<3I')==(im.data+0x13424,im.data+0x13430,im.data+0x1343c)
for offset,value in zip((0x13424,0x13430,0x1343c),reference):im.write(offset,'<i',value)
im.write(0x20bb0,'<3H',*[v&65535 for v in origin]);im.write(0xac18,'<I',im.read(0xac1c+heading//16384*4,'<I')[0]);im.write(0xac10,'<I',im.native(0x7b0cc))
phase=[-1];expected=[]
def allocation(im):
 p=struct.unpack('<3i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),12));kind=im.cpu.reg_read(r.UC_X86_REG_EDX)
 expected.append([phase[0],kind,*[struct.unpack('<h',struct.pack('<H',v&65535))[0] for v in p]]);im.return_from()
im.intercept(0x7b144,'Observe placed temporary-effect allocation; pool state/reset/draw delivery has separate checks.',allocation)
im.call(0xb54dc,eax=definition+entries[0]);assert not expected
im.write(0x20c4c,'<2B',0,1);im.write(0x20c46,'<H',32767);im.write(0x20b8c,'<6h',*point,*point);im.write(0xabe4,'<h',0)
im.call(0xb54dc,eax=definition+entries[2])
def range_context():
 delta=[struct.unpack('<h',struct.pack('<H',(a-b)&65535))[0] for a,b in zip(origin,reference)]
 value=im.call(0xcbe94,eax=delta[0]&0xffffffff,edx=delta[1]&0xffffffff,ebx=delta[2]&0xffffffff)
 im.write(0xabe4,'<H',value&65535)
for frame in range(32):
 phase[0]=frame;range_context()
 for part in range(parts):
  for parameter in range(8 if flags&256 else 1):im.call(0xb6ce0,eax=part,edx=parameter)
 range_context();im.call(0xb54dc,eax=definition+entries[1])
assert actual==expected,(actual,expected)
print(run.stderr.strip())
print(f'Original factory collision, 32 persistent animation/draw passes and all {len(expected)} placed emission requests agree; real C++ pool models join the same-frame draw queue')
