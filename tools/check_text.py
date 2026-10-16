#!/usr/bin/env python3
"""Compare all retail presentation text with original preparation and full/prefix VGA composition.

Language-file bytes and timer input are supplied boundaries. Uppercasing,
variable substitution, line splitting, native widths/centres and complete/prefix
shadow/foreground drawing execute in the original 2.05 code.
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
args=parser.parse_args();root=args.research;data_dir=root/'installs/cd_1994_09/TFX';programs=json.loads((root/'analysis/presentations/programs.json').read_text());catalog=json.loads((root/'analysis/resources/catalog.json').read_text())['entries'];paths={name:row['path'] for row in catalog for name in row['recovered_names']+row['candidate_names']}
image=NativeReference(data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x40000);video=VgaCapture(image);image.write(0x1b238,'<I',0x300400);cpu.mem_write(0x300400,bytes(1))
image.intercept(0xa6134,'Supply a stationary text timer; this comparison covers preparation/static composition, not reveal timing.',lambda im:(im.write(0x16f2c,'<I',0),im.return_from()))
def fail(im):raise RuntimeError('original text preparation reported an error')
image.intercept(0xb0eb0,'Report a native parser error rather than entering the fatal screen.',fail)
language='english'
def external(im):
    pointer=im.cpu.reg_read(r.UC_X86_REG_EAX);name=bytes(im.cpu.mem_read(pointer,80)).split(bytes(1))[0].split()[0].decode('ascii').lower();content=(root/'extracted/cd_1994_09/resources'/paths[language+'/'+name]).read_bytes()
    descriptor=bytearray(im.cpu.mem_read(im.read(0x1ad04,'<I')[0],16));struct.pack_into('<HI',descriptor,10,len(content),0x310000)
    im.cpu.mem_write(0x310000,content+bytes(1));im.cpu.mem_write(0x300200,bytes(descriptor));im.write(0xab42,'<B',1)
    # Tail-call the original recursive preparation with the supplied language file and preserved text settings.
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x300200);im.cpu.reg_write(r.UC_X86_REG_EIP,im.native(0xb1714))
image.intercept(0xb1610,'Supply the actual decoded language-file bytes; original recursive text preparation still executes.',external)
variables=next(p for p in programs if p['name']=='tfx')['variables'];image.write(0x1afee,'<H',len(variables))
for index,variable in enumerate(variables):
    name=variable['name'];image.write(0x1ad44+index,'<B',variable['string_value']);cpu.mem_write(image.data+0x1ad62+index*21,name.encode()+bytes(21-len(name)))
    if variable['string_value']:
        value={'callsign':'MiG','firstname':'Ada'}.get(name,'Slowriot').encode();pointer=0x320000+index*256;cpu.mem_write(pointer,value+bytes(1));image.write(0x1a400+index*4,'<I',pointer)
    else:image.write(0x1a400+index*4,'<I',0xfffffffe if name=='score' else 7+index*12345)
rows=[];cases=[];external_count=0;prefix_cases=0;seen_layouts=set()
for program in programs:
    for function_index,function in enumerate(program['functions']):
        for node in function['nodes']:
            if 'text' not in node:continue
            for language in (('english','french','german','spanish','italian') if '^' in node['text']['text'] else ('english',)):
                descriptor=bytearray.fromhex(node['text']['settings_hex']);content=node['text']['text'].encode('cp437');descriptor[7]=0;struct.pack_into('<HI',descriptor,10,len(content),0x303000)
                cpu.mem_write(0x300000,bytes(descriptor));cpu.mem_write(0x303000,content+bytes(1));image.write(0xab42,'<B',0)
                image.call(0xb1714,eax=0x300000,limit=5000000)
                settings=bytes(cpu.mem_read(image.read(0x1ad04,'<I')[0],16));count=image.read(0x1afe8,'<H')[0];total=image.read(0x1afde,'<H')[0];expected=bytearray();font=settings[8]
                def word(*values):
                    for value in values:expected.extend(struct.pack('<I',value&0xffffffff))
                word(count,total,font,settings[9],bool(settings[6]));height=image.call(0xb12e4)
                for line in range(count):
                    text=bytes(cpu.mem_read(image.data+0x1a4b0+line*80,80)).split(bytes(1))[0];width=image.read(0x1aaf0+line*2,'<h')[0];x=struct.unpack_from('<h',settings,2)[0];y=struct.unpack_from('<h',settings)[0]+line*height
                    if settings[4]==1:x+=319-width
                    elif settings[4]==2:x+=image.read(0x1ab40+line*2,'<h')[0]
                    signed=lambda v:struct.unpack('<h',struct.pack('<H',v&65535))[0]
                    word(len(text));expected+=text;word(signed(x),signed(y),width)
                metadata=bytes(expected)
                video.reset();image.call(0xb1b5c,limit=5000000);expected+=video.pixels()+video.coverage()
                rows.append(f"{int(program['id'],16)} {function_index} {node['index']} {language} 4294967295\n");cases.append((program['name'],function['name'],node['index'],language,expected));external_count+=int('^' in node['text']['text'])
                layout=(font,settings[4],bool(settings[6]))
                if language=='english' and total and layout not in seen_layouts:
                    seen_layouts.add(layout);first=image.read(0x1ab18,'<H')[0]
                    cpu.mem_write(image.read(0x1ad04,'<I')[0]+7,bytes([1]))
                    for visible in sorted({0,1,max(0,first-1),first,min(total,first+1),total//2,total-1,total}):
                        image.write(0x241b6,'<H',visible);image.write(0x1afd8,'<H',0);image.write(0x1acf8,'<I',0)
                        video.reset();image.call(0xb1b5c,limit=5000000)
                        rows.append(f"{int(program['id'],16)} {function_index} {node['index']} {language} {visible}\n");cases.append((program['name'],function['name'],node['index'],language+' prefix '+str(visible),metadata+video.pixels()+video.coverage()));prefix_cases+=1
    print(program['name'],'native text composed',flush=True)
result=subprocess.run([str(args.build/'text_probe'),str(data_dir)],input=''.join(rows).encode(),capture_output=True)
assert result.returncode==0,result.stderr.decode()
at=0;failures=[]
for program,function,node,language,expected in cases:
    actual=result.stdout[at:at+len(expected)]
    if actual!=expected:failures.append((program,function,node,language,next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None),actual[:20].hex(),expected[:20].hex()))
    at+=len(expected)
assert at==len(result.stdout),(at,len(result.stdout))
assert not failures,(len(failures),failures[:12])
print(len(cases)-prefix_cases,'complete text cases and',prefix_cases,'reveal prefixes agree in prepared lines, coordinates, counts and every VGA pixel/coverage bit;',external_count,'external references across five languages')
