#!/usr/bin/env python3
"""Compare planner documents with the original complete text/waypoint loader.

A bounded zero-initialised allocator replaces only heap allocation. The native
line reader, scanf, path construction and command constructors execute. Command
semantics and planner interaction are separate consumers of these records.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';image=NativeReference(directory/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x400000,0x200000);heap=0x420000
image.write(0xa7c8,'<I',0x404000)
for field,pointer in ((0x18080,0x408000),(0x18084,0x409000),(0x18088,0x40a000)):image.write(field,'<I',pointer)
def allocate(im):
    global heap
    size=im.cpu.reg_read(r.UC_X86_REG_EAX);result=heap;heap+=(size+15)&~15
    assert heap<0x4f0000,'native parser exhausted supplied storage'
    im.cpu.mem_write(result,bytes(size));im.cpu.reg_write(r.UC_X86_REG_EAX,result);im.return_from()
image.intercept(0xab004,'Supply bounded, fresh allocations; original waypoint/command construction is unchanged.',allocate)
entries=[entry for entry in json.loads((args.research/'analysis/resources/catalog.json').read_text())['entries'] if entry['family']=='waypoints_text'];rows=[];expected=[];points=0;rejected=[]
for entry in entries:
    source=(args.research/'extracted/cd_1994_09/resources'/entry['path']).read_bytes();heap=0x420000;cpu.mem_write(0x404000,bytes(4900));cpu.mem_write(0x500000,source);image.call(0xa48d8)
    try:image.call(0xa7dc0,eax=0x500000,edx=len(source),ebx=1,limit=10000000)
    except RuntimeError as error:
        # Retained malformed legacy sources can feed a WP line to the command dispatcher,
        # which returns null and is immediately written through by native 0xa7d04.
        if cpu.reg_read(r.UC_X86_REG_EIP)!=image.native(0xa7d04):raise
        rejected.append(entry['path']);expected.append('invalid');rows.append(str(int(entry['identifier'],16))+'\n');continue
    text=source.decode('cp437').replace('\r','').splitlines();count=int(text[6].split()[0])
    if count and text[7].startswith('WP'):
        rejected.append(entry['path']);expected.append('invalid');rows.append(str(int(entry['identifier'],16))+'\n');continue
    fields=[str(int(text[0].split()[0]))+' '+' '.join(str(v) for v in image.read(0x16ebc,'<16H'))+' ']
    def string(pointer):return bytes(cpu.mem_read(pointer,100)).split(bytes(1))[0].hex()
    fields+=list(map(string,(0x408000,image.data+0x180b9,0x409000,image.data+0x180aa,0x40a000)))+[str(count)]
    for index in range(count):
        header=0x404000+index*49;pointer=struct.unpack('<I',cpu.mem_read(header,4))[0];fields.append(string(header+8));route=[]
        while pointer:
            values=struct.unpack('<3h',cpu.mem_read(pointer+8,6));route.append(','.join(map(str,values))+';');pointer=struct.unpack('<I',cpu.mem_read(pointer,4))[0];assert len(route)<4096
        points+=len(route);fields.append(''.join(route))
    left=image.read(0x17260,'<I')[0];fields.extend((source[len(source)-left:].hex(),''));expected.append('|'.join(fields));rows.append(str(int(entry['identifier'],16))+'\n')
result=subprocess.run([str(args.build/'planning_probe'),str(directory)],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
actual=result.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
for entry,a,b in zip(entries,actual,expected):assert a==b,(entry['path'],next(((i,x,y) for i,(x,y) in enumerate(zip(a.split('|'),b.split('|'))) if x!=y),None))
programs=json.loads((args.research/'analysis/presentations/programs.json').read_text())
retail=next(program for program in programs if program['name']=='tfx')
planned={'waytxt/'+node['resource']+'.way' for function in retail['functions'] for node in function['nodes'] if node['kind']=='waypoint_planner'}
assert len(planned)==30 and not (planned & set(rejected))
sys.path.insert(0,str(args.research/'did-unpack'))
from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT')
identifiers={archive.hash_name(name) for name in planned}
valid={int(entry['identifier'],16) for entry in entries if entry['path'] not in rejected}
assert identifiers <= valid,'a retail planner source is missing from the comparison' 
print(len(entries)-len(rejected),'native planner loads agree in exposed fields:',points,'waypoints, metadata, partial header defaults, route names and exact remaining briefing bytes; rejected legacy sources:',rejected)
