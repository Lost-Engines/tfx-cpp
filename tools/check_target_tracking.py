#!/usr/bin/env python3
"""Compare composed forward-HUD target state over original multi-frame draws.

Original weapon/target layout, lock blinking, text and VGA painters execute.
Sensor state and world-screen projections are supplied at their separately
checked boundaries. Audio/voice requests are recorded without playing sound.
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
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--landing',action='store_true',help='include original ILS guidance in the NAV layout')
parser.add_argument('--navigation',action='store_true',help='include the separate refuelling/navigation contact consumer')
parser.add_argument('--alerts',action='store_true',help='include BINGO/PULL UP requests and retained warning timer')
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(args.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000);im.cpu.mem_map(0x300000,0x20000);im.cpu.mem_map(0x400000,0x30000)
for handle,(name,field) in enumerate((('spr/newhud2.spr',0x12c24),('spr/ladnums.spr',0x12c40),('dat/fwshdg.dat',0x12c3c)),1):
    raw=archive.unpack(entries[archive.hash_name(name)]);im.cpu.mem_write(0x400000+(handle-1)*0x10000,raw);im.write(field,'<H',handle)
im.intercept(0xc8568,'Supply unchanged original sight/ladder/heading banks at the external resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x400000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x10000),im.return_from()))
for address in (0x836ac,0xa7130):im.intercept(address,'Supply sensor/selection controller state; their rendering consumers execute.',lambda im:im.return_from())
im.intercept(0x7889c,'Supply the selected aircraft name; native name processing executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300040 if im.cpu.reg_read(r.UC_X86_REG_EAX)==0x310100 else 0x300000),im.return_from()))
im.cpu.mem_write(0x300000,b'MiG-29 Fulcrum\0');im.cpu.mem_write(0x300040,b'RAF Victor tanker\0')
path=[140,40,145,45,150,50,155,55,160,60]
def cannon(im):
    im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EDX),struct.pack('<10h',*path));im.return_from()
im.intercept(0xa2878,'Supply independently checked projected cannon samples.',cannon)
def impact(im):
    im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EDX),struct.pack('<2h',160,60));im.return_from()
im.intercept(0xa29dc,'Supply the independently checked projected Mk82 impact.',impact)
ground=[0,0];ground_valid=False

def project(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);destination=struct.unpack('<I',im.cpu.mem_read(stack+16,4))[0]
    im.cpu.mem_write(destination,struct.pack('<2h',*ground));im.cpu.reg_write(r.UC_X86_REG_EAX,ground_valid);im.return_from(16)
im.intercept(0xc5759,'Supply a projected designated-ground point; native visibility and rectangle drawing execute.',project)
events=[]
im.intercept(0xa4dfc,'Record lock-tone requests without audio output.',lambda im:(events.append('tone'),im.return_from()))
def voice(im):
    stack=im.cpu.reg_read(r.UC_X86_REG_ESP);values=struct.unpack('<4I',im.cpu.mem_read(stack+4,16));assert values[0]==1 and values[3]==0,values
    events.append('voice');im.return_from()
im.intercept(0x70b44,'Record the native external voice callback without audio output.',voice)
im.write(0xac74,'<I',im.native(0x70b44))
im.call(0x809e4);im.call(0xde547);im.call(0x7ded8)
im.write(0x14858,'<d',10000);im.write(0x7d73,'<B',2);im.write(0x1347a,'<B',0);im.write(0x13af4,'<I',0);im.write(0x8f82,'<B',0);im.write(0x12c1c,'<H',0);im.write(0x11b22,'<H',0);im.write(0x6c41,'<B',0)
for field,fmt in ((0x13428,'<f'),(0x13444,'<i'),(0x14778,'<d'),(0x133f4,'<f'),(0x133f8,'<f'),(0x145a8,'<d'),(0x14964,'<H'),(0x8d14,'<H')):im.write(field,fmt,0)
rng=random.Random(0x7fb98);cases=[]
for index in range(1024):
    mode=1 if index<32 else 0 if index<48 else rng.randrange(3)
    weapon=rng.choice([0,1,3,4,5] if mode!=2 else [0,8,18,20,22])
    present=1 if index<64 else int(index%5!=0);locked=int(4<=index<28) if index<32 else int(present and index%3!=0)
    acquiring=int(present and not locked and index%2==0)
    projected=[(160,56),(0,0),(319,199),(-10,80),(200,100)][index%5]
    tracking=[value*256 for value in [(160,56),(0,0),(-15,80),(200,100),(300,180)][(index//5)%5]]
    player=[rng.randrange(-1000000,1000000) for _ in range(3)];position=[rng.randrange(-100000000,100000000) for _ in range(3)]
    basis=[32767,0,0,0,32767,0,0,0,32767] if index<64 else [rng.randrange(-32768,32768) for _ in range(9)]
    dx,dy=[(0,0),(1,0),(2,0),(3,0),(-4,0),(4,0),(0,28),(0,50)][index%8]
    ground_point=[(160,56),(-100,50),(200,100),(319,199)][index%4]
    cases.append([index%97==0,mode,index%3,weapon,1 if index<64 else index%2,0 if index<64 else (index//2)%2,locked,(index//4)%2,present,acquiring,255 if index%2 else 0,*projected,*tracking,*player,*position,rng.randrange(65536),rng.randrange(-2147483648,2147483648),*basis,index%3!=0,*ground_point,dx,dy])
if args.alerts:
    for index,row in enumerate(cases):row.extend([index%2 if index%7==0 else -1,[499,500,10000][index%3],[0,1,4,108,65535][index%5]])
if args.navigation:
    for index,row in enumerate(cases):row.extend([index%3!=0,*[value+10000 for value in row[18:21]],(index*503)%65536,200*65536])
if args.landing:
    for index,row in enumerate(cases):row.extend([index%4!=0,index%3==0,index%2,index%200,(index*3)%200,-500,700,(index*503)%65536,10000,20000,700,800,2,-3,1000,index%3])
landing_fields=[(0x8f82,'B'),(0x8f8b,'B'),(0x8f8c,'B'),(0x14984,'h'),(0x14986,'h'),(0x8f84,'h'),(0x8f86,'h'),(0x8f88,'H'),(0x1497c,'i'),(0x14978,'i'),(0x14938,'H'),(0x1493a,'H'),(0x14980,'h'),(0x14982,'h'),(0x14974,'i'),(0x8f8a,'B')]
im.write(0x7612,'<B',0)
command=[str((args.build/'target_tracking_probe').resolve()),str(directory)]
if args.alerts:command.append('--alerts')
if args.navigation:command.append('--navigation')
if args.landing:command.append('--landing')
output=subprocess.check_output(command,input=('\n'.join(' '.join(str(int(v)) for v in row) for row in cases)+'\n').encode())
header_bytes=(24 if args.alerts else 16)+(64 if args.landing else 0);stride=128000+header_bytes;assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    reset,mode,aircraft,weapon,limited,suppressed,locked,designated,present,acquiring,leader,x,y,tx,ty=row[:15];player=row[15:18];position=row[18:21];heading,speed=row[21:23];basis=row[23:32];ground_valid,gx,gy,dx,dy=row[32:37];ground[:]=[gx,gy]
    if reset:im.write(0x7141,'<B',0);im.write(0x7144,'<I',0);im.call(0x7ded8)
    im.write(0x11b2a,'<H',aircraft);im.write(0x86c8,'<3H',0,0,0);im.write(0x16e9a,'<h',1760)
    slot=10 if weapon==0 else 0;im.write(0x93b0,'<h',slot);im.write(0x13374+slot*2,'<2B',weapon,1);im.write(0x809c+20,'<B',mode==2)
    im.write(0x7140,'<B',mode!=0 and weapon!=0);im.write(0x7148,'<B',mode==0);im.write(0x8860,'<B',suppressed)
    im.cpu.mem_write(0x310000,bytes(128));im.cpu.mem_write(0x310000,struct.pack('<3i3Hi',*position,0,heading,0,speed));im.cpu.mem_write(0x310028,bytes([leader]))
    im.write(0x11108,'<I',0x310000 if present else 0);im.write(0x135d0,'<I',0x310000 if locked else 0);im.write(0x135c8,'<I',0x310000 if acquiring else 0);im.write(0x8840,'<I',1 if designated else 0)
    for field,value in zip((0x13424,0x13430,0x1343c),player):im.write(field,'<i',value)
    im.write(0x1345e,'<9h',*basis);im.write(0x135cc,'<2h',x,y);im.write(0x135c0,'<2i',tx,ty);im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
    cy=56+int(dy/2);im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(159,cy,319,199));im.call(0xc84b1,stack=(0,319,0,199,cy));im.call(0xc82b9,stack=(0,0));im.call(0xc0634,stack=(199,0,319,0))
    if args.alerts:
        request,fuel,elapsed=row[37:40];im.write(0x14858,'<d',fuel);im.write(0x13476,'<H',elapsed)
        if request>=0:im.call(0x7dde4,eax=im.data+(0x6f12 if request else 0x6fbe),edx=im.data+(0x6f72 if request else 0x702e))
    if args.navigation:
        start=40 if args.alerts else 37
        navigation,nx,ny,nz,nh,ns=row[start:start+6]
        im.cpu.mem_write(0x310100,struct.pack('<3i3Hi',nx,ny,nz,0,nh,0,ns));im.write(0x13af4,'<I',0x310100 if navigation else 0)
    if args.landing:
        start=(40 if args.alerts else 37)+(6 if args.navigation else 0)
        for (field,fmt),value in zip(landing_fields,row[start:start+16]):im.write(field,'<'+fmt,value)
    video.reset();events.clear()
    for plane in video.planes:plane[:]=bytes([99])*16000
    try:im.call(0x800f4,eax=limited,limit=4000000)
    except RuntimeError as error:raise RuntimeError((index,row,str(error))) from error
    assert len(events)<=1,(index,events)
    header=[im.read(0x7141,'<B')[0],bool(im.read(0x7144,'<I')[0]),im.read(0x12c10,'<I')[0]==im.data+0x6da6,bool(events)]
    if args.alerts:header.extend([int(im.read(0x12c0c,'<I')[0]==im.data+0x6f12),im.read(0x12c1c,'<h')[0]])
    if args.landing:header.extend(im.read(field,'<'+fmt)[0] for field,fmt in landing_fields)
    want=struct.pack('<'+'i'*len(header),*header)+bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(row,header,[(i,(i-header_bytes)%64000%320,(i-header_bytes)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Forward target composition agrees in {len(cases)} native pixel/coverage/animation/event frames'+(' including BINGO/PULL UP request, paint order and timer' if args.alerts else '')+(' and refuelling contact information/direction/marker' if args.navigation else '')+(' and ILS guidance/state' if args.landing else '')+' with declared sensor, projection and audio boundaries')
