#!/usr/bin/env python3
"""Compare original BINGO/PULL UP line alerts, fuel requests and retained timer.

Runs the original alert request, pre-fault fuel gate and complete line painter.
Valid physical-screen offsets, the ignored line viewport, elapsed ticks, draw
count and external PULL UP requests are supplied. Native lines have no clipping;
out-of-screen offsets which write beyond video memory are excluded. Terrain-risk detection and refuelling/forward-HUD call ordering
are separate consumers, rather than invented inputs from approximate geometry.
"""
import argparse
import math
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();directory=a.research/'installs/cd_1994_09/TFX';im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000)
rng=random.Random(0x7de00);cases=[]
for index in range(512):
    dx,dy=[(0,0),(0,28),(0,54),(1,0),(-100,0),(100,0),(0,100),(20,40),(-20,1)][index%9]
    bounds=[(0,0,319,199),(115,12,214,77),(130,45,180,65),(0,0,159,99)][(index//9)%4]
    fuel=[1000,500,math.nextafter(500,0),math.nextafter(500,math.inf),0,-1][index%6] if index<128 else rng.uniform(-100,1000)
    cases.append([int(index%64==0),index%2,[0,1,108,-1,32767,-32768][(index//64)%6],index%2 if index%7==0 else -1,fuel,[0,1,4,107,108,109,32767,65535][index%8],dx,dy,*bounds,index%3,index%256])
output=subprocess.check_output([str((a.build/'hud_alert_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode());stride=128008;assert len(output)==len(cases)*stride
vertices=(0x6fbe,0x6f12);segments=(0x702e,0x6f72)
def request(kind):im.call(0x7dde4,eax=im.data+vertices[kind],edx=im.data+segments[kind])
for index,row in enumerate(cases):
    reset,alert,remaining,show,fuel,elapsed,dx,dy,lx,ly,hx,hy,draws,background=row
    if reset:request(alert);im.write(0x12c1c,'<h',remaining)
    if show>=0:request(show)
    im.write(0x14858,'<d',fuel)
    # Execute the unmodified fuel test/request before its HUD-fault gate.
    im.cpu.mem_write(im.STACK,struct.pack('<I',im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    im.cpu.emu_start(im.native(0x80100),im.native(0x80120),count=10000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x80120)
    im.write(0x13476,'<H',elapsed);im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy);im.call(0xb9238,stack=(lx,hx,ly,hy));video.reset()
    for plane in video.planes:plane[:]=bytes([background])*16000
    for _ in range(draws):
        if im.read(0x12c1c,'<h')[0]:
            try:im.call(0x7de00,limit=500000)
            except RuntimeError as error:raise RuntimeError((index,row,str(error))) from error
    kind=int(im.read(0x12c0c,'<I')[0]==im.data+vertices[1])
    expected=struct.pack('<2i',kind,*im.read(0x12c1c,'<h'))+bytes(video.pixels())+bytes(video.coverage());actual=output[index*stride:(index+1)*stride]
    assert actual==expected,(index,row,struct.unpack('<2i',actual[:8]),struct.unpack('<2i',expected[:8]),[(i,(i-8)%64000%320,(i-8)%64000//320,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:20])
print(f'BINGO/PULL UP shapes, fuel requests, pixels/coverage and retained timer agree in {len(cases)} original frames')
