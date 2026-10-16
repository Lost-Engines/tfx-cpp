#!/usr/bin/env python3
"""Compare native arming placement, clearing, escape fallback and hit regions."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_arming import NativeArming

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();native=NativeArming(args.data_dir,args.research);im=native.image;cpu=im.cpu
picked=[0]
im.intercept(0xb752c,'Supply the dragged-store segment; collision and 3D selection are separate boundaries.',lambda im:im.return_from(stack_bytes=12))
im.intercept(0xb76a8,'Supply the selected aircraft mount; original placement and clearing code execute.',lambda im:(im.write(0xabec,'<h',picked[0]),im.return_from()))
base=im.native(0x70aa4+0x47c94)
def snapshot():
    result=[];placeholder=im.read(0x7f28,'<H')[0]
    for slot in range(10):
        handle=struct.unpack('<H',cpu.mem_read(base+slot*2,2))[0]
        result.extend([*im.read(0x13374+slot*2,'<2B'),int(handle!=65535),int(handle==placeholder)])
    return result
rng=random.Random(0x8a464);cases=[];expected=[]
for aircraft in range(3):
    native.initialise_aircraft(aircraft);im.write(0x11b40,'<B',0)
    for case in range(1024):
        weapon=case%22+1;slot=rng.randrange(10);picked[0]=slot
        stores=[-1]*10 if case<22 else [rng.randrange(1,23) if rng.randrange(4)==0 else -1 for _ in range(10)]
        native.inventory(stores);im.write(0x1330e,'<h',weapon);im.call(0x8a2ec)
        callback=im.read(0x132fc,'<I')[0]
        mode={im.native(0x8a464):2,im.native(0x89388):5}[callback]
        values=[mode,*snapshot()]
        native.buttons=1;im.call(0x8a464,limit=1000000);values.extend(snapshot())
        im.call(0x898ec,limit=1000000);values.extend(snapshot())
        # Execute the original Escape inventory test through its loop exit,
        # then the original placeholder cleanup. No copied branch logic.
        cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
        cpu.emu_start(im.native(0x8b55e),im.native(0x8b591),count=200000)
        assert cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8b591)
        im.call(0x8b43c);values.extend(snapshot())
        cases.append([aircraft,weapon,slot,*stores]);expected.append(values)
requests=''.join(' '.join(map(str,case))+'\n' for case in cases)
actual=subprocess.check_output([str((args.build/'arming_controls_probe').resolve()),str(args.data_dir)],input=requests.encode()).splitlines()
assert len(actual)==len(expected)
for case,got,want in zip(cases,actual,expected):assert list(map(int,got.split()))==want,(case,list(map(int,got.split())),want)
# The original callback dispatcher is captured before its input-release wait.
native.buttons=1
positions=[(x,y) for x in range(0,320,3) for y in range(0,200,3)]
positions += [(x+dx,y+dy) for x,y in [(20,19),(180,181),(302,16),(313,178),(210,21),(303,46),(85,196),(117,202)] for dx in (-1,0,1) for dy in (-1,0,1)]
callbacks=[0x89210,0x89590,0x8978c,0x89658,0x89b00,0x898ec,0x89488,0x89b2c,0x89b4c,0x89194]
row_callbacks=[0x8a350,0x8a374,0x8a3a4,0x8a3d4,0x8a404,0x8a434]
expected=[]
for native.position in positions:
    im.write(0x132fc,'<I',0)
    cpu.reg_write(r.UC_X86_REG_ESP,im.STACK)
    cpu.emu_start(im.native(0x8b2c0),im.native(0x8b39f),count=20000)
    callback=im.read(0x132fc,'<I')[0]
    if not callback:expected.append([-1,0])
    elif callback in [im.native(file) for file in callbacks]:expected.append([[im.native(file) for file in callbacks].index(callback),0])
    else:expected.append([10,[im.native(file) for file in row_callbacks].index(callback)])
actual=subprocess.check_output([str((args.build/'arming_controls_probe').resolve()),str(args.data_dir),'--hits'],input=''.join(f'{x} {y}\n' for x,y in positions).encode()).splitlines()
assert len(actual)==len(expected)==len(positions)
for position,got,want in zip(positions,actual,expected):assert list(map(int,got.split()))==want,(position,got,want)
print(f'Arming controls agree in {len(cases)} native placement/clearing/exit sequences and {len(positions)} native hit tests')
