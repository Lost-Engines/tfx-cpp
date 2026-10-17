#!/usr/bin/env python3
"""Compare complete native form and option-button pixels and edge coverage."""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference
from native_vga import VgaCapture

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
p.add_argument('--build', type=Path, default=Path('build'))
a = p.parse_args()
path = a.research / 'installs/cd_1994_09/TFX/TFX.DAT'
im = NativeReference(path, data_base=0x100000)
vga = VgaCapture(im)
im.cpu.mem_map(0x300000,0x2000)
im.write(0x24176,'<H',240)
rng = random.Random(0xcfe4c)
rows = []
for index in range(64):
    rows.append(([0,index%3,index%4,rng.randrange(12,34),rng.randrange(8,18),index%16,0,0,1,1,15,11,1],''))
for index in range(256):
    text = rng.choice(['NONE','REDUCED','REALISTIC','OFF','ON','MILITARY SPEC','<','>','RETURN TO GAME','','\xc0\xc9\xd6\xdc'])
    rows.append(([1,0,2,38,20,9,rng.randrange(0,26),rng.randrange(0,15),rng.randrange(1,8),rng.randrange(1,4),rng.randrange(16),rng.randrange(16),[1,3,110][index%3]],text))
output = subprocess.check_output([str((a.build/'dialogue_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,fields))+'|'+text for fields,text in rows)+'\n').encode('latin1'))
assert len(output)==len(rows)*64000
for index,(fields,text) in enumerate(rows):
    kind,fx,fy,fw,fh,fb,x,y,w,h,foreground,background,border=fields
    im.cpu.mem_write(0x300000,bytes(36))
    im.cpu.mem_write(0x300100,bytes(36))
    im.cpu.mem_write(0x300008,bytes([fx,fy,fw,fh,15,fb]))
    vga.reset()
    if kind==0:
        im.call(0xcf87c,eax=0x300000,edx=1,limit=1000000)
    else:
        im.cpu.mem_write(0x300105,bytes([x,y,w,h,foreground,background]))
        im.cpu.mem_write(0x301000,text.encode('latin1')+b'\0')
        import struct
        im.cpu.mem_write(0x30010b,struct.pack('<I',0x301000))
        im.cpu.mem_write(0x30010f,bytes([border]))
        im.call(0xcfe4c,eax=0x300100,edx=0x300000,limit=1000000)
    expected=vga.pixels()
    actual=output[index*64000:(index+1)*64000]
    assert actual==expected,(index,fields,text,[(i%320,i//320,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:30],sum(x!=y for x,y in zip(actual,expected)))
print(f'{len(rows)} complete native dialog frames agree: form bodies, double bevels, raised/sunken controls, outlines, proportional labels and edge coverage')
