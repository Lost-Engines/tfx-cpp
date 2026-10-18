#!/usr/bin/env python3
"""Compare complete original Gravis sample requests and persistent cooldowns.

The DDA88 variadic wrapper, DDADC selection, queue assembly and first-item
dispatch execute unchanged. GF1 voice stopped flags and resident/streamed
sample metadata are declared inputs. Stop/play delivery is observed; this
does not substitute an emulated device or claim hardware interrupt timing.
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
    image.cpu.mem_map(0x300000, 0x2000)
    image.write(0x25ce4, '<I', 0x300000)
    events, queued = [], []
    stopped = [True] * 4

    def status(current):
        voice = current.cpu.reg_read(r.UC_X86_REG_EAX)
        assert 0 <= voice < 4, voice
        events.append(('status', voice))
        current.cpu.reg_write(r.UC_X86_REG_EAX, int(stopped[voice]))
        current.return_from()

    def stop(current):
        events.append(('stop', current.cpu.reg_read(r.UC_X86_REG_EAX)))
        current.return_from()

    def play(current, resident):
        registers = (r.UC_X86_REG_EAX, r.UC_X86_REG_EDX, r.UC_X86_REG_EBX)
        if resident:
            registers += (r.UC_X86_REG_ECX,)
        events.append(('resident' if resident else 'stream',
                       *[current.cpu.reg_read(register) for register in registers]))
        current.return_from()

    image.intercept(0xe6b3c, 'Supply actual GF1 stopped flags at the hardware query boundary.', status)
    image.intercept(0xe6be4, 'Observe selected GF1 voice stop.', stop)
    image.intercept(0xe6adc, 'Observe resident GF1 start address, end and rate.', lambda current: play(current, True))
    image.intercept(0xe6bb0, 'Observe streamed GF1 source, size and rate.', lambda current: play(current, False))
    image.intercept(0xddc84, 'Observe queue input; the complete descriptor conversion executes.',
                    lambda current: queued.append((current.cpu.reg_read(r.UC_X86_REG_EDX) - image.data - 0x9860) // 26))
    rng = random.Random(0xddadc)
    rows = []
    for case in range(8192):
        sequence = [rng.randrange(6) for _ in range(case % 7)]
        header = [int(case % 32 == 0), int(case % 13 != 0), rng.choice([0, 1, 2, 255]),
                  rng.randrange(4), rng.choice([0, 1, 4, 18, 54, 32767, 65535]),
                  rng.choice([0, 1, 2, 255]), rng.randrange(16), len(sequence)]
        definitions = [value for _ in range(6) for value in
                       (rng.choice([-32768, -1, 0, 1, 54, 32767]),
                        rng.choice([0, 1, 100, 65535]), int(rng.randrange(8) != 0),
                        int(case % 96 < 64 or rng.randrange(2)))]
        rows.append(header + sequence + definitions)
    output = subprocess.check_output([str((args.build / 'gus_scheduler_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
    assert len(output) == len(rows)
    fixtures, voices = [], set()
    accepted_count = 0
    for case, (row, line) in enumerate(zip(rows, output)):
        reset, enabled, last, cursor, elapsed, priority, mask, count = row[:8]
        sequence, definitions = row[8:8 + count], row[8 + count:]
        if reset:
            image.cpu.mem_write(0x300000, bytes(4096))
            image.write(0xdfc0, '<B', last)
            image.write(0xdfc1, '<B', cursor)
            for sample in range(6):
                delay, size, available, resident = definitions[sample * 4:sample * 4 + 4]
                at = 0x9860 + sample * 26
                flags = int(available) | (6 if resident else 0)
                image.write(at, '<I', image.data + 0x3874)
                image.write(at + 4, '<HHIhIIHH', 8363, delay & 65535, 0, 0, size, 0x5000 + sample * 0x100, 0, flags)
            image.write(0x9860 + 6 * 26, '<I', 0)
        stopped[:] = [bool(mask & (1 << voice)) for voice in range(4)]
        image.write(0xac85, '<B', enabled)
        image.call(0xc513c, eax=image.data + 0x9860, edx=elapsed)
        events.clear()
        queued.clear()
        image.call(0xdda88, stack=(priority, *[image.data + 0x9860 + sample * 26 for sample in sequence], 0))
        stops = [event[1] for event in events if event[0] == 'stop']
        assert len(stops) <= 1, stops
        accepted = [sample for sample in queued if image.read(0x9860 + sample * 26 + 14, '<I')[0]]
        assert bool(stops) or not accepted, (case, events, queued)
        if stops:
            voice = stops[0]
            voices.add(voice)
            accepted_count += 1
            assert events[:2] == [('status', voice), ('stop', voice)], events
            starts = events[2:]
            if accepted:
                at = 0x9860 + accepted[0] * 26
                size, source = image.read(at + 14, '<2I')
                resident = image.read(at + 24, '<H')[0] & 6 == 6
                wanted = ('resident', voice, source, source + size, 8363) if resident else ('stream', source, size, 8363)
                assert starts == [wanted], (case, starts, wanted)
            else:
                assert not starts, (case, starts)
        expected = [image.read(0xdfc0, '<B')[0], image.read(0xdfc1, '<B')[0],
                    int(bool(stops)), stops[0] if stops else -1, len(accepted), *accepted,
                    *[image.read(0x9860 + sample * 26 + 12, '<h')[0] for sample in range(6)]]
        actual = list(map(int, line.split()))
        assert actual == expected, (case, row, actual, expected)
        if case < 256:
            fixtures.append(row + expected)
    assert voices == {0, 1, 2, 3}, voices
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print(f'{len(rows)} complete original Gravis requests/cooldown updates agree: {accepted_count} accepted across all four voices; availability-first rejection, signed timers, resident rotation, stream selection, idle/priority gates and exact stop/start delivery')


if __name__ == '__main__':
    main()
