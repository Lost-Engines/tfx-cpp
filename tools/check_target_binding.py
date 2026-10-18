#!/usr/bin/env python3
"""Compare original mission-target binding with fixed and mobile registries.

The complete 70B70 binding loop and both actor searches execute. Caller-owned
registries, terrain lookup and the first target's custom-word resource pointer
are declared inputs. No search, priority or destroyed/retired gate is replaced.
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
    image.cpu.mem_map(0x300000, 0x30000)
    queries = []

    def terrain(current):
        queries.append([current.cpu.reg_read(register) for register in
                        (r.UC_X86_REG_EAX, r.UC_X86_REG_EDX, r.UC_X86_REG_EBX)])
        current.cpu.reg_write(r.UC_X86_REG_EAX, 0x3000)
        current.return_from()

    image.intercept(0xb0d80, 'Supply the terrain-cell handle after the actual actor searches fail.', terrain)
    image.intercept(0xb6e48, 'Supply zero custom aim offsets for the already selected first target.',
                    lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0x320000), current.return_from()))
    rng = random.Random(0x70b70)
    signed = lambda value: (value + 2**31) % 2**32 - 2**31
    word = lambda value: (value + 2**15) % 2**16 - 2**15
    rows = []
    cases = []
    for case in range(4096):
        position = [rng.choice([-2**31, -1, 0, 2047, 2048, 409599, 2**31-1])
                    if case < 128 else rng.randrange(-1000000, 1000000)
                    for _ in range(3)]
        cell = [position[axis] >> 11 for axis in (0, 2)]
        centre = [signed((word(value) << 19) + 0x40000) for value in cell]
        fixed = [[rng.randrange(-2**31, 2**31) for _ in range(3)] for _ in range(case % 5)]
        surface = [[slot, *[rng.randrange(-2**31, 2**31) for _ in range(3)],
                    rng.choice([0, 1, 2, 8, 16, 24, 255])]
                   for slot in rng.sample(range(50), case % 9)]
        if fixed and case % 4 < 2:
            for index in range(min(2, len(fixed))):
                fixed[index] = [centre[0], rng.randrange(-2**31, 2**31), centre[1]]
        if surface and case % 4 in (1, 2):
            for index, actor in enumerate(surface[:4]):
                actor[1:4] = [centre[0], rng.randrange(-2**31, 2**31), centre[1]]
                actor[4] = [8, 0, 16, 1][index]
        row = [*position, len(fixed), len(surface),
               *[value for point in fixed for value in point],
               *[value for actor in surface for value in actor]]
        rows.append(row)
        cases.append((position, cell, fixed, surface))
    output = subprocess.check_output(
        [str((args.build / 'target_binding_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode())
    output = output.decode().splitlines()
    assert len(output) == len(cases)
    fixtures = []
    domains = set()
    for case, ((position, cell, fixed, surface), line) in enumerate(zip(cases, output)):
        image.write(0x11b22, '<H', 1)
        image.write(0x5c40, '<3i', *position)
        image.write(0x5c4c, '<H', 0xfffe)
        image.write(0xe742, '<B', 1)
        image.write(0x5980, '<I', 0x300000 if fixed else 0)
        image.cpu.mem_write(image.data + 0x128c8, bytes(50 * 4))
        for index, point in enumerate(fixed):
            address = 0x300000 + index * 32
            image.cpu.mem_write(address, bytes(32))
            image.cpu.mem_write(address + 1, struct.pack('<3i', *point))
            image.cpu.mem_write(address + 13, struct.pack('<HI', 0x1000 + index,
                                  0x300000 + (index + 1) * 32 if index + 1 < len(fixed) else 0))
        for slot, x, y, z, flags in surface:
            address = 0x310000 + slot * 64
            image.write(0x128c8 + slot * 4, '<I', address)
            image.cpu.mem_write(address, bytes(64))
            image.cpu.mem_write(address, struct.pack('<3i', x, y, z))
            image.cpu.mem_write(address + 36, struct.pack('<H', 0x2000 + slot))
            image.cpu.mem_write(address + 47, bytes([flags]))
        queries.clear()
        image.call(0x70b70, limit=100000)
        handle = image.read(0x5c4c, '<H')[0]
        if 0x1000 <= handle < 0x2000:
            wanted = [0, handle - 0x1000, 0, 0]
        elif 0x2000 <= handle < 0x3000:
            wanted = [1, handle - 0x2000, 0, 0]
        else:
            assert handle == 0x3000, handle
            wanted = [2, 0, *cell]
        assert queries == ([[0, *[value & 0xffffffff for value in cell]]] if wanted[0] == 2 else []), queries
        assert image.read(0xe742, '<B')[0] == 0
        actual = list(map(int, line.split()))
        assert actual == wanted, (case, rows[case], actual, wanted)
        domains.add(wanted[0])
        if case < 256:
            fixtures.append(rows[case] + wanted)
    assert domains == {0, 1, 2}, domains
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print(f'{len(cases)} complete original target bindings agree: fixed-scenery priority/list order, mobile slot order, destroyed/retired exclusion, exact cell centres with ignored height, signed/wrapped coordinates and terrain fallback')


if __name__ == '__main__':
    main()
