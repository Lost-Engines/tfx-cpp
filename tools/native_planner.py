"""Bounded original 2D planner with supplied DOS resources and four VGA pages.

The complete original map, widget and text painters execute. Only hardware,
file access, allocation and the optional 3D world setup are supplied here.
No installation is modified and no original instruction runs in the C++ game.
"""
from pathlib import Path
import struct
import sys
from unicorn import x86_const as r
from native_reference import NativeReference
from native_vga import VgaCapture


class PlannerVideo(VgaCapture):
    def __init__(self, image):
        self.pages = [[bytearray(16000) for _ in range(4)] for _ in range(4)]
        super().__init__(image)
        self.image = image
        for field, value in ((0x59a64,0xe000),(0x59a66,0xe400),(0x558ff,0xe800),
                             (0x55901,0xec00),(0x55903,0xe800),(0x55907,0xe800),(0x55909,0xe800)):
            self.set(field, value)

    def get(self, field):
        return struct.unpack('<H', self.image.cpu.mem_read(self.image.native(0x70aa4 + field), 2))[0]

    def set(self, field, value):
        self.image.cpu.mem_write(self.image.native(0x70aa4 + field), struct.pack('<H', value))

    def page(self, selector):
        assert selector in (0xe000,0xe400,0xe800,0xec00), hex(selector)
        return self.pages[(selector - 0xe000) // 0x400]

    def _write(self, cpu, access, address, size, value, unused):
        if 0xe0000 <= address < 0xf0000:
            number, offset = divmod(address - 0xe0000, 0x4000)
            assert offset + size <= 16000, (hex(address), size)
            for plane in range(4):
                if self.mask & (1 << plane):
                    self.pages[number][plane][offset:offset+size] = value.to_bytes(size, 'little')

    def pixels(self):
        return self._deplane(self.page(self.get(0x55907)))

    def backing(self):
        return bytes(self._deplane(self.page(self.get(0x59a64))))

    def reset(self):
        for plane in self.page(self.get(0x55907)):
            plane[:] = bytes(16000)
        self.index = self.mask = 0

    def copy(self, source, target):
        for destination, original in zip(self.page(self.get(target)), self.page(self.get(source))):
            destination[:] = original
        self.index, self.mask = 2, 15


class NativePlanner:
    def __init__(self, directory, research):
        sys.path.insert(0, str(Path(research) / 'did-unpack'))
        from did_unpack import Archive
        self.archive = Archive.read(Path(directory) / 'DID.DAT')
        self.entries = {entry.identifier: entry for entry in self.archive.entries}
        self.image = im = NativeReference(Path(directory) / 'TFX.DAT')
        self.cpu = cpu = im.cpu
        cpu.mem_map(0x400000, 0x400000)
        # Selection -1 still reads the preceding route header in native label
        # highlighting. Supply mapped zeroed guard storage, as the surrounding
        # DOS heap was mapped; no unselected route pointer can match that zero.
        self.heap = 0x401000
        self.video = PlannerVideo(im)
        self.polls = 0
        self.stop_after = None
        self.stopped = False
        self.displayed = bytes(64000)
        self.buttons = 0
        im.write(0x1b238, '<I', 0x7f0000)
        im.write(0x1b23c, '<I', 0x7f0100)
        im.write(0xab36, '<B', 1)
        for address in (0xab004,0xc91a0,0xc90ec,0xb10d0,0xd3820):
            im.intercept(address, 'Supply fresh zeroed allocations within a bounded private heap.', self.allocate)
        for address in (0xab058,0xc91f0,0xd36ef):
            im.intercept(address, 'Retain freed private allocations until this bounded capture ends.', lambda im: im.return_from())
        im.intercept(0x7b494, 'Supply the DOS resource pathname join.', self.filename)
        im.intercept(0xc8bec, 'Supply resource lengths from the independent DID unpacker.', self.length)
        im.intercept(0xc8cf0, 'Supply exact original resource bytes at the DOS filesystem boundary.', self.file)
        im.intercept(0xa8070, 'Supply the decoded planar map cache; native map composition is unchanged.', self.cache)
        for address in (0xc7588,0xc84b1,0xc734c,0xc9bdc,0xc4a14):
            im.intercept(address, 'Supply hardware display, retrace and mouse boundaries for a fixed 2D frame.', lambda im: im.return_from())
        im.intercept(0xc72c0, 'Supply an available mouse.', lambda im: (cpu.reg_write(r.UC_X86_REG_EAX,1),im.return_from()))
        im.intercept(0xa6134, 'Supply a fixed clock without installing the DOS timer interrupt.', lambda im: (im.write(0x16f2c,'<I',0),im.return_from()))
        im.intercept(0xc733e, 'Supply the selected held mouse buttons.', lambda im: (cpu.reg_write(r.UC_X86_REG_EAX,self.buttons),im.return_from()))
        im.intercept(0xc7370, 'Clear the supplied drawing page.', lambda im: (self.video.reset(),im.return_from()))
        for address in (0xb0e4c,):
            im.intercept(address, 'Optional satellite/world 3D setup is outside this 2D planner comparison.', lambda im: im.return_from())
        im.intercept(0xa818c, 'Supply an available mission context for the 2D planner capture.', lambda im: (cpu.reg_write(r.UC_X86_REG_EAX,1),im.return_from()))
        im.intercept(0xd3532, 'Read actual supplied VGA planes for native saved cursor/widget rectangles.', self.capture)
        im.intercept(0xc7326, 'Supply zero relative mouse movement.', self.motion)
        im.intercept(0xd07c6, 'Supply DOS mouse press-count/position; native widget processing continues.', self.mouse_press)
        for address,source,target in ((0xca522,0x55907,0x59a64),(0xca566,0x55907,0x59a66),
                                      (0xca5aa,0x59a64,0x55907),(0xca5ee,0x59a66,0x55907)):
            im.intercept(address, 'Copy supplied VGA planes between native drawing/backing pages.',
                         lambda im,source=source,target=target: (self.video.copy(source,target),im.return_from()))
        im.intercept(0xc62d4, 'Capture the visible drawing page and perform the native page selection.', self.flip)
        im.intercept(0xb0eb0, 'Report native fatal diagnostics instead of entering DOS exit.', self.fatal)

    def text(self, pointer):
        return bytes(self.cpu.mem_read(pointer,120)).split(bytes(1))[0].decode('cp437')

    def read(self, name):
        name = name.replace('\\','/').lstrip('/')
        identifier = self.archive.hash_name(name)
        if identifier not in self.entries:
            raise ValueError('Missing native resource: ' + name)
        return self.archive.unpack(self.entries[identifier])

    def allocate(self, im):
        size = self.cpu.reg_read(r.UC_X86_REG_EAX)
        result = self.heap
        self.heap += (size + 15) & ~15
        assert self.heap < 0x780000
        if size: self.cpu.mem_write(result, bytes(size))
        self.cpu.reg_write(r.UC_X86_REG_EAX,result)
        im.return_from()

    def filename(self, im):
        name = ''.join(self.text(self.cpu.reg_read(register)) for register in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX))
        self.cpu.mem_write(self.cpu.reg_read(r.UC_X86_REG_EAX),name.encode('cp437') + bytes(1))
        im.return_from()

    def length(self, im):
        name=self.text(self.cpu.reg_read(r.UC_X86_REG_EAX)).replace('\\','/').lstrip('/')
        size=len(self.read(name)) if self.archive.hash_name(name) in self.entries else 0
        self.cpu.reg_write(r.UC_X86_REG_EAX,size)
        im.return_from()

    def file(self, im):
        data = self.read(self.text(self.cpu.reg_read(r.UC_X86_REG_EAX)))
        self.cpu.mem_write(self.cpu.reg_read(r.UC_X86_REG_EDX),data)
        self.cpu.reg_write(r.UC_X86_REG_EAX,len(data))
        im.return_from()

    def cache(self, im):
        out = self.cpu.reg_read(r.UC_X86_REG_EAX)
        raw = self.read('iff/raw/' + self.text(out))
        assert len(raw) == 64772
        flat = b''.join(raw[772+y*320:772+y*320+200] for y in range(200))
        self.cpu.mem_write(out+15,raw[4:772] + b''.join(flat[plane::4] for plane in range(4)))
        im.return_from()

    def capture(self, im):
        x,y,width,height,out = struct.unpack('<5I',self.cpu.mem_read(self.cpu.reg_read(r.UC_X86_REG_ESP)+4,20))
        assert x+width<=320 and y+height<=200,(x,y,width,height)
        pixels = self.video.pixels()
        self.cpu.mem_write(out,bytes(pixels[(y+row)*320+x+column] for phase in range(4) for row in range(height) for column in range(phase,width,4)))
        im.return_from()

    def motion(self, im):
        for offset in (4,8):
            pointer, = struct.unpack('<I',self.cpu.mem_read(self.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))
            self.cpu.mem_write(pointer,bytes(2))
        im.return_from()

    def mouse_press(self, im):
        self.polls += 1
        for register,value in ((r.UC_X86_REG_EAX,self.buttons),(r.UC_X86_REG_EBX,0),(r.UC_X86_REG_ECX,200),(r.UC_X86_REG_EDX,100)):
            self.cpu.reg_write(register,value)
        self.cpu.reg_write(r.UC_X86_REG_EIP,im.native(0xd07c8))
        if self.stop_after and self.polls >= self.stop_after:
            self.stopped = True
            self.cpu.emu_stop()

    def flip(self, im):
        self.displayed = bytes(self.video.pixels())
        ordinal = im.read(0xaca4,'<B')[0] ^ 1
        im.write(0xaca4,'<B',ordinal)
        selector = self.video.get(0x558ff + ordinal*2)
        self.video.set(0x55907,selector)
        self.video.set(0x55909,selector)
        im.return_from()

    def fatal(self, im):
        pointer, = struct.unpack('<I',self.cpu.mem_read(self.cpu.reg_read(r.UC_X86_REG_ESP)+4,4))
        raise RuntimeError('Original planner fatal: ' + self.text(pointer))

    def initialise(self, name, modal=False):
        self.cpu.mem_write(0x7f1000,name.encode('ascii') + bytes(1))
        self.polls = 0
        self.stop_after = 8 if modal else None
        self.stopped = False
        try:
            self.image.call(0xaed28 if modal else 0xae9d8,eax=0x7f1000,
                            edx=self.image.data+0x48c4,ebx=1,limit=30000000)
        except RuntimeError:
            if not self.stopped: raise

    def map(self, layer):
        self.image.call(0xabd64,eax=layer,limit=10000000)
        return self.video.backing() + bytes(self.cpu.mem_read(self.image.data+0x20ce0,768))
