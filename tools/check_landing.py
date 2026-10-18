#!/usr/bin/env python3
"""Compare original ILS selection, approach state and complete HUD frames.

The native ILS routines execute with supplied route/SSD resource boundaries.
Guidance executes original bearing, text, masks and VGA line painters; the
separately verified world-point projector is supplied explicitly.
"""
import argparse
from collections import Counter
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
parser.add_argument('--record',type=Path,help='write a compact native guidance-state fixture')
parser.add_argument('--selection',action='store_true',help='compare destination and key-handler state instead of HUD frames')
parser.add_argument('--destination-only',action='store_true',help='compare complete A0BC0 directly, including Alt+L selection messages')
a=parser.parse_args();directory=a.research/'installs/cd_1994_09/TFX';im=NativeReference(directory/'TFX.DAT',data_base=0x100000)
if a.destination_only:a.selection=True
fields=[(0x8f82,'B'),(0x8f8b,'B'),(0x8f8c,'B'),(0x14984,'h'),(0x14986,'h'),(0x8f84,'h'),(0x8f86,'h'),(0x8f88,'H'),(0x1497c,'i'),(0x14978,'i'),(0x14938,'H'),(0x1493a,'H'),(0x14980,'h'),(0x14982,'h'),(0x14974,'i'),(0x8f8a,'B')]
def set_state(values):
    for (field,fmt),value in zip(fields,values):im.write(field,'<'+fmt,value)
def state():return [im.read(field,'<'+fmt)[0] for field,fmt in fields]
rng=random.Random(0xa0f40)
def initial(index):
    return [index%7==0,index%3==0,index%2,12+index%100,18+index%100,rng.randrange(-3000,3001),rng.randrange(-3000,3001),rng.randrange(65536),rng.randrange(10000,400000),rng.randrange(10000,400000),rng.randrange(65536),rng.randrange(65536),rng.randrange(-24,25),rng.randrange(-24,25),rng.randrange(-5000,5001),index%3]

if not a.selection:
    video=VgaCapture(im,aperture=0xa0000);im.call(0x809e4);im.call(0xde547)
    messages=[];requested=[];projected=[]
    def project(image):
        stack=image.cpu.reg_read(r.UC_X86_REG_ESP)
        z,y,x,destination=struct.unpack('<4I',image.cpu.mem_read(stack+4,16))
        signed=lambda value:value if value<0x80000000 else value-0x100000000
        requested[:]=list(map(signed,(x,y,z)))
        image.cpu.mem_write(destination,struct.pack('<2h',*projected[1:]));image.cpu.reg_write(r.UC_X86_REG_EAX,projected[0]);image.return_from(16)
    im.intercept(0xc5759,'Supply separately verified projection; capture its exact signed-word world inputs',project)
    im.intercept(0x81198,'Observe the approach speed/altitude radio request without the separate ticker/audio consumer',lambda image:(messages.append(image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data),image.return_from()))
    cases=[]
    for index in range(1024):
        values=initial(index);values[0]=1
        if values[2]:
            dx,dz=[(0,0),(999,0),(1000,0),(-999,-999),(1200,2000)][(index//2)%5]
            player=[values[8]+dx,-1000,values[9]+dz]
        else:player=[rng.randrange(10000,400000),rng.randrange(-10000,1),rng.randrange(10000,400000)]
        if index>=768 and not values[2]:
            values[1]=0;values[7]=0
            player=[values[3]*2048+1024,[0,-100,-1200,-1220,-1240,-2000,-5000][(index//2)%7],values[4]*2048+1024+700+10000]
        valid=int(index%5!=0);x,y=[(159,56),(0,0),(318,198),(319,198),(320,199),(-1,80),(100,-1),(200,50)][index%8]
        dx,dy=[(0,0),(0,28),(0,50),(-4,0),(3,0)][index%5]
        cases.append([index,*values,*player,index%3==0,valid,x,y,dx,dy])
    output=subprocess.check_output([str((a.build/'landing_probe').resolve()),str(directory),'guidance'],input=('\n'.join(' '.join(str(int(value)) for value in row) for row in cases)+'\n').encode())
    stride=128000+80;assert len(output)==len(cases)*stride,len(output)
    counts=Counter();fixtures=[]
    for index,row in enumerate(cases):
        values=row[1:17];player=row[17:20];speed,valid,x,y,dx,dy=row[20:];set_state(values)
        for field,value in zip((0x13424,0x13430,0x1343c),player):im.write(field,'<i',value)
        im.write(0x7612,'<B',speed);im.write(0x10be8,'<h',dx);im.write(0x10be6,'<h',dy)
        projected[:]=[valid,x,y];messages.clear();requested.clear()
        im.call(0xb9238,stack=(0,319,0,199));im.call(0xc0634,stack=(199,0,319,0));video.reset()
        for plane in video.planes:plane[:]=bytes([99])*16000
        try:im.call(0xa0f40,limit=3000000)
        except RuntimeError as error:raise RuntimeError((index,row,str(error))) from error
        assert messages in ([],[0x3294]),messages
        expected=struct.pack('<20i',*state(),bool(messages),*requested)+bytes(video.pixels())+bytes(video.coverage())
        actual=output[index*stride:(index+1)*stride]
        assert actual==expected,(index,row,[(i,(i-80)%64000%320,(i-80)%64000//320,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:20],list(struct.unpack('<20i',actual[:80])),state())
        if index%17==0:fixtures.append(' '.join(str(int(value)) for value in row+state()+[bool(messages),*requested]))
        counts['beacon' if values[2] else 'runway']+=1
        if index>=768 and not values[2]:counts['height_'+str(state()[-1])]+=1
        if values[2] and not state()[2]:counts['beacon_reached']+=1
    if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
    print(f'ILS guidance agrees in {len(cases)} original pixel/coverage/state/projection/radio frames: {dict(counts)}')
else:
    im.cpu.mem_map(0x300000,0x20000)
    sites={};ports={};messages=[];stops=[];voices=[]
    def terrain(image):
        x=image.cpu.reg_read(r.UC_X86_REG_EDX)&65535;z=image.cpu.reg_read(r.UC_X86_REG_EBX)&65535
        image.cpu.reg_write(r.UC_X86_REG_EAX,sites.get((x,z),65535));image.return_from()
    im.intercept(0xb0d80,'Supply the selected route cell terrain handle without changing its SSD lookup semantics',terrain)
    def category(image):
        handle=image.cpu.reg_read(r.UC_X86_REG_EAX)&65535
        image.cpu.reg_write(r.UC_X86_REG_EAX,ports.get(handle,(-1,))[0]&0xffffffff);image.return_from()
    im.intercept(0xb7a3c,'Supply the independently verified SSD type for terrain/carrier handles',category)
    def port(image):
        handle=image.cpu.reg_read(r.UC_X86_REG_EAX)&65535
        address=0x310000+handle*16
        image.cpu.mem_write(address,struct.pack('<2hH',*ports[handle][1:4]));image.cpu.reg_write(r.UC_X86_REG_EAX,address);image.return_from()
    im.intercept(0xb6e48,'Supply initialised SSD custom port words; native selection and beacon placement execute',port)
    im.intercept(0xb6e88,'Supply the carrier SSD destroyed bit independently of its actor retirement flags',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,ports[image.cpu.reg_read(r.UC_X86_REG_EAX)&65535][4]),image.return_from()))
    im.intercept(0x81198,'Observe exact original ILS selection radio requests',lambda image:(messages.append(image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data),image.return_from()))
    im.intercept(0xa4edc,'Observe the normal-priority afterburner-stop sample at the audio boundary',lambda image:(stops.append(image.cpu.reg_read(r.UC_X86_REG_EAX)),image.return_from()))
    im.intercept(0xa5a9c,'Observe the damage-dependent ILS music-cue request at the audio boundary',lambda image:(voices.append(image.cpu.reg_read(r.UC_X86_REG_EAX)),image.return_from()))
    cases=[]
    for index in range(1536):
        values=initial(index);values[0]=int(index%11==0)
        route_count=index%5;route=[(rng.randrange(200),rng.randrange(200)) for _ in range(route_count)]
        static=[];carriers=[]
        if route:
            for endpoint in [route[-1],route[0]]:
                if index%4==0 and endpoint not in [tuple(site[:2]) for site in static]:static.append([*endpoint,rng.randrange(-2000,2001),rng.randrange(-2000,2001),rng.randrange(65536)])
                for variant in range(3):
                    cell=endpoint if variant!=2 else (rng.randrange(200),rng.randrange(200))
                    carriers.append([cell[0]*2048*256,0,cell[1]*2048*256,rng.randrange(-2000,2001),rng.randrange(-2000,2001),rng.randrange(65536),int((index+variant)%5==0),[0,8,16][(index+variant)%3] if index%7==0 else 0,1 if variant!=1 else index%3,50 if variant!=2 else 49])
        row=[index,*values,index%3,int(index%17==0),int(index%19==0),int(index%23==0),index%2,int(index%6==0),route_count]
        for x,z in route:row.extend([x*2048+1024,z*2048+1024])
        row.append(len(static))
        for site in static:row.extend(site)
        row.append(len(carriers))
        for carrier in carriers:row.extend(carrier)
        cases.append(row)
    output=subprocess.check_output([str((a.build/'landing_probe').resolve()),str(directory),'destination' if a.destination_only else 'selection'],input=('\n'.join(' '.join(str(int(value)) for value in row) for row in cases)+'\n').encode()).decode().splitlines()
    assert len(output)==len(cases)
    counts=Counter()
    for index,(row,line) in enumerate(zip(cases,output)):
        set_state(row[1:17]);craft,inhibited,crashed,ejected,damaged,realistic,route_count=row[17:24];at=24
        route=[]
        for item in range(route_count):
            x,z=row[at:at+2];at+=2;route.append((x//2048,z//2048))
        im.cpu.mem_write(0x300000,struct.pack('<H'+'H'*len(route),len(route),*[x|(z<<8) for x,z in route]));im.write(0x5978,'<I',0x300000);im.write(0x597c,'<H',65535)
        sites.clear();ports.clear();site_count=row[at];at+=1
        for item in range(site_count):
            x,z,ox,oz,heading=row[at:at+5];at+=5;handle=100+item;sites[x,z]=handle;ports[handle]=(50,ox,oz,heading,False)
        im.write(0x128c8,'<50I',*([0]*50));carrier_count=row[at];at+=1
        for item in range(carrier_count):
            x,y,z,ox,oz,heading,destroyed,flags,side,kind=row[at:at+10];at+=10
            slot=49-item;handle=1+item;address=0x301000+slot*256;profile=0x305000+slot*256
            im.write(0x128c8+slot*4,'<I',address);im.cpu.mem_write(address,struct.pack('<3i',x,y,z));im.cpu.mem_write(address+0x24,struct.pack('<H',handle));im.cpu.mem_write(address+0x2f,bytes([flags]));im.cpu.mem_write(address+0x2a,struct.pack('<I',profile));im.cpu.mem_write(profile+0x1f,bytes([side]));ports[handle]=(kind,ox,oz,heading,destroyed)
        im.write(0xabe9,'<B',inhibited);im.write(0x86ce,'<B',crashed);im.write(0x12c04,'<H',ejected);im.write(0x11b2a,'<H',craft);im.write(0x1347a,'<B',6 if realistic else 0);im.write(0x8e18,'<d',1 if damaged else 0)
        im.write(0xac58,'<i',-16384);im.write(0xac5c,'<i',0);messages.clear();stops.clear();voices.clear()
        im.call(0xa0bc0 if a.destination_only else 0x847ec,limit=2000000)
        navigation=bool(stops);waypoint=im.read(0x597c,'<H')[0]
        expected=state()+[int(navigation),int(bool(stops)),voices[0] if voices else -1,waypoint-1 if waypoint!=65535 else -1,int(navigation)]
        if navigation:expected.extend([im.read(0x14962,'<H')[0],*[im.read(field,'<Q')[0] for field in (0x14360,0x148b8,0x148b0,0x148a8)]])
        mapping={0x323c:0,0x3258:1,0x3270:2};expected.extend([len(messages),*[mapping[value] for value in messages]])
        actual=list(map(int,line.split()))
        assert actual==expected,(index,row,actual,expected)
        counts['engaged' if state()[0] else 'disabled']+=1
        if state()[0]:counts['carrier' if state()[1] else 'runway']+=1
    print(f'ILS {"direct destination" if a.destination_only else "key/destination"} selection agrees in {len(cases)} original updates: {dict(counts)}')
