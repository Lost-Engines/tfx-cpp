"""Original GUS.COM bootstrap and commands hosted on the isolated GF1 core.

Supplies a private DOS process, environment, timers and DMA memory. The actual
driver detects RAM, installs vectors and handles GF1 DMA/wave interrupts.
Execution stops after initialization, before its child program is launched.
No original instruction is patched or driver result substituted.
"""
import ctypes
from pathlib import Path
import struct
from unicorn import UC_HOOK_CODE, UC_HOOK_INSN, UC_HOOK_INTR
from unicorn import x86_const as r
from native_gus_memory import GusMemoryReference


class GusDeviceReference(GusMemoryReference):
    def __init__(self, filename, build=Path('build'), ram_kib=1024):
        super().__init__(filename)
        self.library = ctypes.CDLL(str((build / 'libgf1_reference.so').resolve()))
        self.library.gf1_new.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.library.gf1_new.restype = ctypes.c_void_p
        self.library.gf1_delete.argtypes = [ctypes.c_void_p]
        self.library.gf1_delete.restype = None
        self.library.gf1_read.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
        self.library.gf1_read.restype = ctypes.c_uint
        self.library.gf1_write.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
        self.library.gf1_write.restype = None
        self.library.gf1_dma_count.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.library.gf1_dma_count.restype = None
        self.library.gf1_advance.argtypes = [ctypes.c_void_p, ctypes.c_double]
        self.library.gf1_advance.restype = ctypes.c_uint
        self.library.gf1_sample.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16)]
        self.library.gf1_sample.restype = None
        self.dma_address = self.dma_length = self.dma_page = self.flip = 0
        self.reads = self.pending_irq = self.irq_count = 0
        self.ports, self.events, self.messages = {}, [], []
        self.dta, self.allocator = 0x10080, 0x6000
        self.ready = self.booting = False
        self.exit = self.failure = None

        @ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint)
        def dma(target, length):
            try:
                data = bytes(self.cpu.mem_read(self.dma_page * 65536 + self.dma_address, length))
                ctypes.memmove(target, data, length)
            except Exception as error:
                self.failure = error
                ctypes.memset(target, 0, length)
                self.cpu.emu_stop()

        self.dma_callback = dma
        self.chip = self.library.gf1_new(dma, ram_kib)
        for vector in range(256):
            self.word(vector * 4 + 2, 0xf000)
        self.cpu.mem_write(0xf0000, b'\xcf')
        self.word(0x410, 0x21)
        self.word(0x413, 640)
        self.word(0x10000, 0x20cd)
        self.word(0x10002, 0x9000)
        self.word(0x1002c, 0x800)
        self.cpu.mem_write(0x8000, b'ULTRASND=240,3,3,5,5\0PATH=C:\\TFX\0\0\x01\0C:\\TFX\\GUS.COM\0')
        command = b' 135 TFX'
        self.cpu.mem_write(0x10080, bytes([len(command)]) + command + b'\r')
        for register, value in ((r.UC_X86_REG_CS, self.LOAD_SEGMENT + self.header[11]),
                                (r.UC_X86_REG_IP, self.header[10]),
                                (r.UC_X86_REG_SS, self.LOAD_SEGMENT + self.header[7]),
                                (r.UC_X86_REG_SP, self.header[8]),
                                (r.UC_X86_REG_DS, 0x1000), (r.UC_X86_REG_ES, 0x1000)):
            self.cpu.reg_write(register, value)
        boundary = self.LOAD_SEGMENT * 16 + 0x67c
        self.cpu.hook_add(UC_HOOK_CODE, self._ready, begin=boundary, end=boundary)
        self.cpu.hook_add(UC_HOOK_INTR, self._interrupt)
        self.cpu.hook_add(UC_HOOK_INSN, self._input, None, 1, 0, r.UC_X86_INS_IN)
        self.cpu.hook_add(UC_HOOK_INSN, self._output, None, 1, 0, r.UC_X86_INS_OUT)

    def close(self):
        if self.chip:
            self.library.gf1_delete(self.chip)
            self.chip = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _ready(self, cpu, address, size, unused):
        self.ready = True
        cpu.emu_stop()

    def _text(self, address, end=b'\0'):
        return bytes(self.cpu.mem_read(address, 1024)).split(end)[0].decode('cp437')

    def _interrupt(self, cpu, number, unused):
        get, put = cpu.reg_read, cpu.reg_write
        ax, ds, dx, bx, cx = (get(register) for register in
                              (r.UC_X86_REG_AX, r.UC_X86_REG_DS, r.UC_X86_REG_DX, r.UC_X86_REG_BX, r.UC_X86_REG_CX))
        ah, al = ax >> 8, ax & 255
        if number == 0x10:
            return
        if number == 0x1a:
            put(r.UC_X86_REG_CX, 0);put(r.UC_X86_REG_DX, self.reads // 100);put(r.UC_X86_REG_AX, 0)
            return
        if number == 0x2f:
            put(r.UC_X86_REG_AX, 0)
            return
        if number != 0x21:
            raise RuntimeError(('undeclared Gravis bootstrap interrupt', number, ax))
        put(r.UC_X86_REG_FLAGS, get(r.UC_X86_REG_FLAGS) & ~1)
        if ah == 0x30:
            put(r.UC_X86_REG_AX, 5);put(r.UC_X86_REG_BX, 0);put(r.UC_X86_REG_CX, 0)
        elif ah == 0x35:
            put(r.UC_X86_REG_BX, self.word(al * 4));put(r.UC_X86_REG_ES, self.word(al * 4 + 2))
        elif ah == 0x25:
            self.word(al * 4, dx);self.word(al * 4 + 2, ds)
        elif ah in (0x4a, 0x49):
            pass
        elif ah == 0x48:
            put(r.UC_X86_REG_AX, self.allocator);self.allocator += bx + 1
        elif ah in (0x51, 0x62):
            put(r.UC_X86_REG_BX, 0x1000)
        elif ah == 0x09:
            self.messages.append(self._text(ds * 16 + dx, b'$'))
        elif ah == 0x40:
            self.messages.append(bytes(cpu.mem_read(ds * 16 + dx, cx)).decode('cp437'));put(r.UC_X86_REG_AX, cx)
        elif ah == 0x4c:
            self.exit = al;cpu.emu_stop()
        elif ah == 0x2c:
            put(r.UC_X86_REG_CX, 0);put(r.UC_X86_REG_DX, 0)
        elif ah == 0x2a:
            put(r.UC_X86_REG_CX, 1994);put(r.UC_X86_REG_DX, 0x0901)
        elif ah == 0x44:
            put(r.UC_X86_REG_DX, 0x80 if bx < 5 else 0)
        elif ah == 0x34:
            put(r.UC_X86_REG_ES, 0x9000);put(r.UC_X86_REG_BX, 0)
        elif ah == 0x19:
            put(r.UC_X86_REG_AX, 2)
        elif ah == 0x47:
            cpu.mem_write(ds * 16 + get(r.UC_X86_REG_SI), b'\0')
        elif ah == 0x58:
            put(r.UC_X86_REG_AX, 0)
        elif ah in (0x4e, 0x4f):
            # No wildcard matches are supplied for the literal child command.
            put(r.UC_X86_REG_AX, 18);put(r.UC_X86_REG_FLAGS, get(r.UC_X86_REG_FLAGS) | 1)
        elif ah == 0x1a:
            self.dta = ds * 16 + dx
        elif ah == 0x2f:
            put(r.UC_X86_REG_ES, self.dta // 16);put(r.UC_X86_REG_BX, self.dta % 16)
        elif ah == 0x02:
            self.messages.append(chr(dx & 255))
        else:
            raise RuntimeError(('undeclared Gravis DOS service', hex(ax)))

    def _advance(self, milliseconds):
        raised = self.library.gf1_advance(self.chip, milliseconds)
        if raised:
            self.pending_irq = raised

    def _input(self, cpu, port, size, unused):
        self.reads += 1
        self.word(0x46c, self.reads // 100)
        self._advance(0.01)
        if port in (0x40, 0x42):
            value = (65535 - self.reads) & 255
        elif port == 0x61:
            value = (self.reads & 1) * 0x20
        elif 0x240 <= port <= 0x34f:
            value = self.library.gf1_read(self.chip, port, size)
        else:
            value = self.ports.get(port, 0)
        self.events.append([0, port, size, value])
        return value

    def _output(self, cpu, port, size, value, unused):
        self.events.append([1, port, size, value])
        self.ports[port] = value & 255
        if port == 0x0c:
            self.flip = 0
        if port == 0x82:
            self.dma_page = value & 255
        if port in (6, 7):
            name = 'dma_address' if port == 6 else 'dma_length'
            old = getattr(self, name)
            setattr(self, name, (old & ~(255 << (self.flip * 8))) | ((value & 255) << (self.flip * 8)))
            self.flip ^= 1
            self.library.gf1_dma_count(self.chip, self.dma_length)
        if 0x240 <= port <= 0x34f:
            self.library.gf1_write(self.chip, port, size, value)

    def _inject_irq(self):
        get, put = self.cpu.reg_read, self.cpu.reg_write
        if not self.pending_irq or not get(r.UC_X86_REG_FLAGS) & 0x200:
            return
        vector = self.pending_irq - 1 + 8
        self.pending_irq = 0
        self.irq_count += 1
        sp = (get(r.UC_X86_REG_SP) - 6) & 65535
        self.cpu.mem_write(get(r.UC_X86_REG_SS) * 16 + sp,
                          struct.pack('<3H', get(r.UC_X86_REG_IP), get(r.UC_X86_REG_CS), get(r.UC_X86_REG_FLAGS)))
        put(r.UC_X86_REG_SP, sp);put(r.UC_X86_REG_FLAGS, get(r.UC_X86_REG_FLAGS) & ~0x300)
        put(r.UC_X86_REG_CS, self.word(vector * 4 + 2));put(r.UC_X86_REG_IP, self.word(vector * 4))

    def _run(self, end, budget):
        for _ in range((budget + 511) // 512):
            self._inject_irq()
            pc = self.cpu.reg_read(r.UC_X86_REG_CS) * 16 + self.cpu.reg_read(r.UC_X86_REG_IP)
            if pc == end:
                return
            self.cpu.emu_start(pc, end, count=512)
            if self.failure:
                raise self.failure
            if self.booting and (self.ready or self.exit is not None):
                return
            # A DMA completion must also arrive while the driver spins on RAM.
            self._advance(0.01)
        raise RuntimeError('original Gravis driver exceeded its instruction budget')

    def boot(self):
        self.booting = True
        self._run(0, 100000000)
        self.booting = False
        if not self.ready:
            raise RuntimeError(('Gravis bootstrap did not reach its child-launch boundary', self.exit, self.messages))

    def command(self, command, *arguments):
        self.prepare_command(command, arguments)
        self._run(self.RETURN, 1000000)
        return struct.unpack('<4I', self.cpu.mem_read(self.data + 0xdb4, 16))

    def sample(self):
        result = (ctypes.c_int16 * 2)()
        self.library.gf1_sample(self.chip, result)
        self._advance(1000 / 44100)
        if self.pending_irq:
            self._run(self.RETURN, 1000000)
        return tuple(result)
