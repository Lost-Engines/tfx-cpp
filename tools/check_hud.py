#!/usr/bin/env python3
"""Execute the assembled original instrument HUD and compare complete indexed frames."""
import argparse
from pathlib import Path
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
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);im.cpu.mem_map(0x300000,0x40000);im.cpu.mem_map(0x400000,0x100000)
banks=[('pitfont',0x12c2e),('disp12',0x12c3a),('compdisp',0x12c2a),('autolite',0x12c22),('disp2',0x12c34),('warlites',0x12c38),('warlite2',0x12c36),('englite',0x12c28),('aoasprs',0x12c1e),('nwsg',0x12c20),('yugosmap',0x12c30)]
for handle,(name,field) in enumerate(banks,1):
    raw=archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]);assert len(raw)<0x10000
    im.cpu.mem_write(0x400000+(handle-1)*0x10000,raw);im.write(field,'<H',handle)
for address in (0xc8568,0xc85a0):
    im.intercept(address,'Supply original HUD sprite banks at the external resource boundary.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x400000+(im.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x10000),im.return_from()))
contacts=[(103000*256,-100*256,112000*256),(99000*256,-100*256,111000*256),(100000*256,0,111000*256),(100000*256,0,109000*256)]
for index,position in enumerate(contacts):
    address=0x330000+index*128;im.cpu.mem_write(address,bytes(128));im.cpu.mem_write(address,struct.pack('<3i',*position))
    if index>=2:im.cpu.mem_write(address+0x24,struct.pack('<H',index))
def query(im,pool):
    index=struct.unpack('<h',struct.pack('<H',im.cpu.reg_read(r.UC_X86_REG_EAX)&65535))[0]+1
    side=im.cpu.reg_read(r.UC_X86_REG_EDX);assert side in (0,1)
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x330000+(pool*2+side)*128 if index==0 else 0);im.return_from()
im.intercept(0x786d8,'Supply fixed aircraft contacts; the full HUD projection and drawing execute.',lambda im:query(im,0))
im.intercept(0x7c7d0,'Supply fixed mobile-surface contacts.',lambda im:query(im,1))
im.intercept(0xb7a3c,'Supply each surface contact definition type.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,56 if im.cpu.reg_read(r.UC_X86_REG_EAX)==2 else 3),im.return_from()))
sounds=[]
im.intercept(0xa4dfc,'Record the original warning sound request without audio output.',lambda im:(sounds.append(im.cpu.reg_read(r.UC_X86_REG_EAX)),im.return_from()))
video=VgaCapture(im,aperture=0xa0000);im.call(0xde547)
im.write(0x7612,'<B',1) # Isolate 0x803e8 instruments from the separately called upper-HUD painter.
im.write(0x6c38,'<B',3);im.write(0x8840,'<I',0);im.write(0x11108,'<I',0)
im.write(0x16e80,'<I',0x331000);im.write(0x16e7c,'<I',0x331100);im.cpu.mem_write(0x331034,struct.pack('<I',0x331100))
im.write(0x11b22,'<h',1);im.write(0x5c40,'<3i',102000,0,112000);im.write(0x14984,'<2h',50,60)
im.cpu.mem_write(0x331206,bytes([1]))
count=504;stride=128080
output=subprocess.check_output([str((args.build/'hud_probe').resolve()),str(directory),'yugosmap'],input=('\n'.join(map(str,range(count)))+'\n').encode())
assert len(output)==count*stride
for index in range(count):
    left=(0,1,2,3,4,5,8)[(index//3)%7];centre=index%3;right=(0,1,2,3,4,5,7,8)[(index//21)%8];aircraft=(index//168)%3
    im.write(0x713a,'<3H',left,centre,right);im.write(0x7d7c,'<2H',index%4,index%3)
    im.write(0x11b2a,'<H',aircraft);im.write(0x93ae,'<h',(9,3,7)[aircraft]);im.write(0x93b0,'<h',0)
    im.write(0x13374,'<22B',*([1,1]*11));im.write(0x7140,'<B',not bool(index%2));im.write(0x135d0,'<I',index%2)
    systems=[14 if (index+slot)%9==0 else 2 for slot in range(12)];im.write(0x7d70,'<12B',*systems)
    im.write(0x13444,'<i',index+100);im.write(0x13428,'<f',-index*2);im.write(0x86ca,'<H',(index*182)&65535)
    im.write(0x14858,'<d',(0,999.5,2499.5,5000)[index%4]);im.write(0x6c3c,'<h',(index*137)%10000);im.write(0x6c3a,'<h',4)
    im.write(0x133f8,'<f',.75);im.write(0x14880,'<2d',.65,.75)
    im.write(0x14728,'<d',.3);im.write(0x14720,'<d',-.7);im.write(0x14840,'<d',-.2);im.write(0x14838,'<d',.1)
    im.write(0x14958,'<H',index%2);im.write(0x14960,'<H',index%5);im.write(0x14962,'<H',index%5)
    im.write(0x1493a,'<H',16384);im.write(0x597c,'<h',3);im.write(0x14348,'<d',-1000);im.write(0x8d40,'<d',250)
    for field,value in zip((0x13424,0x13430,0x1343c),(100000,-300,110000)):im.write(field,'<i',value)
    im.write(0x7618,'<I',index*54);im.write(0x1199c,'<I',540);im.write(0x13476,'<H',index%55)
    im.write(0x12f29,'<B',index%3==0);im.write(0x12f26,'<B',index%5==0);im.write(0x6c3e,'<2B',index%16,(index//2)%16)
    im.write(0x8d12,'<H',index%5==0);im.write(0x763c,'<H',index%7==0);im.write(0x7638,'<I',0x331200 if index%2 else 0)
    im.write(0x13474,'<H',index%11==0);im.write(0x763e,'<H',index%13==0);im.write(0x10bed,'<B',index%4);im.write(0x1496d,'<B',index%5)
    im.write(0x8f82,'<B',index%2);im.write(0x8f8a,'<B',index%3);im.write(0x8f8c,'<B',index%3==0)
    im.write(0x8d38,'<H',index%4==0);im.write(0x8d3a,'<H',index%8==0)
    im.write(0x10be8,'<h',index%4);im.write(0x10be6,'<h',(index//4)%2*8)
    im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',0x5926,0x3141))
    video.reset();sounds.clear()
    for plane in video.planes:plane[:]=bytes([99])*16000
    im.call(0x803e8,limit=4000000)
    assert sounds in ([],[43]),sounds
    header=[im.read(0x7622,'<H')[0],im.read(0x7624,'<H')[0],bool(sounds),im.read(0x7158,'<B')[0],im.read(0x6c38,'<B')[0],im.read(0x12f30,'<I')[0],*im.read(0x767e,'<2B'),im.read(0x7772,'<B')[0],im.read(0x10bed,'<B')[0],*struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4))]
    fields=(0x4fb78,0x4fb7c,0x4fb7a,0x4fb7e,0x4fb80,0x4fb88,0x4fb84,0x4fb8c)
    header.extend(struct.unpack('<h' if i<4 else '<i',im.cpu.mem_read(im.native(0x70aa4+field),2 if i<4 else 4))[0] for i,field in enumerate(fields))
    want=struct.pack('<20I',*header)+bytes(video.pixels())+bytes(video.coverage());got=output[index*stride:(index+1)*stride]
    assert got==want,(index,left,centre,right,[(i,(i-80)%64000%320,(i-80)%64000//320,a,b) for i,(a,b) in enumerate(zip(got,want)) if a!=b][:30])
print(f'Assembled instrument HUD agrees in {count} complete native pixel/coverage/animation/clip/random-state frames')
