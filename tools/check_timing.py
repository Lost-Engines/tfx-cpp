#!/usr/bin/env python3
"""Compare headless C++ clock sequences with bounded original x86 execution.

Only the timer source and projectile motion/contact callbacks are intercepted.
Animation gating and the flight clock/subdivision code execute unmodified.
This is a subsystem replay, not a complete running-flight capture.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference


class TimingCapture:
    def __init__(self, executable, initial):
        self.image = NativeReference(executable)
        self.image.write(0x10bfc, '<I', initial)
        self.image.write(0x13476, '<H', 5)
        self.readings = deque()
        self.consumed = []
        self.projectiles = []
        self.image.intercept(0xa6134, 'external launcher timer: supplied unsigned 32-bit counter readings', self.timer)
        self.image.intercept(0xa31cc, 'projectile motion: capture elapsed word; actor simulation not yet implemented', self.motion)
        self.image.intercept(0xa373c, 'projectile contacts: capture elapsed word; collisions not yet implemented', self.contacts)
        self.image.intercept(0x720a7, 'end of isolated animation-gate block; return to capture caller', lambda image: image.return_from())

    def timer(self, image):
        if not self.readings:
            raise RuntimeError('native flight clock exhausted declared timer inputs')
        counter = self.readings.popleft()
        self.consumed.append(counter)
        image.write(0x16f2c, '<I', counter)
        image.return_from()

    def motion(self, image):
        self.projectiles.append(('motion', image.read(0x13476, '<H')[0]))
        image.return_from()

    def contacts(self, image):
        self.projectiles.append(('contacts', image.read(0x13476, '<H')[0]))
        image.return_from()

    def frame(self, model, warp, allowed, readings):
        self.readings = deque(readings)
        self.consumed.clear()
        self.projectiles.clear()
        self.image.call(0x7205c)
        animate, = self.image.read(0xac90, '<B')
        remainder, = self.image.read(0xe74c, '<h')
        model_code, = struct.unpack_from('<H', self.image.executable, 973476 + 0xa4ee + (model & 3) * 2)
        self.image.write(0x1347a, '<B', model_code)
        self.image.write(0xe780, '<B', warp)
        # Pass the raw native inhibition state; its full gameplay ownership is
        # deliberately outside this isolated timing contract.
        self.image.write(0x8d3a, '<H', not allowed)
        self.image.call(0x8c43c)
        elapsed, = self.image.read(0x13476, '<H')
        filtered, = self.image.read(0x8774, '<I')
        seconds, = self.image.read(0x142c0, '<Q')
        assert self.image.read(0x10bfc, '<I')[0] == self.consumed[-1]
        self.image.call(0x71fd4, eax=elapsed)
        assert self.image.read(0x13476, '<H')[0] == elapsed, 'subdivision must restore world elapsed'
        assert len(self.projectiles) % 2 == 0
        chunks = []
        for motion, contact in zip(self.projectiles[::2], self.projectiles[1::2]):
            assert motion[0] == 'motion' and contact == ('contacts', motion[1])
            chunks.append(motion[1])
        source = [model, warp, allowed, len(self.consumed), *self.consumed]
        return source, [elapsed, filtered, seconds, animate, remainder, *chunks]


def compare(probe, initial, frames):
    source = str(initial) + '\n' + '\n'.join(' '.join(map(str, source)) for source, expected in frames) + '\n'
    result = subprocess.run([probe], input=source, text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(frames), 'replay returned a different frame count'
    fields = ['world ticks', 'filtered float bits', 'physics double bits', 'animation enabled', 'animation remainder']
    for index, ((source, expected), line) in enumerate(zip(frames, lines)):
        observed = list(map(int, line.split()))
        if observed != expected:
            for field in range(max(len(observed), len(expected))):
                if observed[field:field+1] != expected[field:field+1]:
                    name = fields[field] if field < len(fields) else f'projectile substep {field - len(fields)}'
                    raise AssertionError(f'frame {index}, {name}: C++ {observed[field:field+1]}, native {expected[field:field+1]}, input {source}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--record', type=Path, help='optional generated capture (use an ignored build directory)')
    args = parser.parse_args()
    probe = (args.build / 'tfx_replay').resolve()
    random_source = random.Random(0x205)
    reports = []
    frames_checked = 0
    for initial in (0, 0xfffffff0):
        capture = TimingCapture(args.data_dir / 'TFX.DAT', initial)
        counter = initial
        frames = []
        for frame in range(2048):
            if frame < 96:
                # All four models, normal/warp/inhibited and tight polling,
                # slow frames, 16-bit accumulation and 32-bit counter wrap.
                model = frame % 4
                warp = int(frame % 3 != 0)
                allowed = int(frame % 3 != 2)
                increment = [0, 1, 2, 4, 18, 19, 100, 65535, 65536, 65537, 0xffffffff, 0x80000000][frame // 8]
            else:
                model = random_source.randrange(4)
                warp = random_source.randrange(2)
                allowed = random_source.randrange(2)
                increment = random_source.choice([0, 1, 2, 3, 4, 10, 18, 25, 100, 0xffff, 0x10000, 0xfffffff0])
            readings = []
            for delta in [increment, 0, 1, 0, 1, 2, 4]:
                counter = (counter + delta) & 0xffffffff
                readings.append(counter)
            item = capture.frame(model, warp, allowed, readings)
            frames.append(item)
            # Unconsumed timer candidates are hypothetical, not elapsed time.
            counter = item[0][-1]
        compare(probe, initial, frames)
        frames_checked += len(frames)
        reports.append({'initial_counter': initial, 'frames': [{'input': source, 'expected': expected} for source, expected in frames]})
    if args.record:
        args.record.write_text(json.dumps({'scope': __doc__, 'x87_control_word': '0x037f (controlled; DOS startup not captured)', 'dependencies': {hex(file): reason for file, reason in capture.image.dependencies.items()}, 'sessions': reports}, separators=(',', ':')) + '\n')
    print(f'{frames_checked} native/C++ timing frames passed: exact float bits, timer consumption, animation order and projectile motion/contact substeps')


if __name__ == '__main__':
    main()
