"""Supply archive/filesystem/time boundaries to the complete native environment parser.

This is an original-executable verification helper, never used by the game.
The parser, token conversion and resource-selection logic all execute unchanged.
"""
import json
from pathlib import Path
import struct
from unicorn import x86_const as r
from native_reference import NativeReference


def environment_image(research, name):
    research = Path(research)
    image = NativeReference(research / 'installs/cd_1994_09/TFX/TFX.DAT')
    image.call(0xde851)
    image.call(0xde547)
    catalog = json.loads((research / 'analysis/resources/catalog.json').read_text())['entries']
    entries = {}
    for entry in catalog:
        for alias in entry['candidate_names'] + entry.get('verified_names', []) + entry.get('recovered_names', []):
            entries[alias.replace(chr(92), '/').lower()] = entry
    image.cpu.mem_map(0x300000, 0x50000)
    allocation = [0x300000]

    def text(address):
        result = bytearray()
        while (byte := image.cpu.mem_read(address, 1)) != b'\0':
            result.extend(byte)
            address += 1
        return result.decode('latin1')

    def supply(file):
        cpu = image.cpu
        eax, edx = cpu.reg_read(r.UC_X86_REG_EAX), cpu.reg_read(r.UC_X86_REG_EDX)
        if file == 0xc71b4:
            cpu.mem_write(eax, b'\0')
        elif file in (0xc8bec, 0xc8cf0):
            name = text(eax).replace(chr(92), '/').lstrip('/').lower()
            entry = entries.get(name)
            if file == 0xc8bec:
                cpu.reg_write(r.UC_X86_REG_EAX, entry['output_size'] if entry else 0)
            else:
                if entry is None:
                    raise ValueError('missing environment resource ' + name)
                raw = (research / 'extracted/cd_1994_09/resources' / entry['path']).read_bytes()
                cpu.mem_write(edx, raw)
                cpu.reg_write(r.UC_X86_REG_EAX, 1)
        elif file == 0xc91a0:
            cpu.reg_write(r.UC_X86_REG_EAX, allocation[0])
            allocation[0] += (eax + 255) & ~255
            if allocation[0] >= 0x340000:
                raise ValueError('environment allocation exceeded capture arena')
        elif file == 0xc92f7:
            cpu.mem_write(eax, bytes(16))
        elif file == 0xb0eb0:
            stack = cpu.reg_read(r.UC_X86_REG_ESP)
            raise ValueError(text(struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]))
        image.return_from()

    for file, reason in (
        (0xc71b4, 'Supply an empty resource-root prefix'),
        (0xc8bec, 'Supply original archive resource lengths'),
        (0xc8cf0, 'Supply independently decoded original archive bytes'),
        (0xc91a0, 'Supply bounded capture memory allocation'),
        (0xc91f0, 'Release belongs to the capture memory owner'),
        (0xc92f7, 'Supply fixed clock fields for repeatable environment setup'),
        (0xb0eb0, 'Fail the capture on original fatal diagnostics'),
    ):
        image.intercept(file, reason, lambda current, file=file: supply(file))
    image.cpu.mem_write(0x340000, name.encode('ascii') + b'\0')
    image.call(0x747fc, eax=0x340000, limit=2000000)
    return image
