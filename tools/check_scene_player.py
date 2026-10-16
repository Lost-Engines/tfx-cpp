#!/usr/bin/env python3
"""Compare integrated still/text scene handlers with original VGA execution.

Only asset loading, hardware retraces/flip/palette output and timer values are
supplied externally. Native preparation, reveal, caption drawing, input and
scene-loop control execute together. Movie decoding/clocks are separate checks.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();root=args.research;directory=root/'installs/cd_1994_09/TFX';programs=json.loads((root/'analysis/presentations/programs.json').read_text());catalog=json.loads((root/'analysis/resources/catalog.json').read_text())['entries'];paths={name:row['path'] for row in catalog for name in row['recovered_names']+row['candidate_names']}
image=NativeReference(directory/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x40000);video=VgaCapture(image);image.write(0x1b238,'<I',0x300400);image.write(0x1b23c,'<I',0x300500);cpu.mem_write(0x300500,bytes(256));image.write(0x1a48c,'<I',0x302000)
frame=0;fast=0;expected=[];background=bytes(64000)
for offset in (0xd37a4,0xc6348,0xc6f64,0xc62d4,0xc9bdc,0xc734c,0xc733e):image.intercept(offset,'Asset I/O or hardware output boundary; original scene loop remains active.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
image.intercept(0xde454,'Palette output has its own complete native comparison.',lambda im:im.return_from(4))
image.intercept(0xa6134,'Supply the scene fast-counter sample.',lambda im:(im.write(0x16f2c,'<I',fast),im.return_from()))
image.intercept(0xc7370,'Clear the emulated drawing page.',lambda im:(video.reset(),im.return_from()))
def backdrop(im):
    for plane in range(4):video.planes[plane][:]=background[plane::4]
    im.return_from()
image.intercept(0xca5aa,'Supply the decoded still image; full bitmap extraction is separately verified.',backdrop)
def external(im):
    pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);name=bytes(im.cpu.mem_read(pointer,80)).split(bytes(1))[0].split()[0].decode().lower();content=(root/'extracted/cd_1994_09/resources'/paths['english/'+name]).read_bytes()
    descriptor=bytearray(im.cpu.mem_read(im.read(0x1ad04,'<I')[0],16));struct.pack_into('<HI',descriptor,10,len(content),0x310000);im.cpu.mem_write(0x310000,content+bytes(1));im.cpu.mem_write(0x300200,bytes(descriptor));im.write(0xab42,'<B',1);im.cpu.reg_write(r.UC_X86_REG_EAX,0x300200);im.cpu.reg_write(r.UC_X86_REG_EIP,im.native(0xb1714))
image.intercept(0xb1610,'Supply the actual language file and tail-call original preparation.',external)
variables=next(p for p in programs if p['name']=='tfx')['variables'];image.write(0x1afee,'<H',len(variables))
for index,variable in enumerate(variables):
    name=variable['name'];image.write(0x1ad44+index,'<B',variable['string_value']);cpu.mem_write(image.data+0x1ad62+index*21,name.encode()+bytes(21-len(name)))
    if variable['string_value']:
        value={'callsign':'MiG','firstname':'Ada'}.get(name,'Slowriot').encode();pointer=0x320000+index*256;cpu.mem_write(pointer,value+bytes(1));image.write(0x1a400+index*4,'<I',pointer)
    else:image.write(0x1a400+index*4,'<I',0xfffffffe if name=='score' else 7+index*12345)
def begin(im):
    global fast
    fast=frame*3
    if frame in (3,10):cpu.mem_write(0x300400,bytes([57 if frame==3 else 1]))
for offset in (0xb1f0a,0xb1df7):image.intercept(offset,'Supply input/time at the beginning of each native content iteration.',begin)
def snapshot(im):
    global frame
    digest=14695981039346656037
    for pixel in video.pixels():digest=((digest^pixel)*1099511628211)&0xffffffffffffffff
    expected.append([digest,image.read(0x241b6,'<H')[0] if reveal else total]);frame+=1
for offset in (0xb1f30,0xb1e17):image.intercept(offset,'Capture the complete native content frame without changing scene control flow.',snapshot)
rows=[];cases=[];expected_groups=[]
for program in programs:
    for function_index,function in enumerate(program['functions']):
        for node in function['nodes']:
            if node['type'] not in (1,2):continue
            raw=bytearray.fromhex(node['payload_hex']);kind=node['type'];frame=fast=0;video.reset();image.write(0x241b6,'<H',0);image.write(0xab35,'<B',0);image.write(0xab40,'<B',0);image.write(0xab42,'<B',0);image.write(0x1ad04,'<I',0);cpu.mem_write(0x300400,bytes(1));cpu.mem_write(image.data+0x21000,bytes(range(64))*12)
            struct.pack_into('<h',raw,3 if kind==2 else 11,12)
            if kind==1:
                raw[9]=raw[10]=0;media=(root/'extracted/cd_1994_09/resources'/paths['iff/raw/'+node['resource']+'.lbm']).read_bytes();background=media[772:];cpu.mem_write(image.data+0x20ce0,media[4:772])
            else:background=bytes(64000)
            reveal=False;total=0
            if 'text' in node:
                descriptor=bytearray.fromhex(node['text']['settings_hex']);content=node['text']['text'].encode('cp437');struct.pack_into('<HI',descriptor,10,len(content),0x303000);cpu.mem_write(0x300000,bytes(descriptor));cpu.mem_write(0x303000,content+bytes(1));struct.pack_into('<I',raw,5 if kind==2 else 14,0x300000);reveal=bool(descriptor[7])
                image.call(0xb1714,eax=0x300000);total=image.read(0x1afde,'<H')[0]
            cpu.mem_write(0x301000,bytes(raw));start=len(expected);image.call(0xb1da0 if kind==2 else 0xb1e38,eax=0x301000,limit=10000000)
            expected_groups.append(expected[start:])
            rows.append(f"{int(program['id'],16)} {function_index} {node['index']}\n");cases.extend([(program['name'],function['name'],node['index'],i) for i in range(len(expected)-start)])
result=subprocess.run([str(args.build/'player_probe'),str(directory)],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
groups=[]
for line in result.stdout.splitlines():
    if line.startswith('C '):groups.append([])
    else:groups[-1].append([int(v) for v in line.split()])
assert len(groups)==len(rows)
for row,a,b in zip(rows,groups,expected_groups):
    assert a==b,(row,len(a),len(b),next(((i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y),None))
print(len(rows),'complete original still/text handlers agree across',len(expected),'composed content frames, including reveal, Space consumption and Escape termination')
