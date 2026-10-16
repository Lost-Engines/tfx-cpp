#!/usr/bin/env python3
"""Compare the controls MFD and autopilot indicator with complete original pixels."""
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
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={item.identifier:item for item in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x20000)
for handle,(name,field) in enumerate((('compdisp',0x12c2a),('autolite',0x12c22)),1):
    im.cpu.mem_write(0x300000+(handle-1)*0x8000,archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]))
    im.write(field,'<H',handle)
im.intercept(0xc8568,'Supply original control-display and autopilot sprite banks at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x8000),im.return_from()))
video=VgaCapture(im,aperture=0xa0000);im.call(0xde547)
rng=random.Random(0x88778);cases=[]
# Deflection pointers use the original unclipped VGA line painter; keep its
# endpoints on screen rather than invoking undefined reads past the scanline table.
positions=[(0,0),(1,0),(2,0),(3,0),(-10,0),(12,0),(0,-100),(0,8),(0,20),(0,28),(0,36),(0,40)]
for index in range(768):
    side=index%2;aircraft=(index//2)%3;variant=index//6
    enabled=(variant//8)%2;mode=[0,1,2,3,4,5,65535,32768][variant%8]
    configuration=[0,1,2,3,4,5,65535,32768][(variant//2)%8]
    x,y=positions[(variant//4)%len(positions)]
    surfaces=[rng.uniform(-2,2) for _ in range(2)]
    raptor=[rng.uniform(-.4,.4) for _ in range(2)]
    heading=rng.randrange(65536);waypoint=rng.randrange(-20,200)
    height=-rng.uniform(0,20000);speed=rng.uniform(0,1000)
    cases.append([8,side,aircraft,0,0,0,0,0,0,0,x,y,0,0,*([2]*12),0,1,0,*([0]*22),*surfaces,*raptor,enabled,mode,configuration,heading,waypoint,height,speed])
output=subprocess.check_output([str((args.build/'mfd_probe').resolve()),str(directory),'--controls'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
assert len(output)==len(cases)*128000
for index,row in enumerate(cases):
    side,aircraft=row[1:3];x,y=row[10:12]
    a,b,c,d,enabled,mode,configuration,heading,waypoint,height,speed=row[-11:]
    im.write(0x11b2a,'<H',aircraft);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    im.write(0x14728,'<d',a);im.write(0x14720,'<d',b);im.write(0x14840,'<d',c);im.write(0x14838,'<d',d)
    im.write(0x14958,'<H',enabled);im.write(0x14960,'<H',mode);im.write(0x14962,'<H',configuration)
    im.write(0x1493a,'<H',heading);im.write(0x597c,'<h',waypoint);im.write(0x14348,'<d',height);im.write(0x8d40,'<d',speed)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x88778,eax=side*2,limit=2000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*128000:(index+1)*128000]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
readouts=[]
for index in range(256):
    x,y=positions[index%len(positions)];mode=[0,1,2,3,4,5,32767,32768,65535][(index//2)%9]
    readouts.append([index%2,mode,x,y])
output=subprocess.check_output([str((args.build/'readout_probe').resolve()),str(directory),'--autopilot'],input=('\n'.join(' '.join(map(str,row)) for row in readouts)+'\n').encode())
assert len(output)==len(readouts)*128000
for index,(enabled,mode,x,y) in enumerate(readouts):
    im.write(0x14958,'<H',enabled);im.write(0x14960,'<H',mode);im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x7e1f4,limit=2000000)
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*128000:(index+1)*128000]
    assert got==want,((enabled,mode,x,y),[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Controls MFD agrees in {len(cases)} complete native pixel/coverage frames; autopilot indicator agrees in another {len(readouts)}')
