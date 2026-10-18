#!/usr/bin/env python3
"""Compare complete original gear-key warning, eligibility and toggle delivery."""
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
    events = []
    for address, name in ((0x81198, 'warning'), (0xa4edc, 'sample'), (0xa6068, 'lapc'), (0xb52d4, 'model')):
        def observe(current, name=name):
            value = current.cpu.reg_read(r.UC_X86_REG_EDX if name == 'model' else r.UC_X86_REG_EAX)
            events.append((name, value))
            current.return_from()
        image.intercept(address, 'Observe ' + name + ' delivery; the complete gear key/toggle handlers execute.', observe)
    rng = random.Random(0x84914)
    cases = []
    for index in range(4096):
        cases.append([index % 4, rng.choice([-2147483648, -1, 0, 349, 350, 351, 1000, 2147483647]),
                      rng.randrange(2), rng.choice([0, 1, 2, 11, 14, 255]),
                      *[int(rng.randrange(8) == 0) for _ in range(5)]])
    output = subprocess.check_output([str((args.build / 'gear_key_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in cases) + '\n').encode()).decode().splitlines()
    assert len(output) == len(cases)
    fixtures = []
    for index, (row, line) in enumerate(zip(cases, output)):
        craft, speed, down, condition, inhibited, crashed, disabled, landing, landed = row
        for at, fmt, value in ((0x11b2a, '<H', craft), (0x13444, '<i', speed), (0x146d8, '<d', down),
                              (0x7d7a, '<B', condition), (0xabe9, '<B', inhibited), (0x12c04, '<H', crashed),
                              (0x86ce, '<B', disabled), (0x86cf, '<B', landing), (0x8d3a, '<H', landed)):
            image.write(at, fmt, value)
        events.clear()
        image.call(0x84914)
        expected = [int(any(name == 'warning' for name, _ in events)), int(image.read(0x146d8, '<d')[0] != 0),
                    image.read(0x7d7a, '<B')[0],
                    *[next((value for name, value in events if name == kind), 0) for kind in ('sample', 'lapc', 'model')]]
        assert list(map(int, line.split())) == expected, (index, row, line, expected, events)
        assert all(value == image.data + 0x195c for name, value in events if name == 'warning')
        if index < 256:
            fixtures.append(row + expected)
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print('4096 complete original gear-key calls agree: craft-specific 350-speed boundary, warning precedence, grounded/inhibited/disabled/landing gates, failed/intermittent gear, state, sample, LAPC cue and model entry')


if __name__ == '__main__':
    main()
