"""Capture indexed VGA writes from controlled original 2.05 drawing routines."""
import struct
from unicorn import UC_HOOK_INSN,UC_HOOK_MEM_WRITE
from unicorn import x86_const as r


class VgaCapture:
    def __init__(self,image,aperture=0xe0000):
        self.image=image
        self.aperture=aperture
        cpu=image.cpu;cpu.mem_map(aperture,0x10000)
        for offset,value in ((0x4fb78,0),(0x4fb7a,320),(0x4fb7c,0),(0x4fb7e,200),(0x55907,aperture//16)):cpu.mem_write(image.native(0x70aa4+offset),struct.pack('<H',value))
        for offset,value in ((0x4fb80,0),(0x4fb84,319),(0x4fb88,0),(0x4fb8c,200)):cpu.mem_write(image.native(0x70aa4+offset),struct.pack('<I',value))
        for y in range(200):cpu.mem_write(image.native(0x70aa4+0x5590b+y*2),struct.pack('<H',y*80))
        self.planes=[bytearray(16000) for _ in range(4)]
        self.written=[bytearray(16000) for _ in range(4)]
        self.reset()
        cpu.hook_add(UC_HOOK_INSN,self._out,None,1,0,r.UC_X86_INS_OUT)
        cpu.hook_add(UC_HOOK_MEM_WRITE,self._write)

    def _out(self,cpu,port,size,value,unused):
        if port==0x3c4:
            self.index=value&255
            if size==2 and self.index==2:self.mask=value>>8
        elif port==0x3c5 and self.index==2:self.mask=value&255

    def _write(self,cpu,access,address,size,value,unused):
        if self.aperture<=address and address+size<=self.aperture+16000:
            offset=address-self.aperture
            for plane in range(4):
                if self.mask&(1<<plane):self.planes[plane][offset:offset+size]=value.to_bytes(size,'little');self.written[plane][offset:offset+size]=bytes([255])*size

    def reset(self):
        for plane in self.planes+self.written:plane[:]=bytes(16000)
        self.index=self.mask=0

    def pixels(self):return self._deplane(self.planes)
    def coverage(self):return self._deplane(self.written)

    @staticmethod
    def _deplane(planes):
        result=bytearray(64000)
        for plane in range(4):result[plane::4]=planes[plane]
        return result
