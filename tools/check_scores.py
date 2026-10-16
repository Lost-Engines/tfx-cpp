#!/usr/bin/env python3
"""Compare high-score defaults, encoding/checksums and ranking with original execution.

All score bytes and parser strings live in supplied memory. No file is opened or
written by the original; its real initialiser, cipher and insertion code execute.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x10000);rng=random.Random(0xa69b0)
rows=[];expected=[]
image.call(0xa6944)
defaults=bytes(cpu.mem_read(image.data+0x16f74,670));rows.append('defaults\n');expected.append(defaults.hex())
def normalise(raw):
    output=bytearray(raw)
    for i in range(10):
        for at in (i*67,i*67+21,i*67+42):
            end=output.index(0,at,at+21);output[end:at+21]=bytes(at+21-end)
    return bytes(output)
def record(first,last,call,score):return b''.join(name.encode().ljust(21,bytes(1)) for name in (first,last,call))+struct.pack('<i',score)
def table(case):
    if case==0:return defaults
    values=sorted((rng.randrange(-2**31,2**31) for _ in range(10)),reverse=True)
    return b''.join(record('ACE'+str(i),'PILOT'+str(case),rng.choice(('', 'INFERNO','A'*20)),score) for i,score in enumerate(values))
for case in range(512):
    raw=table(case);cpu.mem_write(image.data+0x16f74,raw)
    checksum=image.call(0xa69b0);encoded=bytes(cpu.mem_read(image.data+0x16f74,670))+struct.pack('<I',checksum)
    rows.append('encode '+raw.hex()+'\n');expected.append(encoded.hex())
    assert image.call(0xa6a10)==checksum and bytes(cpu.mem_read(image.data+0x16f74,670))==raw
    rows.append('decode '+encoded.hex()+'\n');expected.append(raw.hex())
    corrupt=bytearray(encoded);corrupt[case%len(corrupt)]^=1
    rows.append('decode '+corrupt.hex()+'\n');expected.append('invalid')
image.write(0x1afee,'<H',3)
for i,name in enumerate(('firstname','pilotname','callsign')):
    image.write(0x1ad44+i,'<B',1);cpu.mem_write(image.data+0x1ad62+i*21,name.encode()+bytes(1));image.write(0x1a400+i*4,'<I',0x300000+i*32)
for case in range(1024):
    raw=table(case);values=[struct.unpack_from('<i',raw,i*67+63)[0] for i in range(10)]
    score=rng.choice(values+[2**31-1,-2**31,0,values[0]+1 if values[0]<2**31-1 else 0]);names=('TEST','PILOT','ACE')
    cpu.mem_write(image.data+0x16f74,raw);image.write(0x16f70,'<i',score);image.write(0x17212,'<H',65535)
    for i,name in enumerate(names):cpu.mem_write(0x300000+i*32,name.encode()+bytes(1))
    image.call(0xa6b6c);slot=image.read(0x17212,'<h')[0];actual=normalise(bytes(cpu.mem_read(image.data+0x16f74,670)))
    rows.append('insert '+raw.hex()+' '+str(score)+' '+' '.join(json.dumps(s) for s in names)+'\n');expected.append(str(slot)+' '+actual.hex())
result=subprocess.run([str(args.build/'score_probe'),str(args.data_dir/'TFX.DAT')],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
actual=result.stdout.splitlines();assert len(actual)==len(expected)
for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,a[:100],b[:100])
print('Native default roster, 512 complete cipher/checksum roundtrips, 512 corrupted files and 1024 signed score insertions agree; new string padding is zeroed')
