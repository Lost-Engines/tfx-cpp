#!/usr/bin/env python3
"""Compare translated GF1 register operations with the real GUS.COM driver.

The original interrupt dispatcher and complete playback/volume/stop/status
functions execute. Initialized port addresses, active-voice count and hardware
read values are explicit inputs, established separately by a real GF1 bootstrap.
Seven-read bus delays are omitted from comparison; all semantic reads, port
writes, address wrapping, frequency arithmetic and returned status are checked.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_INSN
from unicorn import x86_const as r
from native_gus_memory import GusMemoryReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--synthetic', action='store_true')
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    filename = args.research / 'installs/cd_1994_09/TFX/GUS.COM'
    image = GusMemoryReference(filename)
    for address, port in ((0x2c9, 0x342), (0x2cb, 0x343), (0x2cd, 0x344), (0x2cf, 0x345), (0x2d3, 0x346)):
        image.word(image.data + address, port)
    image.cpu.mem_write(image.data + 0x2b5, bytes([32]))
    if args.synthetic:
        for index in range(257):
            image.word(image.data + 0x32f + index * 2, (index * 13 + 17) & 4095)
    events, state = [], {}

    def output(cpu, port, size, value, unused):
        if port == 0x343:
            state['register'] = value
        events.extend([1, port, size, value])

    def input(cpu, port, size, unused):
        if port == 0x346:
            return 0  # Native D8A delay reads, with no register side effects.
        assert port == 0x345 and size == 1 and state['register'] in (0x80, 0x8d), (port, size, state)
        value = state['ramp'] if state['register'] == 0x8d else state['control']
        events.extend([0, port, size, value])
        return value

    image.cpu.hook_add(UC_HOOK_INSN, output, None, 1, 0, r.UC_X86_INS_OUT)
    image.cpu.hook_add(UC_HOOK_INSN, input, None, 1, 0, r.UC_X86_INS_IN)
    rng = random.Random(0x1564)
    rows = []
    for case in range(4096):
        command = (1, 2, 4, 9)[case % 4]
        rate = rng.choice([0, 1, 6500, 7500, 8363, 9000, 44100, 65535, 2**32 - 1, rng.randrange(2**32)])
        begin, end = (rng.randrange(2**32) for _ in range(2))
        base = rng.choice([1, 19293, 44100, 65535]) if args.synthetic else 19293
        rows.append([command, rng.randrange(32), begin, end, rate, rng.randrange(257), rng.randrange(256), rng.randrange(256), base])
    output = subprocess.check_output([str((args.build / 'gus_driver_probe').resolve()),
                                     '--synthetic' if args.synthetic else str(filename.resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
    assert len(output) == len(rows)
    fixtures = []
    for case, (row, line) in enumerate(zip(rows, output)):
        command, voice, begin, end, rate, volume, ramp, control, base = row
        image.word(image.data + 0x2c7 + 32 * 2, base)
        state.update(ramp=ramp, control=control)
        events.clear()
        arguments = (voice, begin, end, rate) if command == 1 else (voice, volume) if command == 2 else (voice,)
        result = image.command(command, *arguments)
        expected = [result[1] if command == 4 else -1, len(events) // 4, *events]
        actual = list(map(int, line.split()))
        assert actual == expected, (case, row, actual, expected)
        if case < 256:
            fixtures.append(row + expected)
    if args.record:
        assert args.synthetic, 'asset-free fixtures require explicitly supplied test tables'
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print(f'{len(rows)} complete original GUS.COM playback/volume/stop/status commands agree: every register write and semantic read, 32 hardware voices, reversed/wrapped addresses, dword frequency overflow, volume lookup and stopped flags'+('; test-authored coefficient tables' if args.synthetic else '; original driver tables'))


if __name__ == '__main__':
    main()
