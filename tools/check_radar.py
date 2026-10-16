#!/usr/bin/env python3
"""Compare complete native radar views and shared-random consumption with supplied contacts."""
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
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x40000)
im.cpu.mem_write(0x300000,archive.unpack(entries[archive.hash_name('spr/disp2.spr')]))
im.intercept(0xc85a0,'Supply the original central-display sprite bank at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
im.write(0x12c34,'<H',1);groups=[[],[],[],[]];types={}
def query(im,pool):
    index=struct.unpack('<h',struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EAX)&65535))[0]+1
    side=im.cpu.reg_read(r.UC_X86_REG_EDX);assert side in (0,1)
    group=pool*2+side
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000+group*0x1000+index*128 if index<len(groups[group]) else 0);im.return_from()
im.intercept(0x786d8,'Supply fixed aircraft enumerations; contact projection, damage filtering and drawing execute.',lambda im:query(im,0))
im.intercept(0x7c7d0,'Supply fixed surface enumerations; radar drawing executes unchanged.',lambda im:query(im,1))
im.intercept(0xb7a3c,'Supply the fixed surface definition type associated with each supplied handle.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,types[im.cpu.reg_read(r.UC_X86_REG_EAX)]),im.return_from()))
video=VgaCapture(im,aperture=0xa0000);rng=random.Random(0x82a2c);cases=[]
for index in range(640):
    mode=index%2;range_index=(index//2)%(4 if mode==0 else 3)
    scale=((66,330,990,1650) if mode==0 else (990,1320,1650))[range_index]
    player=[rng.randrange(70000,130000),-1000,rng.randrange(70000,130000)]
    heading=0 if index<160 else rng.randrange(65536)
    aircraft=index%3;condition=(0,1,2,11,14)[(index//3)%5]
    stealth=int((index//15)%2);guns=int((index//30)%2);role=(0,1,6)[(index//60)%3]
    x,y=[(0,0),(1,0),(2,0),(3,0),(-2,-100),(10,3)][index%6]
    low,high=rng.randrange(65536),rng.randrange(65536)
    contacts=[]
    for group in range(4):
        points=[]
        for slot in range(6):
            dx,dy=[(-28,-22),(-27,-21),(0,-20),(27,21),(28,22),(rng.randrange(-35,36),rng.randrange(-45,12))][slot]
            px=(player[0]+dx*scale)*256+rng.randrange(256);pz=(player[2]-dy*scale)*256+rng.randrange(256)
            py=(-37-slot%3)*256-(index%2)
            selected=int(group==0 and slot==index%7)
            extra=selected if group<2 else (56 if slot%2==0 else slot)
            points.append([px,py,pz,extra])
        contacts.append(points)
    shots=[]
    for slot,weapon in enumerate((0,1,24,25,26,index%27)):
        px=(player[0]+(slot-3)*3*scale)*256;pz=(player[2]+(slot-3)*4*scale)*256
        shots.append([px,-100000,pz,weapon,slot%2])
    row=[mode,range_index,*player,heading,aircraft,condition,stealth,guns,role,x,y,low,high]
    for points in contacts:row.extend([len(points),*[v for point in points for v in point]])
    row.extend([len(shots),*[v for shot in shots for v in shot]])
    cases.append((row,contacts,shots))
output=subprocess.check_output([str((args.build/'radar_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row,_,_ in cases)+'\n').encode())
stride=128005;assert len(output)==len(cases)*stride
for index,(row,contacts,shots) in enumerate(cases):
    mode,range_index,px,py,pz,heading,aircraft,condition,stealth,guns,role,x,y,low,high=row[:15]
    im.write(0x713c,'<H',mode);im.write(0x7d7c if mode==0 else 0x7d7e,'<h',range_index)
    for field,value in zip((0x13424,0x13430,0x1343c),(px,py,pz)):im.write(field,'<i',value)
    im.write(0x86ca,'<H',heading);im.write(0x11b2a,'<H',aircraft);im.write(0x7d76,'<B',condition)
    im.write(0x12f26,'<B',stealth);im.write(0x7140,'<B',not guns);im.write(0x93b0,'<h',0);im.write(0x13374,'<B',0);im.write(0x80b0,'<B',role)
    im.write(0x10be8,'<h',x);im.write(0x10be6,'<h',y)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high));groups[:]=contacts;types.clear();selected=0
    for group,points in enumerate(contacts):
        for slot,point in enumerate(points):
            address=0x310000+group*0x1000+slot*128
            im.cpu.mem_write(address,bytes(128));im.cpu.mem_write(address,struct.pack('<3i',*point[:3]))
            if group==0 and point[3]:selected=address
            if group>=2:
                handle=100+group*10+slot;types[handle]=point[3];im.cpu.mem_write(address+0x24,struct.pack('<H',handle))
    im.write(0x11108,'<I',selected)
    tail=0x330000;head=0x330100
    im.write(0x16e80,'<I',head);im.write(0x16e7c,'<I',tail);im.cpu.mem_write(head+0x34,struct.pack('<I',0x320000 if shots else tail))
    for slot,shot in enumerate(shots):
        address=0x320000+slot*128;im.cpu.mem_write(address,bytes(128))
        im.cpu.mem_write(address+6,bytes([shot[3]]));im.cpu.mem_write(address+8,struct.pack('<3i',*shot[:3]))
        im.cpu.mem_write(address+0x34,struct.pack('<I',address+128 if slot+1<len(shots) else tail))
        im.cpu.mem_write(address+0x4b,struct.pack('<I',im.data+0x10f28 if shot[4] else im.data+0x10fff))
    video.reset()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x88ecc,limit=2000000)
    want=struct.pack('<B2H',im.read(0x7772,'<B')[0],*struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4)))+bytes(video.pixels())+bytes(video.coverage())
    got=output[index*stride:(index+1)*stride]
    assert got==want,(index,row,[(i,(i-5)%64000%320,(i-5)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Horizontal/BVR radars agree in {len(cases)} complete native pixel/coverage/pulse/random-state frames')
