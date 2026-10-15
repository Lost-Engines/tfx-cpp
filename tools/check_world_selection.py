#!/usr/bin/env python3
"""Execute original mission world/type handlers and terrain filename construction."""
import argparse
from pathlib import Path
import struct
import sys
from unicorn import UC_HOOK_CODE
from unicorn import x86_const as r

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,required=True)
args=parser.parse_args()
sys.path.insert(0,str(args.research.resolve()/'tools'))
from check_development import image,return_from,text

cases=[('yugoslavia','yugos_n'),('columbia','colum_d'),('somalia','somal_st'),('libya','libya_tw'),('seaworld','seastorm')]
for world,environment in cases:
    cpu,data,native,call=image()
    token=world
    def hook(uc,address,size,unused):
        if address==native(0x79284):
            uc.mem_write(data+0x11a08,token.encode()+b'\0')
            return_from(uc)
        elif address==native(0xc71b4):
            uc.mem_write(uc.reg_read(r.UC_X86_REG_EAX),b'\0')
            return_from(uc)
        # World setup and memory allocation are outside this name-selection capture.
        elif address in [native(0xb02c0),native(0xaffa4),native(0xb08cc)]:
            return_from(uc)
        elif address==native(0xc90ec):
            uc.reg_write(r.UC_X86_REG_EAX,0x300000)
            return_from(uc)
        elif address==native(0xb0604):
            uc.emu_stop()
    cpu.hook_add(UC_HOOK_CODE,hook)
    call(0x79878)
    assert text(cpu,data+0x11974)==world
    token=environment
    call(0x799b8)
    assert text(cpu,data+0x11960)==environment
    # Same stack-relative pathname builder used immediately before mission initialisation.
    cpu.reg_write(r.UC_X86_REG_EBP,0x380100)
    cpu.reg_write(r.UC_X86_REG_ESP,0x380000)
    cpu.emu_start(native(0x7280f),native(0x72831),count=10000)
    assert cpu.reg_read(r.UC_X86_REG_EIP)==native(0x72831)
    path=text(cpu,0x380100-0x68)
    assert path=='\\lev\\'+world,path
    # Run the world's own DOS path split/rebuild, stopping before resource loading.
    cpu.mem_write(0x330000,path.encode()+b'\0')
    cpu.mem_write(0x380000,struct.pack('<I',0x200000))
    cpu.reg_write(r.UC_X86_REG_ESP,0x380000)
    cpu.reg_write(r.UC_X86_REG_EAX,0x330000)
    cpu.emu_start(native(0xb0a18),0x200000,count=10000)
    assert cpu.reg_read(r.UC_X86_REG_EIP)==native(0xb0604)
    stem=text(cpu,data+0x18ee4)
    assert stem=='\\lev\\'+world[:8],(world,stem)
    # Common extension builder used by DAT, LEV and LE2 resource loads.
    filenames=[]
    for extension in ['dat','lev','le2']:
        cpu.mem_write(0x330100,extension.encode()+b'\0')
        call(0xb0284,0x330100)
        filenames.append(text(cpu,data+0x18f54))
    assert filenames==[stem+'.'+suffix for suffix in ['dat','lev','le2']],filenames
    print({'mission_world':world,'lighting_type':environment,'native_geometry':filenames})
print('Native world/type separation and DOS filename truncation passed')
