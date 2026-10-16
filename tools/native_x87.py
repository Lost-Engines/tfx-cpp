#!/usr/bin/env python3
"""Supply hardware FPATAN where Unicorn otherwise narrows to binary64.

The original surrounding Watcom code still executes. Each replaced instruction
is an explicit capture dependency; x87 register words/tags and TOP are updated
without converting through a Python float. This adapter is verification-only.
"""
import ctypes
from pathlib import Path
import struct
from native_reference import r


def hardware_fpatan(image,build):
    library=ctypes.CDLL(str((Path(build)/'libnative_x87_backend.so').resolve()))
    operation=library.tfx_fpatan
    operation.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ushort]
    operation.restype=None
    def replace(im):
        status=im.cpu.reg_read(r.UC_X86_REG_FPSW);top=(status>>11)&7;destination=(top+1)&7
        x=im.cpu.reg_read(getattr(r,'UC_X86_REG_FP'+str(top)))
        y=im.cpu.reg_read(getattr(r,'UC_X86_REG_FP'+str(destination)))
        xb=ctypes.create_string_buffer(struct.pack('<QH',*x));yb=ctypes.create_string_buffer(struct.pack('<QH',*y));out=ctypes.create_string_buffer(10)
        operation(yb,xb,out,im.cpu.reg_read(r.UC_X86_REG_FPCW))
        value=struct.unpack('<QH',out.raw)
        im.cpu.reg_write(getattr(r,'UC_X86_REG_FP'+str(destination)),value)
        tags=im.cpu.reg_read(r.UC_X86_REG_FPTAG)
        tag=1 if value[0]==0 and value[1]&0x7fff==0 else 0
        tags=(tags|(3<<(top*2)))&~(3<<(destination*2));tags|=tag<<(destination*2)
        im.cpu.reg_write(r.UC_X86_REG_FPTAG,tags)
        im.cpu.reg_write(r.UC_X86_REG_FPSW,(status&~0x3a00)|(destination<<11))
        im.cpu.reg_write(r.UC_X86_REG_EIP,im.cpu.reg_read(r.UC_X86_REG_EIP)+2)
    for file in (0xd2469,0xd248b,0xd2498,0xd24b2):
        image.intercept(file,'Use actual 80-bit host FPATAN; installed Unicorn narrows both operands and result to binary64',replace)
    return library
