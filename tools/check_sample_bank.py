#!/usr/bin/env python3
"""Check every native sample definition/resource and original SB clock programming.

The descriptor and effect words are read from the relocated original. Resource
bytes are independently decompressed with the research archive reader. Complete
0xdd414 executes for clock tests; only device IN/OUT are external.
"""
import argparse
from pathlib import Path
import shlex
import struct
import subprocess
import sys
from unicorn import UC_HOOK_INSN
from unicorn import x86_const as r
from native_reference import NativeReference

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();directory=a.research/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(a.research/'did-unpack'))
from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={e.identifier:e for e in archive.entries}
im=NativeReference(directory/'TFX.DAT')
output=subprocess.check_output([str((a.build/'sample_bank_probe').resolve()),str(directory)]).decode().splitlines()
missing=[];resolved=0
for index,line in enumerate(output):
 fields=shlex.split(line);actual=[int(fields[0]),fields[1]]+list(map(int,fields[2:]))
 at=0x9860+index*26;pointer=im.read(at,'<I')[0];assert pointer
 name=bytes(im.cpu.mem_read(pointer,9)).split(b'\0')[0].decode()
 rate,delay,effect=im.read(at+4,'<HhI');parameters=list(struct.unpack('<3h',im.cpu.mem_read(effect,6))) if effect else [0]*3
 identifier=archive.hash_name(f'samples/{name}.sam');available=bool(name) and identifier in entries
 pcm=archive.unpack(entries[identifier]) if available else b''
 checksum=14695981039346656037
 for byte in pcm:checksum=((checksum^byte)*1099511628211)&0xffffffffffffffff
 expected=[index,name,rate,delay]+parameters+[int(available),len(pcm),checksum]
 assert actual==expected,(index,actual,expected)
 if available:resolved+=1
 elif name:missing.append(name)
assert im.read(0x9860+len(output)*26,'<I')[0]==0
assert len(output)==106 and resolved==103 and missing==[],(len(output),resolved,missing)
im.cpu.mem_map(0x300000,4096);im.write(0x25cc8,'<I',0x300000)
writes=[]
im.cpu.hook_add(UC_HOOK_INSN,lambda cpu,port,size,user:0,None,1,0,r.UC_X86_INS_IN)
im.cpu.hook_add(UC_HOOK_INSN,lambda cpu,port,size,value,user:writes.append(value&255),None,1,0,r.UC_X86_INS_OUT)
rates=sorted(set(range(1,65536,17))|{1,3906,3907,6500,7046,7500,8363,9000,11025,22050,44100,48000,65535})
actual=list(map(int,subprocess.check_output([str((a.build/'sample_bank_probe').resolve()),'--rates'],input=('\n'.join(map(str,rates))+'\n').encode()).split()))
for rate,period in zip(rates,actual):
 writes.clear();im.cpu.mem_write(0x300004,struct.pack('<H',65535));im.call(0xdd414,eax=rate)
 assert writes and writes[0]==0x40 and len(writes)==2,(rate,writes)
 expected=256-writes[1];assert period==expected,(rate,period,expected)
print(f'{len(output)} native sample slots, {resolved} complete PCM resources, empty/unavailable entries, all effect words and {len(rates)} original DSP time constants agree; all named samples resolve')
