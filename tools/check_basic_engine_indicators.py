#!/usr/bin/env python3
"""Compare basic-flight speed with separate engine factors and status bytes.

Executes original initialization and 8C6E8, supplying only input/timer/device
boundaries. The cross-product includes freshly failed/intermittent indicators
whose factor has already fallen to zero, before the outer indicator refresh.
"""
import argparse
from pathlib import Path
import subprocess
from native_reference import NativeReference, r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    image = NativeReference(args.research / 'installs/cd_1994_09/TFX/TFX.DAT')
    image.call(0xde851)
    image.intercept(0x744e4, 'No DOS mouse driver is present at initialization.',
                    lambda im: (im.cpu.reg_write(r.UC_X86_REG_EAX, 0), im.return_from()))
    image.intercept(0x74614, 'Mouse range reset is an external device boundary.', lambda im: im.return_from())
    baseline = bytes(image.cpu.mem_read(image.data, image.layout['objects'][2]['virtual_size']))
    inputs, expected = [], []
    for aircraft in (1, 2, 3):
        for factors in range(4):
            for left in (0, 1, 2, 11, 14, 255):
                for right in (0, 1, 2, 11, 14, 255):
                    image.cpu.mem_write(image.data, baseline)
                    image.write(0x13424, '<i', 293888)
                    image.write(0x13430, '<i', -1800)
                    image.write(0x1343c, '<i', 236544)
                    image.write(0x86c8, '<3H', 0, 0, 0)
                    image.write(0x86f4, '<f', .65)
                    image.write(0x11b2a, '<H', aircraft - 1)
                    image.write(0x1347a, '<B', 0)
                    image.write(0x11b3c, '<B', 0)
                    image.call(0x8c184)
                    image.call(0x8c318)
                    image.write(0x14880, '<2d', float(bool(factors & 1)), float(bool(factors & 2)))
                    image.write(0x7d72, '<B', left)
                    image.write(0x7d75, '<B', right)
                    image.write(0x13476, '<H', 90)
                    image.call(0x8c6e8)
                    inputs.append([aircraft, factors, left, right])
                    expected.append([image.read(at, fmt)[0] for at, fmt in
                                     ((0x133cc, '<I'), (0x86f4, '<I'), (0x14778, '<Q'), (0x133f8, '<I'))])
    result = subprocess.run([str((args.build / 'basic_engine_probe').resolve())],
                            input='\n'.join(' '.join(map(str, row)) for row in inputs) + '\n',
                            capture_output=True, text=True, check=True)
    actual = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    assert len(actual) == len(expected)
    for case, got, wanted in zip(inputs, actual, expected):
        assert got == wanted, (case, got, wanted)
    if args.record:
        args.record.write_text(''.join(' '.join(map(str, case + values)) + '\n'
                                      for case, values in zip(inputs, expected)))
    print(f'{len(expected)} original basic-flight engine factor/indicator combinations agree in exact speed/throttle bits')


if __name__ == '__main__':
    main()
