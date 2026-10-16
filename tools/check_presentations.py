#!/usr/bin/env python3
"""Compare typed retail graph decoding and original numeric parser handlers.

All nine retail programs are decoded independently. Original branch, numeric
assignment and gosub/return handlers execute with supplied variable values.
Media scheduling, menus, pilot I/O and complete campaign execution are outside
this control-flow comparison.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();programs=json.loads((args.research/'analysis/presentations/programs.json').read_text());data_dir=args.research/'installs/cd_1994_09/TFX'
image=NativeReference(data_dir/'TFX.DAT');image.cpu.mem_map(0x300000,0x10000);image.write(0xab41,'<B',1);image.write(0x1afee,'<H',1)
rows=[];expected_cases=[];branches=assignments=0
for program in programs:
    expected=bytearray()
    def word(*values):
        for value in values:expected.extend(struct.pack('<I',value&0xffffffff))
    def string(value):
        raw=value.encode('cp437');word(len(raw));expected.extend(raw)
    word(len(program['variables']))
    for variable in program['variables']:string(variable['name']);word(variable['string_value'])
    word(len(program['functions']))
    for function_index,function in enumerate(program['functions']):
        string(function['name']);word(len(function['nodes']))
        for node in function['nodes']:
            kind=node['type'];raw=bytes.fromhex(node['payload_hex']);word(node['offset'],kind)
            if kind in (0,1,2):
                string(node.get('resource',''));word(node.get('fade_in',0),node.get('fade_out',0),node.get('frame_delay_bios_ticks',0),node['wait_ticks'],int(node.get('play_until_end',False)),int('text' in node))
                if 'text' in node:
                    layout=node['text']['native_layout'];word(layout['x'],layout['y'],layout['alignment'],layout['shadow'],layout['reveal'],layout['font'],layout['colour']);string(node['text']['text'])
            elif kind==3:word(raw[0]!=0,struct.unpack_from('<I',raw,1)[0],raw[5],struct.unpack_from('<I',raw,6)[0],raw[10]==1,raw[11],raw[12])
            elif kind==10:word(struct.unpack_from('<I',raw)[0],raw[4],struct.unpack_from('<I',raw,5)[0])
            elif kind in (5,8,9,13):string(node['resource']);word(struct.unpack_from('<H',raw,9)[0] if kind==9 else 0)
            elif kind==11:word(raw[0],raw[1],struct.unpack_from('<h',raw,2)[0])
            elif kind not in (4,7,12):raise AssertionError(('unexpected retail action',kind))
            if kind not in (3,10):continue
            ordinal=struct.unpack_from('<I',raw,1 if kind==3 else 0)[0]
            name=program['variables'][ordinal]['name'] if kind==10 or raw[0] else 'unused'
            image.write(0x1ad62,'<'+str(len(name)+1)+'s',name.encode()+bytes(1));image.cpu.mem_write(0x300000,bytes(9)+name.encode()+bytes(1))
            payload=bytearray(raw);struct.pack_into('<I',payload,1 if kind==3 else 0,0x300000)
            if kind==3:
                struct.pack_into('<I',payload,13,0x300100);image.cpu.mem_write(0x300100,bytes([5]));branches+=1
                cases=[struct.unpack_from('<I',raw,6)[0],struct.unpack_from('<I',raw,6)[0]^1] if raw[0] else [0]
            else:cases=[0,42,0xffffffff,0x80000000];assignments+=1
            image.cpu.mem_write(0x300200,bytes(payload))
            for value in cases:
                image.write(0x1a400,'<I',value)
                if kind==3:
                    image.write(0x1ad14,'<I',0x300300);image.write(0x1ad1c,'<I',0x300400);image.write(0x1afdc,'<H',0)
                    image.call(0xb22d8,eax=0x300200);destination=image.read(0x1ad14,'<I')[0];depth=image.read(0x1afdc,'<H')[0]
                    assert destination in (0x300100,0x300300)
                    if depth:
                        image.call(0xb2574);assert image.read(0x1ad1c,'<I')[0]==0x300400
                    values=[int(destination==0x300100),depth]
                else:
                    image.call(0xb28b8,eax=0x300200);values=[image.read(0x1a400,'<I')[0]]
                rows.append(f"{'B' if kind==3 else 'A'} {int(program['id'],16)} {function_index} {node['index']} {value}\n");expected_cases.append(values)
    result=subprocess.run([str(args.build/'presentation_probe'),str(data_dir)],input=f"D {int(program['id'],16)}\n".encode(),capture_output=True,check=True).stdout
    assert result==expected,(program['name'],len(result),len(expected),next((i for i,(a,b) in enumerate(zip(result,expected)) if a!=b),None))
result=subprocess.run([str(args.build/'presentation_probe'),str(data_dir)],input=''.join(rows),capture_output=True,text=True,check=True)
actual=[[int(v) for v in line.split()] for line in result.stdout.splitlines()];assert len(actual)==len(expected_cases)
for row,a,b in zip(rows,actual,expected_cases):assert a==b,(row,a,b)
print(len(programs),'retail graphs decode exactly;',branches,'branch records and',assignments,'assignments agree with original execution across',len(rows),'numeric cases, including native gosub return state')
