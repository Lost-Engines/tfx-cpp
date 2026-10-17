#!/usr/bin/env python3
"""Compare original navigation, AA and AG HUD layouts with supplied cue inputs.

Original attitude projection and all VGA painters execute. The cannon path is
supplied at its separately verified trajectory/projection boundary. These cases
have no landing-approach controller, ground-navigation target or selected air
contact; those controllers and timed launch notices are separate integrations.
"""
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
parser.add_argument('--full',action='store_true')
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x400000,0x30000)
for handle,(name,field) in enumerate((('spr/newhud2.spr',0x12c24),('spr/ladnums.spr',0x12c40),('dat/fwshdg.dat',0x12c3c)),1):
    raw=archive.unpack(entries[archive.hash_name(name)]);im.cpu.mem_write(0x400000+(handle-1)*0x10000,raw);im.write(field,'<H',handle)
im.intercept(0xc8568,'Supply the unchanged original sight/ladder sprite banks at their resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x400000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x10000),im.return_from()))
path=[]
def cannon(im):
    destination=im.cpu.reg_read(r.UC_X86_REG_EDX);im.cpu.mem_write(destination,struct.pack('<10h',*path));im.return_from()
im.intercept(0xa2878,'Supply five projected cannon samples; the temporary trajectory has its own original-code comparison.',cannon)
def impact(im):
    destination=im.cpu.reg_read(r.UC_X86_REG_EDX);im.cpu.mem_write(destination,struct.pack('<2h',*path[:2]));im.return_from()
im.intercept(0xa29dc,'Supply the projected bomb-impact point; its temporary trajectory is compared separately.',impact)
im.call(0x809e4);im.call(0xde547)
if args.full:
    im.intercept(0x836ac,'Exclude the separately driven radar/acquisition cue controller from this layout composition.',lambda im:im.return_from())
    im.intercept(0xa7130,'Exclude the cannon-selection controller; its displayed telemetry is supplied explicitly.',lambda im:im.return_from())
    im.write(0x14858,'<d',10000);im.write(0x7d73,'<B',2);im.write(0x1347a,'<B',0);im.write(0x13af4,'<I',0)
    for field,fmt in ((0x13428,'<f'),(0x13444,'<i'),(0x14778,'<d'),(0x133f4,'<f'),(0x133f8,'<f'),(0x13424,'<i'),(0x13430,'<i'),(0x1343c,'<i'),(0x145a8,'<d'),(0x14964,'<H'),(0x8d14,'<H')):im.write(field,fmt,0)
im.write(0x8f82,'<B',0);im.write(0x12c1c,'<H',0);im.write(0x11108,'<I',0);im.write(0x11b22,'<H',0);im.write(0x6c41,'<B',0)
rng=random.Random(0x7e5b4);cases=[]
for mode in range(4 if args.full else 3):
    for index in range(256):
        weapon=([7,7,7,7] if args.full and mode==3 else [0,1,3,4] if args.full and mode==1 else [0,8,18,22] if args.full and mode==2 else [0,1,3,4,8,18,22])[index%(4 if args.full and mode else 7)];dx,dy=[(0,0),(1,0),(2,0),(3,0),(-4,0),(4,0),(0,28),(0,50)][index%8]
        pitch=rng.randrange(65536);heading=rng.randrange(65536);roll=rng.randrange(65536)
        path=[value for _ in range(5) for value in (rng.randrange(60,260),rng.randrange(-20,160))]
        cases.append([mode,index%3,weapon,rng.randrange(-32768,32768),index%2,0 if args.full else (index//2)%2,0 if args.full else (index//4)%2,(index//8)%2,pitch,heading,roll,(-pitch)&65535,(-roll)&65535,56+int(dy/2),dx,dy,*path])
output=subprocess.check_output([str((args.build/'weapon_display_probe').resolve()),str(directory),*(['full'] if args.full else [])],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode())
stride=128000;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    mode,aircraft,weapon,ammo,suppressed,air_lock,ground_lock,limited,pitch,heading,roll,projection_pitch,projection_roll,cy,dx,dy=row[:16];path=row[16:]
    im.write(0x11b2a,'<H',aircraft);im.write(0x86c8,'<3H',pitch,heading,roll);im.write(0x16e9a,'<h',ammo)
    slot=10 if args.full and weapon==0 else 0
    im.write(0x93b0,'<h',slot);im.write(0x13374+slot*2,'<2B',weapon,1);
    if args.full:
        im.write(0x7140,'<B',mode!=0);im.write(0x7148,'<B',mode==0);im.write(0x809c+20,'<B',mode==2)
    im.write(0x8860,'<B',suppressed);im.write(0x135d0,'<I',air_lock);im.write(0x8840,'<I',ground_lock)
    im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(159,cy,319,199));im.call(0xc84b1,stack=(0,319,0,199,cy));im.call(0xc82b9,stack=(projection_pitch,projection_roll))
    if mode and not args.full:im.call(0xc0634,stack=(97+dy,4+dy,231+dx,91+dx))
    else:im.call(0xc0634,stack=(199,0,319,0))
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    try:im.call(0x800f4 if args.full else (0x7ecb4,0x7e5b4,0x7e958)[mode],eax=limited,limit=4000000)
    except RuntimeError as error:raise RuntimeError((index,row,str(error))) from error
    want=bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(row,[(i%64000%320,i%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'{"Forward composition: " if args.full else ""}Navigation/AA/AG HUD layouts agree in {len(cases)} complete native pixel/coverage frames with declared trajectory and targeting boundaries')
