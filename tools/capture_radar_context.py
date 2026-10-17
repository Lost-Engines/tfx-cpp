#!/usr/bin/env python3
"""Observe original live radar inputs without changing game instructions."""
import argparse
import json
from pathlib import Path
import runpy
import sys
from unicorn import UC_HOOK_CODE
import native_dpmi


images = []


class RadarReference(native_dpmi.DpmiReference):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        images.append(self)
        self.observed_frame = -1
        self.radar_events = []

        def boundary(cpu, at, size, unused):
            self.observed_frame += 1

        def radar(cpu, at, size, unused):
            if len(self.radar_events) >= 256:
                raise RuntimeError('radar observation exceeded its frame bound')
            projectiles = []
            head = self.read(0x16e80, '<I')[0]
            tail = self.read(0x16e7c, '<I')[0]
            pointer = int.from_bytes(cpu.mem_read(head + 52, 4), 'little') if head else tail
            while pointer != tail:
                if len(projectiles) >= 98:
                    raise RuntimeError('radar projectile list exceeded its pool')
                projectiles.append({
                    'weapon': cpu.mem_read(pointer + 6, 1)[0],
                    'position': list(self.read(pointer - self.data + 8, '<3i')),
                    'previous': list(self.read(pointer - self.data + 20, '<3i')),
                    'player_owned': self.read(pointer - self.data + 75, '<I')[0] == self.data + 0x10f28,
                })
                pointer = self.read(pointer - self.data + 52, '<I')[0]
            self.radar_events.append({
                'frame': self.observed_frame + 1,
                'pulse_before': bool(self.read(0x7772, '<B')[0]),
                'player': [self.read(field, '<i')[0] for field in (0x13424, 0x13430, 0x1343c)],
                'heading': self.read(0x86ca, '<H')[0],
                'range': self.read(0x7d7c, '<h')[0],
                'offset': [self.read(field, '<h')[0] for field in (0x10be8, 0x10be6)],
                'projectiles': projectiles,
            })

        self.cpu.hook_add(UC_HOOK_CODE, boundary, begin=self.native(0x72045), end=self.native(0x72045))
        self.cpu.hook_add(UC_HOOK_CODE, radar, begin=self.native(0x82a2c), end=self.native(0x82a2c))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--mission', type=int, default=501)
    parser.add_argument('--frames', type=int, default=220)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference = native_dpmi.DpmiReference
    native_dpmi.DpmiReference = RadarReference
    sys.argv = ['capture_native_flight.py', '--research', str(args.research.resolve()),
                '--mission', str(args.mission), '--frames', str(args.frames),
                '--inputs', str(args.inputs.resolve()), '--output', str(args.output.resolve())]
    try:
        runpy.run_path(str(Path(__file__).with_name('capture_native_flight.py')), run_name='__main__')
    finally:
        native_dpmi.DpmiReference = reference
        if images and args.output.exists():
            (args.output / 'radar.json').write_text(json.dumps(images[-1].radar_events, indent=2) + '\n')


if __name__ == '__main__':
    main()
