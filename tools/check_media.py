#!/usr/bin/env python3
"""Compare external presentation media with native animation decoding and independent extraction.

Every compressed block executes the original x86 decoder. Final planar pixels
and written coverage also compare with the separately maintained research tool.
No captured art, compressed game bytes or original instructions are bundled.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn import x86_const as r

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();sys.path.insert(0,str((args.research/'tools').resolve()))
from decode_media import animation_layout,sprite_layout,deplane,unpack_animation,delta_frame
entries=json.loads((args.research/'analysis/resources/catalog.json').read_text())['entries']
data_dir=args.research/'installs/cd_1994_09/TFX';exe=(data_dir/'TFX.DAT').read_bytes()
cpu=Uc(UC_ARCH_X86,UC_MODE_32);cpu.mem_map(0,0x800000);cpu.mem_write(0xde8cc,exe[0xde8cc:0xdea13])
counts={'bitmap':0,'sprites':0,'animation':0};blocks=0
for entry in entries:
    kind=entry['family']
    if kind not in counts:continue
    raw=(args.research/'extracted/cd_1994_09/resources'/entry['path']).read_bytes();mode={'animation':'A','bitmap':'B','sprites':'S'}[kind]
    result=subprocess.run([str(args.build/'media_probe'),str(data_dir)],input=f"{mode} {int(entry['identifier'],16)}\n".encode(),capture_output=True,check=True).stdout
    expected=bytearray()
    palette=bytes((v*255+31)//63 for v in raw[4:772]) if kind!='sprites' else b''
    if kind=='bitmap':expected+=palette+raw[772:]
    elif kind=='sprites':
        frames=sprite_layout(raw);expected+=struct.pack('<I',len(frames))
        for frame in frames:
            size=frame['width']*frame['height'];expected+=struct.pack('<2I',frame['width'],frame['height'])+deplane(raw[frame['offset']:frame['offset']+size],frame['width'],frame['height'])
    else:
        layout=animation_layout(raw);expected+=struct.pack('<3I',layout['game_frames'],layout['initial_full'],len(layout['frames']))+palette
        planes=bytearray(64000);coverage=bytearray(64000)
        for index,block in enumerate(layout['frames']):
            packed=raw[block['offset']:block['offset']+block['size']];decoded=unpack_animation(packed)
            cpu.mem_write(0x300000,bytes(8)+packed);cpu.mem_write(0x400000,bytes(262144));cpu.mem_write(0x700000,struct.pack('<3I',0x200000,0x300000,0x400000));cpu.reg_write(r.UC_X86_REG_ESP,0x700000);cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
            cpu.emu_start(0xde8cc,0xdea0e,count=5000000)
            assert cpu.reg_read(r.UC_X86_REG_EIP)==0xdea0e,(entry['identifier'],index,'decode budget')
            length=cpu.reg_read(r.UC_X86_REG_EDI)-0x400000
            assert length==len(decoded) and bytes(cpu.mem_read(0x400000,length))==decoded,(entry['identifier'],index,'native decoded block')
            if index==0 and layout['initial_full']:planes[:]=decoded;coverage[:]=bytes([255])*64000
            else:delta_frame(decoded,planes,coverage)
            expected+=deplane(planes)+deplane(coverage);blocks+=1
    assert result==expected,(entry['identifier'],kind,len(result),len(expected),next((i for i,(a,b) in enumerate(zip(result,expected)) if a!=b),None))
    counts[kind]+=1
    if kind=='animation':print(entry['identifier'],len(layout['frames']),'animation blocks agree',flush=True)
print('Native media comparison passed:',counts,blocks,'original-decoder animation blocks; exact composed pixels, coverage and palettes')
