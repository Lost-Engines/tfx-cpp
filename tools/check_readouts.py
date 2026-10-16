#!/usr/bin/env python3
"""Compare clock, fuel, throttle and countermeasure instruments with original pixels."""
import argparse
from pathlib import Path
import random
import struct
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'))
from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT')
entry=next(item for item in archive.entries if item.identifier==archive.hash_name('spr/pitfont.spr'))
bank=archive.unpack(entry)
im=NativeReference(directory/'TFX.DAT',data_base=0x100000)
im.cpu.mem_map(0x300000,0x10000);im.cpu.mem_write(0x300000,bank)
im.intercept(0xc85a0,'Supply the decoded original pitfont bank at the external resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
im.write(0x12c2e,'<H',1)
video=VgaCapture(im,aperture=0xa0000)
im.call(0xde547) # Execute Watcom startup to install its actual floating printf handlers.
rng=random.Random(0x813c4)
cases=[]
# Values around each tick/format/colour boundary, including fractional fuel and throttle.
fuels=[0,1,9.49,9.5,9.51,998.5,999,999.49,999.5,999.99,1000,1000.5,2499.5,2499.99,2500,2500.5,9999,12000]
times=[0,53,54,539,540,3239,3240,194399,194400,54*3723,54*36000,0xffffffff]
positions=[(0,0),(1,0),(2,0),(3,0),(-7,0),(12,0),(0,-150),(0,8),(0,18),(0,27),(0,43),(0,46),(0,47),(0,60)]
for index in range(504):
    ticks=times[index%len(times)] if index<168 else rng.randrange(0x100000000)
    elapsed=rng.randrange(0x100000000);offset=(ticks-elapsed)&0xffffffff
    fuel=fuels[index%len(fuels)] if index<252 else rng.randrange(15000)+rng.random()
    throttle=[0,.01,.09,.1,.09999999,.9999999,1,1.2][index%8] if index<252 else rng.random()*1.2
    aircraft=index%3;ecm=bool(index&1);stealth=bool(index&2)
    chaff=[0,1,9,10,15,99,100,255][index%8];flares=[0,1,9,10,15,99,100,255][(index//8)%8]
    x,y=positions[index%len(positions)]
    cases.append((elapsed,offset,fuel,throttle,aircraft,int(ecm),int(stealth),chaff,flares,x,y))
rows=[' '.join(map(str,case)) for case in cases]
output=subprocess.check_output([str((args.build/'readout_probe').resolve()),str(directory)],input=('\n'.join(rows)+'\n').encode())
assert len(output)==len(cases)*128001
for index,case in enumerate(cases):
    elapsed,offset,fuel,throttle,aircraft,ecm,stealth,chaff,flares,x,y=case
    im.write(0x7618,'<I',elapsed);im.write(0x1199c,'<I',offset)
    im.write(0x14858,'<d',fuel);im.write(0x133f8,'<f',throttle)
    im.write(0x11b2a,'<H',aircraft);im.write(0x12f29,'<B',ecm);im.write(0x12f26,'<B',stealth)
    im.write(0x6c3e,'<2B',chaff,flares);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    for address in (0x813c4,0x81558,0x81694,0x8176c):im.call(address,limit=2000000)
    status={1:0,14:1,11:2}[im.read(0x7d78,'<B')[0]]
    want=bytes([status])+bytes(video.pixels())+bytes(video.coverage())
    got=output[index*128001:(index+1)*128001]
    assert got==want,(case,[(i,(i-1)%64000%320,(i-1)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Clock, fuel, throttle and countermeasure readouts agree in {len(cases)} complete native pixel/coverage/status frames')
