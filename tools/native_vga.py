"""Capture indexed VGA writes from controlled original 2.05 drawing routines."""
import struct
from unicorn import UC_HOOK_INSN,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
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
        cpu.hook_add(UC_HOOK_MEM_READ,self._read)
        cpu.hook_add(UC_HOOK_MEM_WRITE,self._write)

    def _out(self,cpu,port,size,value,unused):
        if port==0x3c4:
            self.index=value&255
            if size==2 and self.index==2:self.mask=value>>8
        elif port==0x3c5 and self.index==2:self.mask=value&255
        elif port==0x3ce:
            self.gc_index=value&255
            if size==2:self._graphics(self.gc_index,value>>8)
        elif port==0x3cf:self._graphics(self.gc_index,value&255)

    def _graphics(self,index,value):
        if index==3:self.rotate=value&7;self.logic=value&24
        elif index==4:self.read_plane=value&3
        elif index==5:self.write_mode=value&3
        elif index==8:self.bit_mask=value&255

    def _read(self,cpu,access,address,size,value,unused):
        offset=address-self.aperture
        if 0<=offset and offset+size<=16000:
            self.latches=[plane[offset:offset+size] for plane in self.planes]
            cpu.mem_write(address,bytes(self.latches[self.read_plane]))

    def _write(self,cpu,access,address,size,value,unused):
        if self.aperture<=address and address+size<=self.aperture+16000:
            offset=address-self.aperture
            if self.write_mode:raise AssertionError(f'Unmodelled VGA write mode {self.write_mode}')
            raw=value.to_bytes(size,'little')
            for plane in range(4):
                if not self.mask&(1<<plane):continue
                for at,byte in enumerate(raw):
                    old=self.latches[plane][at] if at<len(self.latches[plane]) else 0
                    byte=((byte>>self.rotate)|(byte<<(8-self.rotate)))&255
                    if self.logic==8:byte&=old
                    elif self.logic==16:byte|=old
                    elif self.logic==24:byte^=old
                    self.planes[plane][offset+at]=(byte&self.bit_mask)|(old&~self.bit_mask&255)
                    self.written[plane][offset+at]=255

    def reset(self,colour=0):
        for plane in self.planes:plane[:]=bytes([colour])*16000
        for plane in self.written:plane[:]=bytes(16000)
        self.image.cpu.mem_write(self.aperture,bytes([colour])*16000)
        self.latches=[bytes(8) for _ in range(4)]
        self.index=self.mask=self.gc_index=0
        self.logic=self.rotate=self.write_mode=self.read_plane=0
        self.bit_mask=255

    def pixels(self):return self._deplane(self.planes)
    def coverage(self):return self._deplane(self.written)

    @staticmethod
    def _deplane(planes):
        result=bytearray(64000)
        for plane in range(4):result[plane::4]=planes[plane]
        return result
