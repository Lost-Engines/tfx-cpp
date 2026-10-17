#!/usr/bin/env python3
"""Compare live SSD parts, streams, custom state, drawing and collision dispatch with native 2.05."""
import argparse
import json
from pathlib import Path
import struct
import subprocess

from unicorn import x86_const as r
from native_reference import NativeReference


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    args = parser.parse_args()
    data_dir = args.research / 'installs/cd_1994_09/TFX'
    text = (args.research / 'analysis/maps/data.js').read_text()
    objects = json.loads(text[text.index('=')+1:].strip().removesuffix(';'))['objects']
    image = NativeReference(data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 0x30000)
    definition, instance = 0x300000, 0x310000
    calls, requests, reports = [], [], []
    collisions = 0
    raw = b''
    distance = 0

    def bind(im):
        im.cpu.mem_write(im.cpu.reg_read(r.UC_X86_REG_EAX), struct.pack('<H', im.cpu.reg_read(r.UC_X86_REG_EDX)))
        im.return_from()
    image.intercept(0xb4d3c, 'Resolve model indices to stable symbolic handles; no renderer or allocator runs in this VM comparison.', bind)
    def resolve(im):
        im.cpu.reg_write(r.UC_X86_REG_EAX,instance)
        im.return_from()
    image.intercept(0xc8568, 'This controlled case has one SSD instance, handle zero.', resolve)
    def collision(im):
        nonlocal collisions
        collisions += 1
        im.return_from()
    image.intercept(0xb7a30, 'Record a collision callback; damage to the separate querying object is outside this VM test.', collision)
    def report(im):
        reports.append(struct.unpack('<i',struct.pack('<I',im.cpu.reg_read(r.UC_X86_REG_EAX)))[0])
        im.return_from()
    image.intercept(0xb7a3c, 'Record damage percentage callback; do not run world classification here.', report)
    def measure(im):
        im.write(0xabe4,'<h',distance)
        im.return_from()
    image.intercept(0xb6be8, 'Explicit anchor-distance input; camera placement is tested separately from VM control flow.', measure)
    for file, anchored in [(0xb635c,False),(0xb6438,True),(0xb65b0,False),(0xb668c,True),(0xb6810,False),(0xb68dc,True),(0xb6a44,False)]:
        def draw(im, anchored=anchored, kind=int(file==0xb6a44)):
            part = im.cpu.reg_read(r.UC_X86_REG_EAX) & 65535
            anchor = im.cpu.reg_read(r.UC_X86_REG_EDX) & 65535
            xyz = struct.unpack_from('<3h',raw,10+anchor*6) if anchored else (0,0,0)
            calls.append((part,*xyz,kind))
            im.return_from()
        image.intercept(file, 'Record model-part draw placement; native polygon rendering is tested by the renderer checks.', draw)
    def light(im):
        requests.append((79,4,*[im.cpu.reg_read(reg)&65535 for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]))
        im.return_from()
    image.intercept(0xb626c,'Record an authored temporary-effect request; placed pool delivery is checked separately.',light)
    def offset(im):
        requests.append((72,3,*[im.cpu.reg_read(reg)&65535 for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX)]))
        im.return_from()
    image.intercept(0xb7350,'Record authored offset request; runtime effect allocation is outside this VM test.',offset)

    payload, expected, labels = [], [], []
    for obj in objects.values():
        raw = (args.research / 'extracted/cd_1994_09/resources' / obj['path']).read_bytes()
        assert max(obj['entries']) < len(raw), obj['id']
        image.cpu.mem_write(definition,raw)
        image.cpu.mem_write(instance,bytes(65536))
        for part in range(obj['part_count']):
            image.cpu.mem_write(instance+16+29*part+9,b'\xff\xff')
        image.write(0x20b98,'<I',definition)
        image.write(0x20b9c,'<I',instance)
        image.write(0x20ba0,'<I',image.native(0xb6c84))
        image.write(0x20c4a,'<H',0)
        image.write(0x1b250,'<I',definition)
        image.write(0xac3c,'<I',image.native(0xb7a30))
        image.write(0xac14,'<I',image.native(0xb7a3c))
        requests.clear()
        image.call(0xb54dc,eax=definition+obj['entries'][0])
        assert not any(request[0]==79 for request in requests),('unexpected initial effect request',obj['names'])
        commands = [(999,0,0,1,0,0,0,0,0,0,0,0,0)]
        # All authored events execute on the same instance, exposing persistent damage and restoration.
        for entry in range(1,len(obj['entries'])):
            commands.append((entry,0,0,1,2000,128,100,0,0,0,0,0,0))
            commands.append((999,1,0,1,0,128,100,0,0,0,0,0,0))
        # Exercise every authored collision volume at its centre and through its full diagonal.
        for at,op,operands in obj['programs']:
            if op not in (12,13,14,28,29,31,35,47,48,49,50,51,52,53,64,65,80,81,82):
                continue
            lo,hi = [struct.unpack('<h',struct.pack('<H',v))[0] for v in operands[:3]], [struct.unpack('<h',struct.pack('<H',v))[0] for v in operands[3:6]]
            middle = [(a+b)//2 for a,b in zip(lo,hi)]
            for player in (0,1):
                commands.append((2,0,player,1,2000,128,100,*middle,*middle))
                commands.append((1,0,player,1,0,128,100,*lo,*hi))
        payload.append(f"{int(obj['id'],16)} {len(commands)}\n")
        for command in commands:
            entry,animate,player,enabled,damage,status,distance,*movement = command
            payload.append(' '.join(map(str,command))+'\n')
            labels.append((obj['names'] or [obj['id']],command))
            image.write(0x20c4c,'<BB',player,enabled)
            image.write(0x20c46,'<H',damage)
            image.write(0x20b8c,'<6h',*movement)
            image.write(0xabe4,'<h',distance)
            image.cpu.mem_write(image.native(0x70aa4+0x47c82),struct.pack('<H',status))
            for offset,fmt,value in [(0xabe8,'<B',0),(0xabe9,'<B',0),(0xabea,'<B',0),(0xabf2,'<h',0),(0xabec,'<h',-1),(0xabee,'<h',0),(0xabf0,'<H',0)]:image.write(offset,fmt,value)
            calls.clear();requests.clear();reports.clear();collisions=0
            if animate:
                for part in range(obj['part_count']):
                    for parameter in range(8 if obj['flags']&256 else 1):
                        image.call(0xb6ce0,eax=part,edx=parameter)
            elif entry < len(obj['entries']):
                image.write(0x20ba0,'<I',image.native(0xb6c84))
                image.call(0xb54dc,eax=definition+obj['entries'][entry])
            memory = bytes(image.cpu.mem_read(instance,16+obj['part_count']*29+obj['custom_bytes']))
            values=[bool(memory[2]&16),bool(memory[15]&1),memory[2]&15,*struct.unpack_from('<2H',memory,3)]
            values += [(obj['custom_bytes']+1)//2,*struct.unpack_from('<'+str(obj['custom_bytes']//2)+'H',memory,16+29*obj['part_count'])]
            values += [obj['part_count']]
            for part in range(obj['part_count']):
                base=16+29*part
                rotation_at=struct.unpack_from('<H',memory,base+27)[0]*2
                rotation=struct.unpack_from('<3H',raw,rotation_at) if rotation_at else (0,0,0)
                values += [struct.unpack_from('<H',memory,base+9)[0],memory[base+8],*rotation,*memory[base:base+8],*[v*2 for v in struct.unpack_from('<8H',memory,base+11)]]
            values += [collisions,image.read(0xabe8,'<B')[0],image.read(0xabe9,'<B')[0],image.read(0xabea,'<B')[0],image.read(0xabf2,'<h')[0],image.read(0xabec,'<h')[0],image.read(0xabee,'<h')[0],image.read(0xabf0,'<H')[0],len(calls)]
            for call in calls:values.extend(call)
            values.append(len(requests))
            for request in requests:values.extend(request)
            values += [len(reports),*reports]
            expected.append([int(v) for v in values])
    result=subprocess.run([str(args.build/'instance_probe'),str(data_dir)],input=''.join(payload),text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr)
    actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()]
    assert len(actual)==len(expected),(len(actual),len(expected))
    for index,(a,b) in enumerate(zip(actual,expected)):
        if a!=b:
            first=next(i for i,(x,y) in enumerate(zip(a,b)) if x!=y) if len(a)==len(b) else 'length'
            raise AssertionError((index,labels[index],first,'C++',a,'native',b))
    print(f'{len(objects)} definitions; {len(expected)} persistent native SSD states agree')


if __name__=='__main__':main()
