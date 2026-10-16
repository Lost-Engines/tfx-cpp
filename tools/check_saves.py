#!/usr/bin/env python3
"""Compare pilot save encoding/reading with original serialization routines.

File reads/writes are redirected to memory. The native thirty-slot layout,
string/numeric choices, call-site lookup and resume modes execute unchanged.
Original installation saves are only read; no original file is modified.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';program=next(p for p in json.loads((args.research/'analysis/presentations/programs.json').read_text()) if p['name']=='tfx');image=NativeReference(directory/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x40000);rng=random.Random(0xb3aa8)
output=bytearray();input_data=b'';read_at=0

def write(im):
    pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);length=im.cpu.reg_read(r.UC_X86_REG_EDX);output.extend(im.cpu.mem_read(pointer,length));im.cpu.reg_write(r.UC_X86_REG_EAX,length);im.return_from()
def read(im):
    global read_at
    pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);length=im.cpu.reg_read(r.UC_X86_REG_EDX);data=input_data[read_at:read_at+length];assert len(data)==length;im.cpu.mem_write(pointer,data);read_at+=length;im.cpu.reg_write(r.UC_X86_REG_EAX,length);im.return_from()
image.intercept(0xcc434,'Capture original writes to a memory stream; no file is written.',write)
image.intercept(0xcc41c,'Supply saved bytes from a memory stream; no file is opened.',read)
def fail(im):raise RuntimeError('original save reported an invalid parser pointer')
image.intercept(0xb0eb0,'Report a native serialization error instead of entering a fatal screen.',fail)
functions=program['functions'];nodes=[];node_pointer=0x321000
for f,function in enumerate(functions):
    pointer=0x320000+f*25;count=len(function['nodes']);cpu.mem_write(pointer,struct.pack('<3IH',pointer+25 if f+1<len(functions) else 0,pointer-25 if f else 0,node_pointer,count));group=[]
    for n in range(count):
        p=node_pointer+n*13;group.append(p);cpu.mem_write(p,bytes([function['nodes'][n]['type']])+struct.pack('<3I',p+13 if n+1<count else 0,p-13 if n else 0,0))
    nodes.append(group);node_pointer+=count*13
image.write(0x1ad3c,'<I',0x320000);image.write(0x1afea,'<H',len(functions))
variables=program['variables'];cpu.mem_write(image.data+0x1ad44,bytes([int(v['string_value']) for v in variables])+bytes(30-len(variables)))
rows=[];expected=[];read_cases=0

def normalise(raw):
    result=bytearray(raw);at=0
    for v in variables:
        if v['string_value']:
            end=result.index(0,at,at+21);result[end:at+21]=bytes(at+21-end);at+=21
        else:at+=4
    return bytes(result)
def verify_read(raw,values,callers,resume):
    global input_data,read_at,read_cases
    input_data=raw;read_at=0
    image.write(0x1ad1c,'<I',0x333333)
    image.call(0xb3c14,eax=7,limit=1000000);assert read_at==len(raw)
    for index,(v,value) in enumerate(zip(variables,values)):
        actual=image.read(0x1a400+index*4,'<I')[0]
        if v['string_value']:assert bytes(cpu.mem_read(actual,21)).split(bytes(1))[0].decode()==value
        else:assert actual==value
    assert image.read(0x1afdc,'<H')[0]==len(callers)
    assert [image.read(0x1ab68+i*4,'<I')[0] for i in range(len(callers))]==[nodes[f][n] for f,n in callers]
    assert image.read(0x1ad1c,'<I')[0]==(nodes[resume[0]][resume[1]] if resume else 0x333333)
    read_cases+=1
for case in range(512):
    values=[];row=['1']
    for index,v in enumerate(variables):
        if v['string_value']:
            text=rng.choice(('',v['name'].upper(),'TEST-PILOT','A'*20));values.append(text);row.append(text or '-');pointer=0x330000+index*32;cpu.mem_write(pointer,text.encode()+bytes(21-len(text)));image.write(0x1a400+index*4,'<I',pointer)
        else:
            value=rng.randrange(2**32);values.append(value);row.append(value);image.write(0x1a400+index*4,'<I',value)
    for index in range(len(variables),30):value=rng.randrange(2**32);row.append(value);image.write(0x1a400+index*4,'<I',value)
    callers=[(rng.randrange(len(functions)),0) for _ in range(case%6)];callers=[(f,rng.randrange(len(nodes[f]))) for f,n in callers];image.write(0x1afdc,'<H',len(callers));row.append(len(callers))
    for index,(f,n) in enumerate(callers):image.write(0x1ab68+index*4,'<I',nodes[f][n]);row.extend((f,n))
    mode=case%4;f=rng.randrange(len(functions));n=rng.randrange(len(nodes[f]));
    if mode==1 and n==0:mode=2
    if mode==3 and n+1==len(nodes[f]):mode=2
    image.write(0x1ad1c,'<I',nodes[f][n]);resume=None if mode==0 else (f,n-1 if mode==1 else n+1 if mode==3 else n);row.extend(resume or (-1,-1))
    output.clear();image.call(0xb3aa8,eax=7,edx=mode,limit=1000000);raw=bytes(output);verify_read(raw,values,callers,resume);rows.append(' '.join(map(str,row))+'\n');expected.append(raw)
for path in sorted(directory.glob('TFXSAV.*')):
    raw=path.read_bytes();rows.append('0 '+str(len(raw))+' '+' '.join(map(str,raw))+'\n');expected.append(normalise(raw))
result=subprocess.run([str(args.build/'save_probe'),str(directory)],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
actual=[]
for line in result.stdout.splitlines():
    fields=[int(v) for v in line.split()];assert fields[0]==len(fields)-1;actual.append(bytes(fields[1:]))
assert len(actual)==len(expected)
for index,(a,b) in enumerate(zip(actual,expected)):assert a==b,(index,len(a),len(b),next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),None))
print('512 native save/write/read states agree, including all four resume modes and return stacks;',len(expected)-512,'existing DOS saves decode/re-encode with only post-terminator padding cleared')
