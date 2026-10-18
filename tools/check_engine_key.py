#!/usr/bin/env python3
"""Compare complete original engine keys, power state and ordered sound/model output."""
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
    events = []

    def samples(current):
        stack = current.cpu.reg_read(r.UC_X86_REG_ESP)
        words = struct.unpack('<8I', current.cpu.mem_read(stack + 4, 32))
        priority, *descriptors = words
        count = descriptors.index(0)
        assert all((pointer - current.data - 0x9860) % 26 == 0 for pointer in descriptors[:count])
        ids = [(pointer - current.data - 0x9860) // 26 for pointer in descriptors[:count]]
        assert all(0 <= identifier < 106 for identifier in ids)
        events.extend([0, priority, count, *ids])
        current.return_from()

    image.write(0xac74, '<I', image.native(0x75954))
    image.intercept(0x75954, 'Observe the requested priority and sample descriptors at the external sound callback.', samples)
    for address, kind, register in ((0xa6068, 1, r.UC_X86_REG_EAX), (0xb52d4, 2, r.UC_X86_REG_EDX)):
        def observe(current, kind=kind, register=register):
            events.extend([kind, current.cpu.reg_read(register)])
            current.return_from()
        image.intercept(address, 'Observe sound/model notification; both engine handlers and afterburner stop execute.', observe)
    rng = random.Random(0x842b0)
    bits = lambda value: struct.unpack('<Q', struct.pack('<d', value))[0]
    cases = [[index % 2, rng.choice([0, 1, 2, 11, 14, 255]), rng.choice([0, 1, 2, 11, 14, 255]),
              rng.choice([0, 1, 4, 255]), bits(rng.choice([0, .25, 1])),
              *[int(rng.randrange(8) == 0) for _ in range(3)], rng.randrange(256), rng.randrange(256)]
             for index in range(4096)]
    output = subprocess.check_output([str((args.build / 'engine_key_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in cases) + '\n').encode()).decode().splitlines()
    assert len(output) == len(cases)
    fixtures = []
    for index, (row, line) in enumerate(zip(cases, output)):
        side, condition, other, afterburner, factor, inhibited, crashed, disabled, control, display = row
        selected, opposite = ((0x7d72, 0x7d75) if not side else (0x7d75, 0x7d72))
        power = 0x14880 if not side else 0x14888
        for at, fmt, value in ((selected, '<B', condition), (opposite, '<B', other), (power, '<Q', factor),
                              (0x1496d, '<B', afterburner), (0xabe9, '<B', inhibited), (0x12c04, '<H', crashed),
                              (0x86ce, '<B', disabled), (0x10bed, '<B', control), (0x6c38, '<B', display)):
            image.write(at, fmt, value)
        events.clear()
        image.call(0x84370 if side else 0x842b0)
        expected = [image.read(power, '<Q')[0], image.read(selected, '<B')[0], image.read(0x1496d, '<B')[0],
                    image.read(0x10bed, '<B')[0], image.read(0x6c38, '<B')[0], len(events), *events]
        assert list(map(int, line.split())) == expected, (index, row, line, expected)
        if index < 256:
            fixtures.append(row + expected)
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print('4096 complete original engine-key calls agree: power factors, normal/off/fault conditions, inhibition, afterburner stop, display state, ordered SB sequences, LAPC cues and model notifications')


if __name__ == '__main__':
    main()
