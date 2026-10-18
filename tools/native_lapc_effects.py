"""Original LAPC-I effects setup/cue/release joined to the original OSL driver.

Supplies filename/resource I/O and protected-to-real-mode register transport.
The actual 32-bit wrappers and 16-bit master/LA driver execute. Prior main-song
identity is an explicit caller input, including the no-song (-1) case.
"""
from pathlib import Path
import sys
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference, r
from native_osl import NativeOSL, r as r16


class NativeLAPCEffects:
    def __init__(self, research=Path('../tfx-reverse'), main_song=-1, image=None):
        standalone = image is None
        directory = research / 'installs/cd_1994_09/TFX'
        launcher = (directory / 'START.EXE').read_bytes()
        sys.path.insert(0, str(research / 'did-unpack'))
        from did_unpack import Archive
        self.archive = Archive.read(directory / 'DID.DAT')
        self.entries = {entry.identifier: entry for entry in self.archive.entries}
        self.device = NativeOSL(launcher)
        self.image = image = image if image is not None else NativeReference(directory / 'TFX.DAT')
        self.source = None
        self.loads, self.commands = [], []
        names, at = [], 0x4f6e
        while launcher[at:at + 6] == b'tunes\\':
            end = launcher.index(0, at)
            names.append(launcher[at:end].decode())
            at = end + 1
        image.cpu.mem_map(0x1000, 0xf000)
        image.cpu.mem_map(0x300000, 0x1000)
        image.cpu.mem_write(0x300000, b'\xc3')
        image.cpu.mem_write(0x3000, b'TFX\\\0')
        image.write(0xa3f8, '<I', 0x300000)
        if main_song is not None:
            image.write(0xa3e4, '<i', main_song)
        if standalone:
            image.write(0xa4e8, '<2B', 2, 2)
            image.write(0x8866, '<B', 1)
            image.write(0xa3d8, '<B', 1)
            image.write(0xab4c, '<h', 0)  # Explicit non-CD caller context.

        def filename(current):
            pointer = current.cpu.reg_read(r.UC_X86_REG_EAX)
            name = bytes(current.cpu.mem_read(pointer, 256)).split(b'\0')[0].decode()
            self.loads.append(name)
            self.source = self.archive.unpack(self.entries[self.archive.hash_name(name)])
            current.return_from()

        def bridge(cpu, address, size, unused):
            command = image.read(0x16f50, '<I')[0] >> 8 & 255
            self.commands.append([command, *(image.read(at, '<I')[0] for at in (0x16f50, 0x16f44, 0x16f4c, 0x16f48))])
            if command == 0x1f:
                image.write(0x16f50, '<I', 0x3000)
                image.write(0x16f48, '<I', 0)
            elif command == 0x13:
                index = image.read(0x16f44, '<I')[0] & 255
                image.cpu.mem_write(0x2000, names[index].encode() + b'\0')
                image.write(0x16f50, '<I', 0x2000)
                image.write(0x16f48, '<I', 0)
            elif command == 0x14:
                assert self.source is not None
                result, carry = self.device.load(self.source)
                assert not carry
                image.write(0x16f50, '<I', result)
            else:
                assert command in (3, 4, 6, 0x1c, 0x1d, 255), ('unexpected LAPC effects bridge', command)
                pairs = [('AX', 0x16f50), ('BX', 0x16f44), ('CX', 0x16f4c), ('DX', 0x16f48)]
                values = {name: image.read(at, '<I')[0] & 65535 for name, at in pairs}
                self.device.call(0x9b4, 'iret', **values)
                for name, at in pairs:
                    image.write(at, '<I', self.device.cpu.reg_read(getattr(r16, 'UC_X86_REG_' + name)))
            image.return_from()

        image.intercept(0xa51ec, 'Supply the requested original effects resource at its filename/read boundary.', filename)
        image.cpu.hook_add(UC_HOOK_CODE, bridge, begin=0x300000, end=0x300000)
        self.device.initialise()
        self.device.shared_timer()

    def begin(self):
        self.image.call(0xa5fc8)
        assert self.loads[-1] == 'tunes\\fxonly.rld'

    def cue(self, order):
        self.image.call(0xa6068, eax=order)

    def tick(self):
        self.device.host_tick()

    def enable_music(self, enabled):
        self.image.write(0x8866, '<B', bool(enabled))
        self.image.call(0xa5c4c if enabled else 0xa5ce0)

    def end(self):
        self.image.call(0xa60e4)
