#!/usr/bin/env python3
"""Compare native SSD swept-box tests, including directed boundary cases."""
import argparse
import itertools
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=Path('build'))
    args = parser.parse_args()
    image = NativeReference(args.data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 4096)
    rng = random.Random(0x535344)
    cases = []
    # Degenerate/reversed bounds occur in authored data too; do not normalise.
    for index in range(10000):
        lo = [rng.randrange(-32768, 32768) for _ in range(3)]
        hi = [rng.randrange(-32768, 32768) for _ in range(3)]
        if index % 3:
            lo, hi = [min(a,b) for a,b in zip(lo,hi)], [max(a,b) for a,b in zip(lo,hi)]
        movement = [rng.randrange(-32768, 32768) for _ in range(6)]
        cases.append((index % 2, lo + hi + movement))
    for a, b in itertools.product(itertools.product((-11,-10,0,10,11), repeat=2), repeat=2):
        for diagonal in (0,1):
            cases.append((diagonal, [-10,-10,-10,10,10,10,a[0],0,a[1],b[0],0,b[1]]))
    expected = []
    for diagonal, values in cases:
        image.cpu.mem_write(0x300000, struct.pack('<6h', *values[:6]))
        image.write(0x20b8c, '<6h', *values[6:])
        expected.append(bool(image.call(0xb7858 if diagonal else 0xb7768, eax=0x300000) & 255))
    payload = ''.join(' '.join(map(str, [diagonal] + values)) + '\n' for diagonal,values in cases)
    result = subprocess.run([str(args.build / 'tfx_probe'), 'collision'], input=payload, text=True, capture_output=True, check=True)
    actual = [bool(int(value)) for value in result.stdout.split()]
    assert len(actual) == len(expected)
    for index,(a,b) in enumerate(zip(actual,expected)):
        assert a == b, (index, cases[index], 'C++',a,'native',b)
    print(f'{len(cases)} native SSD collision cases agree (axis-aligned, diagonal, reversed and boundary cases)')


if __name__ == '__main__':
    main()
