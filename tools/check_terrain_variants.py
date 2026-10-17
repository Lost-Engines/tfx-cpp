#!/usr/bin/env python3
"""Compare complete original 40,000-cell random-variant initialization.

B0708's traversal, RNG reset/step, modulo, definition-name indexing and handle
writes execute. Supply decoded grid/table resources and observe SSD creation;
external SSD allocation/cache release are the only declared boundaries.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();directory=a.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(a.research/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={entry.identifier:entry for entry in archive.entries}
def read(name):return archive.unpack(entries[archive.hash_name(name)])
source=(a.research/'analysis/maps/data.js').read_text();world=json.loads(source[source.index('=')+1:].strip().removesuffix(';'))
selections=[(row['name'],row['name']) for row in world['environments'] if row['config'] and not row['undefined_tile_indices'] and row['name']!='columbia']
selections += [('yugoslav','yugos_n'),('columbia','colum_d'),('somalia','somal_st'),('libya','libya_tw'),('seaworld','seaclear')]
actual=subprocess.check_output([str((a.build/'tfx_probe').resolve()),'environment_variants',str(directory)],input=('\n'.join(' '.join(row) for row in selections)+'\n').encode()).splitlines()
assert len(actual)==len(selections)
im=NativeReference(directory/'TFX.DAT');im.cpu.mem_map(0x400000,0x100000)
im.write(0xaac6,'<B',0);im.write(0xaacc,'<H',42)
im.write(0x18f44,'<I',0x410000);im.write(0x18f4c,'<I',0x400000)
im.write(0x18f50,'<I',0x480000);im.write(0x18f40,'<I',0x490000)
im.intercept(0xc85a0,'Resolve the supplied seventeen-byte definition-name records at diagnostic handle 42.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,0x410000),current.return_from()))
im.intercept(0xb4cc4,'The diagnostic host owns SSD/cache allocation; retain observed instances until the bounded capture ends.',lambda current:current.return_from())
selected=[]
def instantiate(current):
    pointer=current.cpu.reg_read(r.UC_X86_REG_EAX)
    name=bytes(current.cpu.mem_read(pointer,17)).split(b'\0')[0]
    rotation=current.cpu.reg_read(r.UC_X86_REG_EDX)&255
    assert rotation<4
    selected.append(name.lower()+b'\0'+struct.pack('<H',rotation<<14))
    current.cpu.reg_write(r.UC_X86_REG_EAX,len(selected));current.return_from()
im.intercept(0xb4da8,'Observe selected SSD name/quarter-turn and return a distinct diagnostic handle; no drawing or SSD initializer runs in this selection test.',instantiate)
for (grid,lighting),line in zip(selections,actual):
    table=read('lev/'+grid+'.dat');count=struct.unpack_from('<H',table)[0];at=2;runtime=bytearray(struct.pack('<H',count));names=bytearray()
    for index in range(count):
        rotation,variants=struct.unpack_from('<2H',table,at);at+=4
        runtime+=struct.pack('<3H',len(names)//17,variants,rotation)
        for _ in range(variants):
            end=table.index(b'\0',at);name=table[at:end];at=end+1
            assert len(name)<17
            names+=name+bytes(17-len(name))
    assert at==len(table) and len(runtime)<0x10000 and len(names)<0x70000
    im.cpu.mem_write(0x400000,bytes(runtime));im.cpu.mem_write(0x410000,bytes(names));im.write(0x18e5c,'<i',count)
    im.cpu.mem_write(0x480000,read('lev/'+grid+'.lev'));im.cpu.mem_write(0x490000,read('lev/'+grid+'.le2'))
    selected.clear();im.call(0xb0708,limit=10000000)
    low=bytes(im.cpu.mem_read(0x480000,40000));high=bytes(im.cpu.mem_read(0x490000,40000));digest=14695981039346656037
    for z in range(200):
        for x in range(200):
            at=x*200+199-z;handle=low[at]|high[at]<<8
            for byte in selected[handle-1]:digest=((digest^byte)*1099511628211)&0xffffffffffffffff
    random=struct.unpack('<2H',im.cpu.mem_read(im.native(0xc9894),4))
    expected=[digest,*random]
    assert json.loads(line)==expected,(grid,json.loads(line),expected)
print(f'{len(selections)*40000} original cell variants/rotations and final RNG states agree across {len(selections)} grid/environment combinations')
