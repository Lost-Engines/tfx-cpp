#!/usr/bin/env python3
"""Execute original Q2.COM's missing-firmware and absent-CSP-device paths.

Supplies an initialized C runtime environment and DOS file-not-found responses.
No QSound, firmware, hardware detection or processing result is substituted.
The check neither installs Creative software nor modifies the game directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR
from unicorn import x86_const as r


def execute(raw, root, device_probe=False):
    cpu = Uc(UC_ARCH_X86, UC_MODE_16)
    cpu.mem_map(0, 0x200000)
    cpu.mem_write(0x10100, raw)
    for register, value in ((r.UC_X86_REG_CS, 0x1000), (r.UC_X86_REG_DS, 0x1000),
                            (r.UC_X86_REG_ES, 0x1000), (r.UC_X86_REG_SS, 0x1000),
                            (r.UC_X86_REG_SP, 0xff00), (r.UC_X86_REG_FLAGS, 0x202)):
        cpu.reg_write(register, value)
    cpu.mem_write(0x13a88, struct.pack('<H', 0x5000))
    cpu.mem_write(0x15000, struct.pack('<2H', 0x5010, 0))
    cpu.mem_write(0x15010, ('SOUND=' + root + '\0').encode('ascii'))
    cpu.mem_write(0x15100, struct.pack('<3H', 0x5120, 0x5130, 0))
    cpu.mem_write(0x15120, b'Q2.COM\0')
    cpu.mem_write(0x15130, b'32768\0')
    cpu.mem_write(0x1ff00, struct.pack('<4H', 0xf000, 2, 0x5100, 0))
    opened = []

    def interrupt(current, number, unused):
        ax = current.reg_read(r.UC_X86_REG_AX)
        assert number == 0x21 and ax >> 8 == 0x3d, ('undeclared DOS boundary', number, ax)
        pointer = current.reg_read(r.UC_X86_REG_DS) * 16 + current.reg_read(r.UC_X86_REG_DX)
        opened.append(bytes(current.mem_read(pointer, 256)).split(b'\0')[0].decode('ascii'))
        current.reg_write(r.UC_X86_REG_AX, 2)  # DOS file/device not found.
        current.reg_write(r.UC_X86_REG_FLAGS, current.reg_read(r.UC_X86_REG_FLAGS) | 1)

    cpu.hook_add(UC_HOOK_INTR, interrupt)
    cpu.emu_start(0x10000 + (0x39a if device_probe else 0x962), 0x1f000, count=1000000)
    assert cpu.reg_read(r.UC_X86_REG_IP) == 0xf000
    assert cpu.reg_read(r.UC_X86_REG_AX) == 0
    assert bytes(cpu.mem_read(0x80000, 12)) == bytes(12), 'failed initialization published a QSound interface'
    expected = ['CSPXXXX0'] if device_probe else [root + '\\CSP\\WFM0001' + chr(letter) + '.CSP' for letter in range(ord('z'), ord('a') - 1, -1)]
    assert opened == expected, (opened, expected)
    return {'sound_directory': root, 'device_probe': device_probe, 'opened': opened,
            'initialized': False, 'published_interface': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--output', type=Path, help='optional JSON evidence manifest')
    args = parser.parse_args()
    raw = (args.research / 'installs/cd_1994_09/TFX/Q2.COM').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '24d626ce3a436296cd4cbfeb4123c8eb0b26765cb73f6678346512fb064edbbf'
    results = [execute(raw, root) for root in ('C:\\SB16', 'D:\\CREATIVE', 'C:\\SOUND')]
    results.append(execute(raw, 'C:\\SB16', True))
    if args.output:
        args.output.write_text(json.dumps(results, indent=2) + '\n')
    print('Original Q2.COM main: 26 CSP firmware candidates searched under each of three SOUND roots; missing firmware returns without publishing its interface. Original CSP lookup: CSPXXXX0 absent -> initialization fails. These checks establish dependencies, not QSound synthesis.')


if __name__ == '__main__':
    main()
