#!/usr/bin/env python3
"""Compare native SSD effect-request placement and in-interpreter delivery order.

The original local quarter turn, origin addition, player-relative handoff and
complete 0xb626c/0x7b0cc helpers execute. Allocation is observed at 0x7b144 and
its final word position is compared; the actual pool has separate comparisons.
A separate authored SSD verifies callbacks observe each preceding custom state.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');rng=random.Random(0xb626c)
quarter=im.read(0xac1c,'<4I');im.cpu.emu_start(im.native(0x7589a),im.native(0x758b8),count=3)
assert im.read(0xabf4,'<3I')==(im.data+0x13424,im.data+0x13430,im.data+0x1343c);im.write(0xac10,'<I',im.native(0x7b0cc));events=[]
def allocation(im):
 point=struct.unpack('<3i',im.cpu.mem_read(im.cpu.reg_read(r.UC_X86_REG_EAX),12));kind=im.cpu.reg_read(r.UC_X86_REG_EDX)
 events.append([*[struct.unpack('<h',struct.pack('<H',v&65535))[0] for v in point],kind]);im.return_from()
im.intercept(0x7b144,'Observe the pool-allocation request and its separately checked final word stores.',allocation)
s=(a.research/'analysis/maps/data.js').read_text();objects=json.loads(s[s.index('=')+1:].strip().removesuffix(';'))['objects'];authored=[arguments for obj in objects.values() for _,op,arguments in obj['programs'] if op==79]
assert len(authored)==782
rows=[];expected=[];fixture=[]
word=lambda n:struct.unpack('<h',struct.pack('<H',n&65535))[0]
for case in range(len(authored)*4+8192):
 if case<len(authored)*4:
  item=authored[case//4];kind=item[3];local=list(map(word,item[:3]));turn=case%4
 else:
  kind=case%10;local=[rng.choice((-32768,-1,0,1,32767,rng.randrange(-32768,32768))) for _ in range(3)];turn=rng.randrange(4)
 origin=[rng.choice((-32768,-1,0,32767,rng.randrange(-32768,32768))) for _ in range(3)]
 reference=[rng.randrange(-2147483648,2147483648) for _ in range(3)];heading=turn*16384;row=[kind,*local,*origin,heading,*reference];rows.append(row)
 im.write(0x20bb0,'<3h',*origin)
 for at,v in zip((0x13424,0x13430,0x1343c),reference):im.write(at,'<i',v)
 im.write(0xac18,'<I',quarter[turn]);events.clear();im.call(0xb626c,eax=local[0]&0xffffffff,edx=local[1]&0xffffffff,ebx=local[2]&0xffffffff,ecx=kind)
 assert len(events)==1;expected.append(events[0])
 if case<64 or (case>=len(authored)*4 and case%47==0):fixture.append(row+events[0])
result=subprocess.check_output([str((a.build/'effects_probe').resolve()),'--place'],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixture)+'\n')
# Independently execute a tiny SSD with state changes bracketing two outputs.
order=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');order.cpu.mem_map(0x300000,0x20000);definition,instance=0x300000,0x310000;raw=bytearray(16);raw[0]=2;raw[8]=3
emit=lambda *v:raw.extend(struct.pack('<'+'H'*len(v),*v))
def entry(index):struct.pack_into('<H',raw,10+index*2,(len(raw)-(10+index*2))//2)
entry(0);emit(11,0,0,0);entry(1);emit(11,0,11,79,1,2,3,3,11,0,22,79,65531,65530,65529,9,11,0,33,0);entry(2);emit(0)
order.cpu.mem_write(definition,bytes(raw));order.write(0x20b98,'<I',definition);order.write(0x20b9c,'<I',instance);order.write(0x20ba0,'<I',order.native(0xb6c84));observed=[]
def output(im):
 observed.extend([struct.unpack('<H',im.cpu.mem_read(instance+16,2))[0],79,*[im.cpu.reg_read(reg)&65535 for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]]);im.return_from()
order.intercept(0xb626c,'Observe request registers and current SSD custom state at the synchronous output boundary.',output)
for index in (0,1):order.call(0xb54dc,eax=definition+10+index*2+struct.unpack_from('<h',raw,10+index*2)[0]*2)
assert struct.unpack('<H',order.cpu.mem_read(instance+16,2))[0]==33
actual=list(map(int,subprocess.check_output([str((a.build/'effects_probe').resolve()),'--request-order']).split()));assert actual==observed,(actual,observed)
print(f'{len(rows)} native placed effect requests agree, covering all 782 authored requests at every quarter turn, all ten kinds, extreme words and independent player references')
print('Complete authored SSD callback-order case agrees: outputs observe intermediate custom states 11/22 before the final state 33')
