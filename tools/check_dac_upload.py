#!/usr/bin/env python3
"""Compare live RGB expansion with the original VGA palette uploader.

The original differential upload/cached palette loop executes unchanged. A
six-bit VGA DAC models ports 3c8/3c9, including index/channel advancement and
retained entries. RGB display expansion uses the existing six-to-eight-bit rule.
Authored palette files retain their separate strict six-bit validation.
"""
import argparse
from pathlib import Path
import random
import subprocess
from unicorn import UC_HOOK_INSN
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--write-fixture',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');dac=bytearray(768);address=0;writes=0
def out(cpu,port,size,value,unused):
    global address,writes
    if port==0x3c8:address=(value&255)*3
    elif port==0x3c9:
        assert size==1;dac[address]=value&63;address=(address+1)%768;writes+=1
im.cpu.hook_add(UC_HOOK_INSN,out,None,1,0,r.UC_X86_INS_OUT)
rng=random.Random(0xc770c);cases=[[value,(value*7+125)%256,(value*17+90)%256] for value in range(256)]
cases.extend([value,value,value] for value in (0,63,64,90,125,127,128,255));cases.extend([rng.randrange(256) for _ in range(3)] for _ in range(32));cases.extend([cases[-1]]*8)
output=subprocess.check_output([str((a.build/'dac_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases);fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    im.cpu.mem_write(im.data+0xf988,bytes(row)*256);im.call(0xc770c,stack=(im.data+0xf988,),limit=200000)
    expected=[(value*255+31)//63 for value in dac[:3]]
    assert dac==bytes(dac[:3])*256,(index,row)
    assert list(map(int,line.split()))==expected,(index,row,line,expected)
    if index%17==0 or 256<=index<264:fixtures.append([*row,*expected])
if a.write_fixture:a.write_fixture.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'Native differential palette upload and six-bit DAC expansion agree for {len(cases)} updates ({writes} component writes), including HUDCOL and unchanged uploads')
