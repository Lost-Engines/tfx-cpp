#!/usr/bin/env python3
"""Compare the original high-score screen's complete growth and pulsing VGA frames.

Decoded background input, retraces/display pages, saved palette and mouse are
explicit boundaries; native list formatting, clip setup and font drawing run.
"""
import argparse
from pathlib import Path
import subprocess
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';image=NativeReference(directory/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x10000);video=VgaCapture(image)
sys.path.insert(0,str(args.research/'did-unpack'))
from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');identifier=archive.hash_name('iff/raw/hiscore.lbm');entry=next(entry for entry in archive.entries if entry.identifier==identifier);background=archive.unpack(entry)[772:]
image.write(0x1b238,'<I',0x300000);frames=[];wanted=0
for offset in (0xc6348,0xca5aa,0xca2f4,0xca3c0):image.intercept(offset,'Display/page or saved palette boundary; no high-score layout is replaced.',lambda im:im.return_from())
def backdrop(im):
    for plane in range(4):video.planes[plane][:]=background[plane::4]
    im.return_from()
image.intercept(0xc6f64,'Supply the independently decoded original background.',backdrop)
def flip(im):
    frames.append(bytes(video.pixels()))
    if len(frames)>=wanted+1:cpu.mem_write(0x300000,bytes([1]))
    im.return_from()
image.intercept(0xc62d4,'Capture each complete native display flip; supply exit after the requested frames.',flip)
image.intercept(0xc733e,'Supply a mouse exit after the requested display flips.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,int(len(frames)>=wanted+1)),im.return_from()))
count=0
for slot in (-1,0,4,9):
    image.call(0xa6944);raw=bytes(cpu.mem_read(image.data+0x16f74,670));image.write(0x17212,'<h',slot);cpu.mem_write(0x300000,bytes(1));video.reset();frames=[];wanted=46 if slot<0 else 76
    image.call(0xa6c3c,limit=20000000)
    expected=b''.join(frames[1:]);assert len(expected)==wanted*64000,(slot,len(frames),wanted)
    result=subprocess.run([str(args.build/'score_probe'),str(directory),'--frames',str(slot),str(wanted)],input=(raw.hex()+'\n').encode(),capture_output=True);assert result.returncode==0,result.stderr
    actual=result.stdout;assert len(actual)==len(expected),(len(actual),len(expected))
    differences=[i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b]
    if differences:
        first=differences[0];frame=first//64000;offset=first%64000
        raise AssertionError((slot,'differing pixels',len(differences),'first frame/x/y',frame,offset%320,offset//320,'C++/native',actual[first],expected[first]))
    count+=wanted
print(count,'complete native high-score frames agree, including expanding clipping, formatting, font pixels, shadow and thirty-step selected-row pulses')
