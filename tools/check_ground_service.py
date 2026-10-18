#!/usr/bin/env python3
"""Compare original landing-service eligibility and its persistent serviced latch.

Complete 71E44 executes. Refit, radio/model, reset and flight initialization
are observed consumer boundaries; a declared initializer supplies its final
landed flag. Their numerical/reset integration is a separate flight comparison.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference, r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    image = NativeReference(args.research / 'installs/cd_1994_09/TFX/TFX.DAT')
    image.cpu.mem_map(0x300000, 4096)
    image.write(0x1b238, '<I', 0x300000)
    image.write(0xe74e, '<H', 1)
    delivered, final_landed = [], [False]
    for address in (0xa5a9c, 0x8b5e0, 0x81198, 0xb52d4, 0x8fad4, 0x8c318):
        def consumer(current, address=address):
            delivered.append(address)
            current.return_from()
        image.intercept(address, 'Observe an eligibility controller consumer; numerical/refit delivery has separate comparisons.', consumer)
    image.intercept(0xb1334, 'Supply the caller-owned score variable address.',
        lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0x300100), current.return_from()))
    image.intercept(0x8bba0, 'Supply the downstream weapon-selection result; it does not affect eligibility.',
        lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0), current.return_from()))

    def initialise(current):
        delivered.append(0x8c184)
        current.write(0x8d3a, '<H', final_landed[0])
        current.return_from()
    image.intercept(0x8c184, 'Supply the separately checked flight initializer final landed state.', initialise)
    rng = random.Random(0x71e44)
    rows = [[int(index % 97 == 0), rng.randrange(2), rng.choice([0, 0, -1, 1, 250, -2147483648, 2147483647]),
             *[int(rng.randrange(8) == 0) for _ in range(3)], rng.choice([0, 0, 0, -1, 1, 32767]), rng.randrange(2)]
            for index in range(8192)]
    output = subprocess.check_output([str((args.build / 'ground_service_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
    assert len(output) == len(rows)
    fixtures = []
    for index, (row, line) in enumerate(zip(rows, output)):
        reset, landed, speed, resolved, crashed, disabled, violations, final_landed[0] = row
        if reset:
            image.write(0xe74e, '<H', 1)
        for at, fmt, value in ((0x8d3a, '<H', landed), (0x13444, '<i', speed), (0x593e, '<B', resolved),
                              (0x12c04, '<H', crashed), (0x86ce, '<B', disabled), (0xe75c, '<h', violations)):
            image.write(at, fmt, value)
        delivered.clear()
        image.call(0x71e44)
        values = [int(0x8c184 in delivered), image.read(0xe74e, '<H')[0]]
        assert list(map(int, line.split())) == values, (index, row, line, values, delivered)
        if index < 256:
            fixtures.append(row + values)
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print('8192 complete original service eligibility calls agree: initial-start latch, stopped/landed, completion, loss and orders gates; persistence across repeated stops, airborne reset and post-service initializer changes')


if __name__ == '__main__':
    main()
