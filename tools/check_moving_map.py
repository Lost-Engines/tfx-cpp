#!/usr/bin/env python3
"""Compare full native moving maps with supplied actor enumerations and mission targets."""
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
im.intercept(0xc85a0,'Supply the original environment schematic sprite at the resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300000),im.return_from()))
im.write(0x12c30,'<H',1);lists=[[],[],[],[]]
def query(im,pool):
    index=struct.unpack('<h',struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EAX)&65535))[0]+1
    side=im.cpu.reg_read(r.UC_X86_REG_EDX);assert side in (0,1)
    group=pool*2+side
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000+group*0x1000+index*16 if index<len(lists[group]) else 0)
    im.return_from()
im.intercept(0x786d8,'Supply fixed air-actor enumerations; their controllers and allegiance filtering have separate comparisons.',lambda im:query(im,0))
im.intercept(0x7c7d0,'Supply fixed surface-actor enumerations; map projection and painting still execute.',lambda im:query(im,1))
video=VgaCapture(im,aperture=0xa0000);rng=random.Random(0x823d0);total=0
for name in ('yugosmap','libyamap','colummap','somalmap','seamap'):
    im.cpu.mem_write(0x300000,archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]))
    im.write(0x12f30,'<I',0);im.write(0x767e,'<2B',11,6)
    cases=[]
    for index in range(128):
        player=[rng.randrange(-2048,410000),-1000,rng.randrange(-2048,410000)]
        heading=[0,16384,32768,49152][index%4] if index<16 else rng.randrange(65536)
        elapsed=[0,1,49,50,51,54,65535][index%7];stealth=index%2;landing=(index//2)%2
        runway=[player[0]//2048+rng.randrange(-20,21),player[2]//2048+rng.randrange(-20,21)]
        offset=[(0,0),(1,0),(2,0),(3,0),(-10,-10),(20,20),(0,35),(0,70)][index%8]
        bounds=[(135,151,186,193),(213,133,264,167),(20,20,200,120)][index%3]
        if index>=64:
            # Expose the clear rectangle where the schematic no longer
            # covers it, including each VGA-plane alignment at the border.
            cell=(-1,0,1,15,16,17,18,20,99,100,180,182,183,184,199,200)[(index-64)//4]
            player=[143*2048,-1000,cell*2048]
            offset=(index%4,0);bounds=(213,133,264,167)
        contacts=[]
        for group in range(4):
            points=[]
            for slot in range(3):
                x=player[0]+rng.randrange(-30,31)*2048+rng.randrange(-255,256)
                z=player[2]+rng.randrange(-30,31)*2048+rng.randrange(-255,256)
                y=(-36-slot)*256-(index%2)
                points.append([x*256,y,z*256])
            contacts.append(points)
        targets=[[player[0]+rng.randrange(-25,26)*2048,0,player[2]+rng.randrange(-25,26)*2048] for _ in range(3)]
        row=[*player,heading,elapsed,stealth,landing,*runway,*offset,*bounds]
        for points in contacts:row.extend([len(points),*[v for point in points for v in point]])
        row.extend([len(targets),*[v for point in targets for v in point]])
        cases.append((row,player,heading,elapsed,stealth,landing,runway,offset,bounds,contacts,targets))
    output=subprocess.check_output([str((args.build/'map_display_probe').resolve()),str(directory),name],input=('\n'.join(' '.join(map(str,c[0])) for c in cases)+'\n').encode())
    stride=128038;assert len(output)==len(cases)*stride
    for index,case in enumerate(cases):
        row,player,heading,elapsed,stealth,landing,runway,offset,bounds,contacts,targets=case
        for field,value in zip((0x13424,0x13430,0x1343c),player):im.write(field,'<i',value)
        im.write(0x86ca,'<H',heading);im.write(0x13476,'<H',elapsed);im.write(0x12f26,'<B',stealth)
        im.write(0x8f82,'<B',landing);im.write(0x14984,'<2h',*runway)
        im.write(0x10be8,'<h',offset[0]);im.write(0x10be6,'<h',offset[1])
        lists[:]=contacts
        for group,points in enumerate(contacts):
            for slot,point in enumerate(points):im.cpu.mem_write(0x310000+group*0x1000+slot*16,struct.pack('<3i',*point))
        im.write(0x11b22,'<h',len(targets))
        for slot,point in enumerate(targets):im.write(0x5c40+slot*26,'<3i',*point)
        video.reset()
        for plane in video.planes:plane[:]=bytes([99])*16000
        left,top,right,bottom=bounds
        im.call(0x823d0,eax=left,edx=top,ebx=right,ecx=bottom,limit=2000000)
        fields=(0x4fb78,0x4fb7c,0x4fb7a,0x4fb7e,0x4fb80,0x4fb88,0x4fb84,0x4fb8c)
        clip=[struct.unpack('<h' if i<4 else '<i',im.cpu.mem_read(im.native(0x70aa4+field),2 if i<4 else 4))[0] for i,field in enumerate(fields)]
        want=struct.pack('<I2B8i',im.read(0x12f30,'<I')[0],*im.read(0x767e,'<2B'),*clip)+bytes(video.pixels())+bytes(video.coverage())
        got=output[index*stride:(index+1)*stride]
        assert got==want,(name,index,row,[(i,(i-38)%64000%320,(i-38)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
    total+=len(cases)
print(f'Moving maps agree in {total} complete native pixel/coverage/blink/clip frames across all five schematics')
