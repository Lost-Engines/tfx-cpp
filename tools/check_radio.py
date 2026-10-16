#!/usr/bin/env python3
"""Compare original scrolling-radio state sequences and complete VGA frames."""
import argparse
from pathlib import Path
import random
import shlex
import struct
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--frames',action='store_true')
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x1000);im.cpu.mem_map(0x400000,0x10000)
im.cpu.mem_write(0x400000,archive.unpack(entries[archive.hash_name('spr/pitfont.spr')]))
im.write(0x12c2e,'<H',1)
im.intercept(0xc85a0,'Supply the unchanged original pitfont bank at its resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x400000),im.return_from()))
shown=[]
def observe(im,register):
    pointer=im.cpu.reg_read(register);shown.append(bytes(im.cpu.mem_read(pointer,32)).split(b'\0',1)[0].decode('latin1'))
im.intercept(0x826b4,'Observe the original coloured-font radio window without replacing its painter.',lambda im:observe(im,r.UC_X86_REG_EBX))
im.intercept(0x87154,'Observe the original HUD-font radio window without replacing its painter.',lambda im:observe(im,r.UC_X86_REG_ECX))
im.call(0x81174)
rng=random.Random(0x81290);cases=[]
messages=['','ABC','AWACS CONFIRMS INBOUND HOSTILES','Talk to me, Goose!','FUEL 25% - BREAK LEFT.','GO\xd6SE 123','A\0DISCARDED','LINE ONE\nLINE TWO','X'*100]
for index in range(512 if args.frames else 4096):
    action=1 if index==0 else rng.choice([0]*15+[1,2,3,4])
    ticks=[0,1,3,4,5,19,20,21,54,55][index%10];warp=(index//11)%2;view=[0,1,28][index%3]
    dx,dy=[(0,0),(1,0),(2,0),(3,0),(-125,0),(12,0),(0,-123),(0,28),(0,72),(0,100)][index%10]
    cases.append([action,ticks,warp,view,dx,dy,messages[index%len(messages)]])
def quoted(message):return '"'+message.replace('\\','\\\\').replace('"','\\"')+'"'
request='\n'.join(' '.join(map(str,row[:6]))+' '+quoted(row[6]) for row in cases)+'\n'
output=subprocess.check_output([str((args.build/'radio_probe').resolve()),str(directory),*(['frames'] if args.frames else [])],input=request.encode('latin1'))
if not args.frames:output=output.decode().splitlines();assert len(output)==len(cases)
else:assert len(output)==len(cases)*128024
for index,(action,ticks,warp,view,dx,dy,message) in enumerate(cases):
    im.cpu.mem_write(0x300000,message.encode('latin1')+b'\0')
    if action in (1,2):im.call(0x81198 if action==1 else 0x81254,eax=0x300000)
    elif action==3:im.call(0x81174)
    elif action==4:im.call(0x81268)
    im.write(0x13476,'<H',ticks);im.write(0xe780,'<B',warp);im.write(0x87b6,'<H',view);im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    im.call(0xc0634,stack=(199,0,319,0));video.reset();shown.clear()
    for plane in video.planes:plane[:]=bytes([99])*16000
    if not im.read(0x7612,'<B')[0]:im.call(0x81290,limit=1000000)
    assert len(shown)<=1,(index,shown)
    state=[im.read(0x7610,'<h')[0],im.read(0x761c,'<h')[0],im.read(0x7612,'<B')[0],im.read(0x7613,'<B')[0],im.read(0x7614,'<B')[0],bool(shown)]
    if args.frames:
        want=struct.pack('<6i',*state)+bytes(video.pixels())+bytes(video.coverage());got=output[index*128024:(index+1)*128024]
        assert got==want,(index,action,ticks,[(i,(i-24)%64000%320,(i-24)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
    else:
        actual=shlex.split(output[index]);got=[*map(int,actual[:6]),actual[6]];want=[*state,shown[0] if shown else '']
        assert got==want,(index,action,ticks,got,want)
print(f'Original radio {"complete pixel/coverage frames" if args.frames else "state/window sequence"} agree across {len(cases)} updates, including replay, looping, filtering and both fonts')
