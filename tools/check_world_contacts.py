#!/usr/bin/env python3
"""Check native fixed-scenery loads and nearby mobile-surface regions."""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference
from check_actors import dataset


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
    parser.add_argument('--build',type=Path,default=Path('build'))
    parser.add_argument('--save-fixture',type=Path)
    args=parser.parse_args();rng=random.Random(0x75628)
    data=args.research/'installs/cd_1994_09/TFX';image=NativeReference(data/'TFX.DAT');image.cpu.mem_map(0x300000,0x50000)
    created=[];events=[];hit=[]
    def create(im):
        at=im.cpu.reg_read(r.UC_X86_REG_EAX);name=bytes(im.cpu.mem_read(at,10)).split(b'\0')[0].decode('ascii').lower();created.append(name)
        im.cpu.reg_write(r.UC_X86_REG_EAX,len(created));im.return_from()
    image.intercept(0xb4d98,'Capture fixed-placement SSD resource requests; original profile lookup, record mutation, event dispatch and list links execute.',create)
    image.intercept(0xb52d4,'Capture fixed-placement initial events without needing the graphical object loader.',lambda im:(events.append((im.cpu.reg_read(r.UC_X86_REG_EAX),im.cpu.reg_read(r.UC_X86_REG_EDX)&65535)),im.return_from()))
    image.intercept(0xb76a8,'Capture mobile actor eligibility after the original broad-phase region test; SSD collision is checked separately.',lambda im:(hit.append(1),im.return_from()))
    rows=[];expected=[];synthetic=[];placements=0;retail_placements=0
    programs=json.loads((args.research/'analysis/waypoints/programs.json').read_text())['programs']
    profile_rows=dataset(args.research/'analysis/entities/data.js')['records']
    retail_profiles=struct.pack('<2H',0,len(profile_rows))+b''.join(bytes.fromhex(p['hex']) for p in profile_rows)
    pairs=[(retail_profiles,(args.research/'extracted/cd_1994_09/resources'/p['path']).read_bytes(),False) for p in programs]
    authored_profiles=struct.pack('<2H',0,2)+b''.join(struct.pack('<B20s10sBH',17,b'Test',name,0,index) for index,name in enumerate((b'carrier',b'platform')))
    for case in range(128):
        raw=bytearray()
        for index in range(case%24):
            if index%3==0:raw.extend(struct.pack('<HB',1,15))
            body=struct.pack('<B3iHIH',17,*[rng.randrange(-100000000,100000001) for _ in range(3)],index%2,0,rng.choice((0,1,5,65535)))
            raw.extend(struct.pack('<H',len(body))+body)
        raw.extend(b'\0\0');pairs.append((authored_profiles,bytes(raw),True))
    for profiles,raw,authored in pairs:
        at=4;index=0
        image.cpu.mem_write(image.data+0x127ec,bytes(256*4))
        while at<len(profiles):
            length={14:74,15:58,16:46,17:34}[profiles[at]&127];pointer=0x320000+index*128
            image.cpu.mem_write(pointer,profiles[at:at+length]);image.write(0x127ec+index*4,'<I',pointer);at+=length;index+=1
        image.cpu.mem_write(0x300000,raw);image.write(0x5980,'<I',0);created.clear();events.clear();at=0;records={};index=0
        while int.from_bytes(raw[at:at+2],'little'):
            size=int.from_bytes(raw[at:at+2],'little');body=raw[at+2:at+2+size]
            if body[0]==17:
                records[0x300000+at+2]=(index,struct.unpack_from('<H',body,13)[0]);image.call(0x75628,eax=0x300000+at+2)
            at+=2+size;index+=1
        pointer=image.read(0x5980,'<I')[0];values=[]
        while pointer:
            original_index,profile_id=records[pointer];body=bytes(image.cpu.mem_read(pointer,21));handle=struct.unpack_from('<H',body,13)[0];name=created[handle-1];event=struct.unpack_from('<H',body,19)[0]
            if event:assert (handle,event) in events
            values.extend([original_index,profile_id,*struct.unpack_from('<3i',body,1),event,len(name),*name.encode()]);pointer=struct.unpack_from('<I',body,15)[0];placements+=1
        if not authored:retail_placements+=len(records)
        rows.append(['P',profiles.hex(),raw.hex()]);expected.append(values);synthetic.append(authored)
    for case in range(8192):
        previous=[rng.randrange(-500000,500001) for _ in range(3)];current=[v+rng.randrange(-6000,6001) for v in previous]
        if case%7==0:previous=[rng.randrange(-2147483648,2147483648) for _ in range(3)];current=[rng.randrange(-2147483648,2147483648) for _ in range(3)]
        image.call(0x7c528,eax=previous[0]&0xffffffff,edx=previous[1]&0xffffffff,ebx=previous[2]&0xffffffff,ecx=current[0]&0xffffffff,stack=(current[1]&0xffffffff,current[2]&0xffffffff))
        centre=list(image.read(0x12990,'<3i'));extent=[image.read(a,'<i')[0] for a in (0x129a4,0x129a0,0x1299c)]
        if case%2:position=[struct.unpack('<i',struct.pack('<I',(c+e+delta)&0xffffffff))[0] for c,e,delta in zip(centre,extent,[rng.choice((-1,0,1)) for _ in range(3)])]
        else:position=[struct.unpack('<i',struct.pack('<I',(c+rng.randrange(-1000,1001)*256)&0xffffffff))[0] for c in centre]
        image.write(0x128c8,'<50I',0x330000,*([0]*49));image.cpu.mem_write(0x330000,bytes(49));image.cpu.mem_write(0x330000,struct.pack('<3i',*position));hit.clear();image.call(0x7c724)
        rows.append(['R',*previous,*current,*position]);expected.append([*centre,*extent,int(bool(hit))]);synthetic.append(True)
    output=subprocess.run([str(args.build/'world_contacts_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
    actual=[[int(v) for v in line.split()] for line in output.stdout.splitlines()];assert len(actual)==len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i][:3],a,b)
    if args.save_fixture:
        lines=[]
        for row,values,authored in zip(rows,expected,synthetic):
            if not authored:continue
            digest=14695981039346656037
            for val in values:
                for byte in struct.pack('<I',val&0xffffffff):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
            lines.append(' '.join(map(str,row+[digest]))+'\n')
        args.save_fixture.write_text(''.join(lines));subprocess.run([str(args.build/'world_contacts_probe'),str(args.save_fixture)],check=True)
    print(len(programs),'retail programs audited:',retail_placements,'fixed placements;',placements-retail_placements,'authored placements and 8192 native nearby-surface regions/edge tests agree')


if __name__=='__main__':main()
