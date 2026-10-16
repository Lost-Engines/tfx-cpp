#!/usr/bin/env python3
"""Execute original pilot name editing with supplied key scans; graphics are external."""
import argparse
import json
from pathlib import Path
import random
import shlex
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x10000);rng=random.Random(0xa1ee0)
image.write(0x1afee,'<H',1);image.write(0x1ad44,'<B',1);cpu.mem_write(image.data+0x1ad62,b'pilotname\0');image.write(0x1a400,'<I',0x302000);image.write(0x1b238,'<I',0x300300);image.write(0x1b23c,'<I',0x301000);cpu.mem_write(0x300100,b'pilotname\0')
for file in (0xca5aa,0xc62d4,0xc6348,0xd2dd8):image.intercept(file,'Drawing/presentation output is outside the name editor state machine.',lambda im:im.return_from())
image.intercept(0xc98d8,'Name field rectangle is a supplied drawing boundary.',lambda im:im.return_from(20))
image.intercept(0xd2d94,'Font width only selects the displayed x coordinate; exact glyph/layout checks are separate.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0),im.return_from()))
keys=[];key_index=0

def key(im):
    global key_index
    assert key_index<len(keys),'original name editor consumed all supplied keys without returning'
    cpu.mem_write(0x300300,bytes([keys[key_index]]));key_index+=1
image.intercept(0xa1f4d,'Supply the next original keyboard make code after the editor clears its input latch.',key)
rows=[];expected=[]
cases=[[scan,28] for scan in range(128)]+[[30]*20+[14]*3+[31,32,28],[30,31,1],[14,14,28]]
cases.extend([rng.randrange(128) for _ in range(rng.randrange(1,48))]+[28] for _ in range(1024))
for index,keys in enumerate(cases):
    fallback=('DIRK','LOOSE CANNON','INFERNO','')[index%4];control=index%2;key_index=0;cpu.mem_write(0x300200,fallback.encode()+bytes(1));cpu.mem_write(0x302000,bytes(32));cpu.mem_write(0x301000,bytes(128));cpu.mem_write(0x30101d,bytes([control]))
    qualified=image.call(0xa1ee0,eax=0x300100,edx=0x300200,ebx=120,ecx=80,limit=1000000)&65535
    value=bytes(cpu.mem_read(0x302000,21)).split(bytes(1))[0].decode()
    rows.append(json.dumps(fallback)+' '+str(control)+' '+str(len(keys))+' '+' '.join(map(str,keys))+'\n');expected.append((value,bool(qualified)))
result=subprocess.run([str(args.build/'name_probe'),str(args.data_dir/'TFX.DAT')],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
actual=[(fields[0],bool(int(fields[1]))) for line in result.stdout.splitlines() if (fields:=shlex.split(line))];assert len(actual)==len(expected)
for index,(a,b) in enumerate(zip(actual,expected)):assert a==b,(index,a,b,rows[index])
print(len(cases),'complete native pilot-name edits agree, including all make codes, 11-character limit, defaults, Escape, Backspace and Control qualification')
