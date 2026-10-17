#!/usr/bin/env python3
"""Compare original complete UV near intersection and saturated projection.

Actual D8739/D8744 and D87E0 execute with supplied signed Q16 camera points,
full unsigned UV words, direction, origin and aperture. A code hook observes
the completed intersection before projection; it replaces no instruction.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--research',type=Path,default=Path('../tfx-reverse'));p.add_argument('--build',type=Path,default=Path('build'));p.add_argument('--record',type=Path);p.add_argument('--cases',type=int,default=8192);a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096);code=lambda off:im.native(0x70aa4+off);observed=[]
def capture(cpu,address,size,user):observed[:]=[struct.unpack('<i',struct.pack('<I',cpu.reg_read(reg)))[0] for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX)]
im.cpu.hook_add(UC_HOOK_CODE,capture,begin=im.native(0xd875a),end=im.native(0xd875a));rng=random.Random(0xd87e0);rows=[]
for case in range(a.cases):
 outside=[rng.randrange(-2147483648,2147483648) for _ in range(2)]+[rng.choice((-32768,-16000,-1000,-1,0,15,16))*65536+rng.randrange(65536)];inside=[rng.randrange(-2147483648,2147483648) for _ in range(2)]+[rng.choice((17,18,100,1000,16000,32767))*65536+rng.randrange(65536)];uv=[rng.randrange(65536) for _ in range(4)];rows.append([case%2,*outside,*inside,*uv])
actual=subprocess.check_output([str((a.build/'texture_near_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines();assert len(actual)==len(rows);fixtures=[]
for case,(row,line) in enumerate(zip(rows,actual)):
 wide=row[0];outside=row[1:4];inside=row[4:7];uv_out=row[7:9];uv_in=row[9:11];forward=case%3!=0;im.call(0xca780)
 if wide:im.call(0xca6fc,stack=(0xffffffff,0xffffffff))
 im.call(0xb94da,stack=(160,100,319,199));im.cpu.mem_write(code(0x6814c),struct.pack('<3i',*outside));im.cpu.mem_write(code(0x6814c+32),struct.pack('<3i',*inside));im.cpu.mem_write(0x300000,bytes(1024));im.cpu.mem_write(code(0x481ac),struct.pack('<4H',*(uv_out+uv_in if forward else uv_in+uv_out)));im.cpu.reg_write(r.UC_X86_REG_EDI,code(0x481ac));im.cpu.reg_write(r.UC_X86_REG_EBP,0x300000);im.cpu.reg_write(r.UC_X86_REG_ESI,0);observed.clear();im.call(0xd8739 if forward else 0xd8744,eax=0,ebx=32,ecx=16,limit=10000)
 want=[*observed,*struct.unpack('<2H',im.cpu.mem_read(0x300380,4)),*struct.unpack('<2h',im.cpu.mem_read(0x300000,4))];assert len(want)==6
 assert list(map(int,line.split()))==want,(case,row,line,want)
 if case<128 or case%97==0:fixtures.append(row+want)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} original textured near intersections agree: both edge directions, full signed camera dwords/depth words, unsigned UV carries, exact-near and fractional depths, wrapped midpoint replay and saturated normal/wide projection.')
