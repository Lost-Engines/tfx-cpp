#!/usr/bin/env python3
"""Compare complete original actor initialisation and Q8 movement with C++.

Only allocation and SSD resource creation are host boundaries. Native profile
lookup, pool limits, group copying and formation placement execute unchanged.
Player route conversion is checked separately; no AI/combat is simulated here.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference, r


def dataset(path):
    text = path.read_text()
    return json.loads(text[text.index('=') + 1:].strip().removesuffix(';'))


def original(data_dir, raw, profiles):
    image = NativeReference(data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 0x50000)
    image.cpu.mem_write(0x300000, raw)
    heap = 0x330000

    def allocate(im):
        nonlocal heap
        size = im.cpu.reg_read(r.UC_X86_REG_EAX)
        assert heap + size < 0x350000
        im.cpu.reg_write(r.UC_X86_REG_EAX, heap)
        heap += (size + 15) & ~15
        im.return_from()

    image.intercept(0xc90ec, 'Bounded host allocation; native clearing/copying and pool management remain active', allocate)
    image.intercept(0xb4d98, 'SSD creation is a declared resource boundary; return a valid synthetic handle', lambda im: (im.cpu.reg_write(r.UC_X86_REG_EAX, 1), im.return_from()))
    image.intercept(0x75228, 'Player routes checked with the native converter separately', lambda im: im.return_from())
    for index, profile in enumerate(profiles):
        pointer = 0x320000 + index * 128
        image.cpu.mem_write(pointer, bytes.fromhex(profile['hex']))
        image.write(0x127ec + index * 4, '<I', pointer)
    image.write(0xac58, '<i', -16384)
    image.write(0xac5c, '<i', 0)
    image.call(0x75690, eax=0x300000, limit=2000000)
    rows = []
    for pool in (0x10f6c, 0x11034, 0x128c8):
        for slot in range(50):
            pointer = image.read(pool + slot * 4, '<I')[0]
            if not pointer:
                continue
            source = bytes(image.cpu.mem_read(pointer, 68 if pool != 0x128c8 else 49))
            air = pool != 0x128c8
            profile_pointer = struct.unpack_from('<I', source, 0x3c if air else 0x2a)[0]
            profile = bytes(image.cpu.mem_read(profile_pointer, 34))
            command = struct.unpack_from('<I', source, 0x2c if air else 0x26)[0] - 0x300000
            row = [14 if air else 16, command, struct.unpack_from('<H', profile, 32)[0], slot, profile[31]]
            row += list(struct.unpack_from('<3i', source)) + list(struct.unpack_from('<3H', source, 12))
            row += [struct.unpack_from('<i', source, 18)[0], struct.unpack_from('<H' if air else '<B', source, 0x42 if air else 0x2f)[0]]
            row += [source[0x28], source[0x29]] if air else [255, 0]
            rows.append(row)
    return sorted(rows, key=lambda row: (row[1], row[14]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    args = parser.parse_args()
    data_dir = args.research / 'installs/cd_1994_09/TFX'
    profiles = dataset(args.research / 'analysis/entities/data.js')['records']
    programs = json.loads((args.research / 'analysis/waypoints/programs.json').read_text())['programs']
    names = [p['names'][0] if p['names'] else p['id'] for p in programs]
    result = subprocess.run([str((args.build / 'actor_probe').resolve()), str(data_dir)], input='\n'.join(names) + '\n', text=True, capture_output=True, check=True)
    lines = iter(result.stdout.splitlines())
    total = 0
    for program, name in zip(programs, names):
        header = next(lines).split()
        assert header[0] == name
        observed = [list(map(int, next(lines).split())) for _ in range(int(header[2]))]
        for _ in range(int(header[3])):
            next(lines)
        expected = original(data_dir, (args.research / 'extracted/cd_1994_09/resources' / program['path']).read_bytes(), profiles)
        assert observed == expected, (name, [(a, b) for a, b in zip(observed, expected) if a != b][:3], len(observed), len(expected))
        total += len(expected)
    assert next(lines, None) is None
    generator = random.Random(0xc0560)
    image = NativeReference(data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 4096)
    image.write(0xac58, '<i', -16384)
    image.write(0xac5c, '<i', 0)
    requests, expected = [], []
    for i in range(4096):
        position = [generator.randrange(-100000000, 100000001), generator.randrange(-6000000, 2000000), generator.randrange(-100000000, 100000001)]
        angles = [generator.randrange(65536) for _ in range(3)]
        distance = generator.randrange(-100000, 100001)
        requests.append(' '.join(map(str, (*position, *angles, distance))))
        image.cpu.mem_write(0x300000, struct.pack('<3i3H', *position, *angles))
        image.call(0xc0560, eax=0x300000, edx=0x30000c, ebx=distance & 0xffffffff)
        expected.append(list(struct.unpack('<3i', image.cpu.mem_read(0x300000, 12))))
    result = subprocess.run([str((args.build / 'actor_probe').resolve()), 'move'], input='\n'.join(requests) + '\n', text=True, capture_output=True, check=True)
    observed = [list(map(int, row.split())) for row in result.stdout.splitlines()]
    assert observed == expected, next(((i, a, b) for i, (a, b) in enumerate(zip(observed, expected)) if a != b), None)
    print(f'{len(programs)} native program initialisations ({total} individual actors) and {len(expected)} wrapped movement cases match')


if __name__ == '__main__':
    main()
