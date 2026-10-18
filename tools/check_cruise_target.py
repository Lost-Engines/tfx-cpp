#!/usr/bin/env python3
"""Compare AGM-109H acquisition with original 93128, including its real projector.

Only camera/player/mission destination inputs are supplied. Native designation,
contact/guidance pointers, forced height, range branch and projection execute.
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
p.add_argument('--save-fixture',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0x93128)
rows=[];expected=[]
def signed(value):return struct.unpack('<i',struct.pack('<I',value&0xffffffff))[0]
for index in range(4096):
    destination=[rng.randrange(-2147483648,2147483648)for _ in range(2)]
    player=[rng.randrange(-2147483648,2147483648)for _ in range(3)]
    camera=[rng.randrange(-2147483648,2147483648)for _ in range(3)]
    matrix=[rng.randrange(-32768,32768)for _ in range(9)];origin=[rng.randrange(-32768,32768)for _ in range(2)]
    if index<256:
        destination=[0,1000*256];player=[0,0,1000]
        axis=(index//16)%2*2
        player[axis]=signed(player[axis]+(-32768,-32767,-32766,0,32766,32767,32768,2147483647)[index%8])
        matrix=[32767,0,0,0,32767,0,0,0,32767];origin=[159,56];camera=[0,0,(index%32-16)*1000*65536]
    if index in (0,1):player=[-2147483648,0,1000]if index==0 else[0,0,signed(1000-2147483648)]
    rows.append(['C',*player,*destination,*matrix,*camera,*origin])
    address=im.native(0x70aa4+0x47c4a);im.cpu.mem_write(address,struct.pack('<9h',*matrix));im.cpu.reg_write(r.UC_X86_REG_ESI,address);im.call(0xb959f)
    im.call(0xb9ab9,stack=tuple(n&0xffffffff for n in reversed(camera)));im.call(0xb94da,stack=tuple(n&0xffffffff for n in [*origin,319,199]))
    for field,value in zip((0x13424,0x13430,0x1343c),player):im.write(field,'<i',value)
    im.write(0x16e84,'<3i',destination[0],123456,destination[1]);im.write(0x135a0,'<3i',1,2,3)
    for field in (0x8840,0x11108,0x135c8,0x135d0):im.write(field,'<I',0)
    im.write(0x135d4,'<2h',123,456);im.write(0x8860,'<B',1)
    im.call(0x93128)
    assert all(im.read(field,'<I')[0]==im.data+0x135a0 for field in (0x8840,0x11108,0x135c8,0x135d0))
    assert im.read(0x135d4,'<2h')==(123,456) and im.read(0x8860,'<B')==(1,)
    assert im.read(0x16e88,'<i')==(-2560,)
    expected.append([*im.read(0x135a0,'<3i'),*im.read(0x135c0,'<2i'),*im.read(0x135cc,'<2h')])
actual=subprocess.check_output([str((a.build/'ground_probe').resolve())],input=''.join(' '.join(map(str,row))+'\n'for row in rows).encode()).splitlines()
assert len(actual)==len(expected)
for index,(got,want)in enumerate(zip(actual,expected)):assert list(map(int,got.split()))==want,(index,rows[index],got,want)
if a.save_fixture:
    lines=[]
    for index in [*range(64),*range(256,4096,31)]:
        digest=14695981039346656037
        for value in expected[index]:
            for byte in struct.pack('<I',value&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        lines.append(' '.join(map(str,[*rows[index],digest]))+'\n')
    a.save_fixture.write_text(''.join(lines))
    subprocess.run([str((a.build/'ground_probe').resolve()),str(a.save_fixture)],check=True)
print('4096 original AGM-109H designation/guidance/projection cases agree, including exact range boundaries and retained lock timers')
