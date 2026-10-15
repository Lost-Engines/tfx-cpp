#!/usr/bin/env python3
"""Compare player basis rotations, normalisation and angle extraction with x86."""
import argparse
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--data-dir', type=Path, required=True)
    args = parser.parse_args()
    image = NativeReference(args.data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 4096)
    probe = str((args.build / 'attitude_probe').resolve())
    generator = random.Random(0x8dc50)

    def compare(mode, inputs, expected):
        result = subprocess.run([probe, mode], input='\n'.join(' '.join(map(str, row)) for row in inputs) + '\n', text=True, capture_output=True, check=True)
        observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
        assert len(observed) == len(expected)
        for i, (a, b) in enumerate(zip(observed, expected)):
            assert a == b, (mode, i, inputs[i], a, b)

    directions = [(y, x) for y in (-32768, -32767, -1, 0, 1, 32767) for x in (-32768, -32767, -1, 0, 1, 32767)]
    directions += [(generator.randrange(-32768, 32768), generator.randrange(-32768, 32768)) for _ in range(4096)]
    expected = [[image.call(0xcdc18, stack=(x & 0xffffffff, y & 0xffffffff)) & 65535] for y, x in directions]
    compare('direction', directions, expected)
    rotations, rotated, normalisations, normalised, angles, extracted = [], [], [], [], [], []
    basis = [32767, 0, 0, 0, 32767, 0, 0, 0, 32767]
    for frame in range(2048):
        for axis, entry in enumerate((0xccf4c, 0xcd058, 0xcd15c)):
            amount = generator.randrange(65536) if frame < 128 else generator.randrange(-1000, 1001) & 65535
            rotations.append([axis, amount, *basis])
            image.cpu.mem_write(0x300000, struct.pack('<9h', *basis))
            image.call(entry, eax=0x300000, edx=amount)
            basis = list(struct.unpack('<9h', image.cpu.mem_read(0x300000, 18)))
            rotated.append(list(basis))
        normalisations.append([0, 0, *basis])
        image.call(0xccd3c, eax=0x300000)
        basis = list(struct.unpack('<9h', image.cpu.mem_read(0x300000, 18)))
        normalised.append(list(basis))
        angles.append([0, 0, *basis])
        extracted.append([image.call(entry, eax=0x300000) & 65535 for entry in (0xcd574, 0xcd5a8, 0xcd5c4)])
    compare('rotate', rotations, rotated)
    compare('normalise', normalisations, normalised)
    compare('angles', angles, extracted)
    print(f'{len(directions)} native directions, {len(rotated)} rotations, {len(normalised)} normalisations and {len(extracted)} angle extractions match')


if __name__ == '__main__':
    main()
