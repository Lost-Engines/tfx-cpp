"""Relocated original GUS.COM with bounded software-interrupt commands.

Allocation-only checks supply detected RAM explicitly and do not boot DOS.
The device reference subclass boots the original driver on GF1 hardware.
Both execute the unchanged real-mode software-interrupt entry and dispatcher.
"""
import hashlib
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16
from unicorn import x86_const as r


class GusMemoryReference:
    SHA256 = 'dc8abddfd7deee6e25f3e625708684209a408420c74e3ae1c403e0d4d47a5925'
    LOAD_SEGMENT = 0x1010
    RETURN = 0xf0100

    def __init__(self, filename):
        raw = Path(filename).read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.SHA256:
            raise ValueError('Gravis allocation reference requires the September 1994 GUS.COM')
        header = self.header = struct.unpack('<14H', raw[:28])
        assert header[0] == 0x5a4d
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_16)
        self.cpu.mem_map(0, 0x200000)
        load = self.LOAD_SEGMENT * 16
        self.cpu.mem_write(load, raw[header[4] * 16:])
        for index in range(header[3]):
            offset, segment = struct.unpack_from('<2H', raw, header[12] + index * 4)
            address = (self.LOAD_SEGMENT + segment) * 16 + offset
            self.word(address, self.word(address) + self.LOAD_SEGMENT)
        # The verified dispatcher's relocated MOV AX, DGROUP operand.
        self.data = self.word(load + 0x439) * 16

    def word(self, address, value=None):
        if value is not None:
            self.cpu.mem_write(address, struct.pack('<H', value & 65535))
        return int.from_bytes(self.cpu.mem_read(address, 2), 'little')

    def reset(self, ram_kib):
        assert ram_kib in (256, 512, 768, 1024)
        self.cpu.mem_write(self.data + 0xdc4, struct.pack('<2I', 32768, ram_kib * 1024 - 32768))

    def prepare_command(self, command, arguments):
        assert len(arguments) <= 4
        self.cpu.mem_write(self.data + 0xdb4, struct.pack('<4I', *arguments, *([0] * (4 - len(arguments)))))
        for register, value in ((r.UC_X86_REG_CS, self.LOAD_SEGMENT), (r.UC_X86_REG_IP, 0x248f),
                                (r.UC_X86_REG_SS, 0x9000), (r.UC_X86_REG_SP, 0xff00),
                                (r.UC_X86_REG_DS, 0x1000), (r.UC_X86_REG_AX, command),
                                (r.UC_X86_REG_EFLAGS, 0x202)):
            self.cpu.reg_write(register, value)
        self.cpu.mem_write(0x9ff00, struct.pack('<3H', 0x100, 0xf000, 0x202))

    def command(self, command, *arguments):
        self.prepare_command(command, arguments)
        self.cpu.emu_start(self.LOAD_SEGMENT * 16 + 0x248f, self.RETURN, count=10000)
        assert self.cpu.reg_read(r.UC_X86_REG_CS) * 16 + self.cpu.reg_read(r.UC_X86_REG_IP) == self.RETURN
        return struct.unpack('<4I', self.cpu.mem_read(self.data + 0xdb4, 16))

    def allocate(self, size):
        return self.command(5, size)[1] or None

    def remaining(self):
        return struct.unpack('<I', self.cpu.mem_read(self.data + 0xdc8, 4))[0]
