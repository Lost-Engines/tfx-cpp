#!/usr/bin/env python3
"""Compare native presentation input, wait budgets, animation clocks and palette ramps.

Hardware mouse/retrace/palette output and animation pixel decoding are declared
boundaries. Original input, countdown, repeat-pointer and clock arithmetic run;
complete pixel decoding/drawing has separate native comparisons.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--save-fixture',type=Path)
args=parser.parse_args();image=NativeReference(args.data_dir/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0,4096);cpu.mem_map(0x300000,0x40000);rng=random.Random(0xc9fac)
mouse=0;uploads=[];changed=False;block_index=0
image.intercept(0xc733e,'Supply the sampled mouse button byte; the native priority/key/skip logic executes.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,mouse),im.return_from()))
for file,reason in ((0xc62d4,'Display flip is outside countdown arithmetic.'),(0xc9bdc,'Supply a retrace boundary without blocking on a VGA device.'),(0xc7370,'Capture fade arithmetic without clearing physical display pages.'),(0xc734c,'Capture fade arithmetic without resetting a VGA device.')):image.intercept(file,reason,lambda im:im.return_from())
def palette(im):
    sp=im.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0];uploads.append(bytes(im.cpu.mem_read(pointer,768)));im.return_from(4)
image.intercept(0xde454,'Capture each original six-bit DAC upload.',palette)
def decode(im):
    global changed,block_index
    sp=im.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',im.cpu.mem_read(sp+4,4))[0];changed=True;block_index=(pointer+4-0x303000)//8;im.return_from()
image.intercept(0xde8cc,'Record the block selected by the native clock; all compressed blocks are separately compared with native decoding.',decode)
image.intercept(0xdef78,'Pixel-plane delta application is outside this clock comparison and has separate complete-frame checks.',lambda im:im.return_from())
def stop(finished):
    def handler(im):im.cpu.reg_write(r.UC_X86_REG_EAX,int(finished));im.return_from()
    return handler
for file,finished in ((0xb1f65,True),(0xb1f5c,False),(0xb2177,True),(0xb216e,False),(0xb1e27,True),(0xb1e1e,False)):image.intercept(file,'Stop at the native wait termination/input branch, after its exact decrement/hold decision.',stop(finished))
rows=[];expected=[];animation_updates=0

def digest(values):
    result=14695981039346656037
    for value in values:
        for byte in struct.pack('<I',value&0xffffffff):result=((result^byte)*1099511628211)&0xffffffffffffffff
    return result

for case in range(4096):
    key=rng.choice((0,1,16,30,57,255));shift=rng.randrange(2);mouse=rng.randrange(4);caption=rng.randrange(2);reveal=rng.randrange(2);visible=rng.randrange(65536);total=rng.randrange(65536);skipped=rng.randrange(2);quit=rng.randrange(2)
    image.write(0x1b238,'<I',0x300f00);image.write(0x1b23c,'<I',0x301000);image.write(0x1ad04,'<I',0x301200 if caption else 0);cpu.mem_write(0x300f00,bytes([key]));cpu.mem_write(0x301000,bytes(256));cpu.mem_write(0x301000+42,bytes([shift]));cpu.mem_write(0x301207,bytes([reveal]));image.write(0x241b6,'<H',visible);image.write(0x1afde,'<H',total);image.write(0xab35,'<B',skipped);image.write(0xab40,'<B',quit)
    result=image.call(0xb1128)
    values=[result,cpu.mem_read(0x300f00,1)[0],image.read(0xab35,'<B')[0],image.read(0xab40,'<B')[0]]
    rows.append(['K',key,shift,mouse,caption,reveal,visible,total,skipped,quit]);expected.append(digest(values))
for case in range(4096):
    kind=case%3;ticks=rng.choice((-32768,-1,0,1,2,200,32767));caption=rng.randrange(2);reveal=rng.randrange(2);visible=rng.randrange(65536);total=rng.randrange(65536)
    cpu.mem_write(0x301100,bytes(18));cpu.mem_write(0x30110d,bytes([caption]));cpu.mem_write(0x30110e,struct.pack('<I',0x301200));cpu.mem_write(0x301207,bytes([reveal]));image.write(0x241b6,'<H',visible);image.write(0x1afde,'<H',total)
    cpu.reg_write(r.UC_X86_REG_ESI,ticks&0xffffffff if kind==0 else 0x301100);cpu.reg_write(r.UC_X86_REG_EDI,ticks&0xffffffff)
    finished=image.call(0xb2164 if kind==0 else 0xb1f30 if kind==1 else 0xb1e17)
    remaining=cpu.reg_read(r.UC_X86_REG_ESI if kind==0 else r.UC_X86_REG_EDI)
    rows.append(['W',kind,ticks,caption,reveal,visible,total]);expected.append(digest([remaining,finished]))
for case in range(1024):
    frames=rng.choice((2,3,7,20,2000));delay=rng.choice((0,1,2,18,65535));initial=rng.randrange(2**32);now=initial;steps=64
    image.write(0x24084,'<I',0x302000);cpu.mem_write(0x302000,struct.pack('<2H',256,frames));cpu.mem_write(0x303000,struct.pack('<2I',4,0)*frames)
    image.write(0x24078,'<I',0x303008);image.write(0x24080,'<I',0x303008);image.write(0x2408e,'<H',2);image.write(0x2408c,'<H',delay);image.write(0x24070,'<I',initial);image.write(0xad2c,'<I',0x330000);image.write(0x24088,'<I',0x331000)
    row=['A',frames,delay,initial,steps];values=[]
    for step in range(steps):
        elapsed=rng.choice((0,1,2,3,18,55,65535,65536,0x7fffffff,0x80000000,0xffffffff));row.append(elapsed);now=(now+elapsed)&0xffffffff;cpu.mem_write(0x46c,struct.pack('<I',now));changed=False;block_index=0
        result=image.call(0xc9fac)
        values.extend([image.read(0x24070,'<I')[0],image.read(0x2408e,'<H')[0],int(changed),int(result==0),block_index]);animation_updates+=1
    rows.append(row);expected.append(digest(values))
cpu.mem_write(0x300000,bytes(range(64))*12)
for file,stages,inward in ((0xca2f4,40,True),(0xca35c,80,True),(0xca3c0,40,False),(0xca428,80,False)):
    uploads.clear();image.call(file,eax=0x300000,limit=3000000);assert len(uploads)==stages
    for level,palette in zip(range(1,stages+1) if inward else range(stages,0,-1),uploads):rows.append(['F',stages,level]);expected.append(digest(palette))
result=subprocess.run([str(args.build/'presentation_timing_probe')],input=''.join(' '.join(map(str,row))+'\n' for row in rows),capture_output=True,text=True,check=True)
actual=[int(v) for v in result.stdout.split()];assert len(actual)==len(expected)
for i,(a,b) in enumerate(zip(actual,expected)):assert a==b,(i,rows[i][:14],a,b)
if args.save_fixture:
    args.save_fixture.write_text(''.join(' '.join(map(str,row+[value]))+'\n' for i,(row,value) in enumerate(zip(rows,expected)) if row[0]=='F' or i%8==0))
    subprocess.run([str(args.build/'presentation_timing_probe'),str(args.save_fixture)],check=True)
print('4096 native input cases, 4096 scene-wait decisions,',animation_updates,'animation clock/repeat updates and 240 complete DAC uploads agree')
