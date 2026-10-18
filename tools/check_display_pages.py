#!/usr/bin/env python3
"""Compare original 74104's persistent footer-refresh decision before painting.

The entire decision prefix executes, stopping at its original clamp boundary.
No instruction is replaced. VGA page rotation and retained pixels are checked
through the separate complete-flight comparisons.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference, r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    image = NativeReference(args.research / 'installs/cd_1994_09/TFX/TFX.DAT')
    rng = random.Random(0x74104)
    rows, previous = [], -1
    for index in range(8192):
        reset = index % 97 == 0
        if reset:
            previous = -1
        offset = previous if rng.randrange(4) else rng.choice([-32768, -100, -1, 0, 1, 28, 54, 55, 199, 32767])
        rows.append([int(reset), rng.choice([0, 0, 0, 1, 2, 3, 4, 255]), offset])
        previous = offset
    output = subprocess.check_output([str((args.build / 'display_pages_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
    assert len(output) == len(rows)
    fixtures, copied = [], 0
    for index, (row, line) in enumerate(zip(rows, output)):
        reset, phase, offset = row
        if reset:
            image.write(0x10be2, '<h', -1)
        image.write(0x10bed, '<B', phase)
        image.write(0x10be6, '<h', offset)
        image.cpu.mem_write(image.STACK, struct.pack('<I', image.RETURN))
        image.cpu.reg_write(r.UC_X86_REG_ESP, image.STACK)
        image.cpu.reg_write(r.UC_X86_REG_EFLAGS, 0x202)
        image.cpu.emu_start(image.native(0x74104), image.native(0x7414d), count=100)
        assert image.cpu.reg_read(r.UC_X86_REG_EIP) == image.native(0x7414d)
        base = image.cpu.reg_read(r.UC_X86_REG_EBP)
        copy = struct.unpack('<I', image.cpu.mem_read(base - 12, 4))[0]
        expected = [copy, image.read(0x10bed, '<B')[0]]
        assert list(map(int, line.split())) == expected, (index, row, line, expected)
        assert image.read(0x10be2, '<h')[0] == offset
        copied += copy
        if index < 512:
            fixtures.append(row + expected)
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print(f'8192 original footer-refresh decisions agree: {copied} copies, retained Y, raw signed offsets, shared byte countdown and reset persistence')


if __name__ == '__main__':
    main()
