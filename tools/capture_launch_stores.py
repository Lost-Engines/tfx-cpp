#!/usr/bin/env python3
"""Observe original launch fuel/loadout ordering without replacing game code."""
import argparse
import json
from pathlib import Path
import runpy
import sys
from unicorn import UC_HOOK_CODE
import native_reference

images = []

class LaunchReference(native_reference.NativeReference):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_events = []
        images.append(self)
        functions = {
            0x8c184: 'player_start',
            0x8c318: 'engine_start',
            0x8b248: 'loadout_setup',
            0x8b47c: 'arming_screen',
            0x8978c: 'default_button',
            0x95dc8: 'accumulate_stores',
            0x95f3c: 'physical_start',
            0x72045: 'flight_frame',
        }
        for address, name in functions.items():
            def observe(cpu, at, size, unused, name=name):
                if len(self.launch_events) >= 200:
                    raise RuntimeError('launch observation exceeded its bounded event count')
                self.launch_events.append({
                    'event': name,
                    'fuel': self.read(0x14858, '<d')[0],
                    'pylons': list(self.cpu.mem_read(self.data + 0x13374, 22)),
                    'raw_fields': {hex(field): self.read(field, '<d')[0] for field in (0x14878, 0x14890, 0x14850, 0x14770, 0x14320)},
                })
            self.cpu.hook_add(UC_HOOK_CODE, observe, begin=self.native(address), end=self.native(address))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--mission', type=int, required=True)
    p.add_argument('--frames', type=int, default=16)
    p.add_argument('--flight-model', choices=('arcade', 'simple', 'military-spec', 'realistic'), default='arcade')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    # Add read-only observers before the ordinary complete-session harness
    # constructs its VM. Its existing DOS/video/input boundaries stay intact.
    native_reference.NativeReference = LaunchReference
    sys.argv = ['capture_native_flight.py', '--research', str(a.research.resolve()),
                '--mission', str(a.mission), '--frames', str(a.frames), '--flight-model', a.flight_model,
                '--output', str(a.output.resolve())]
    try:
        runpy.run_path(str(Path(__file__).with_name('capture_native_flight.py')), run_name='__main__')
    finally:
        if images and a.output.exists():
            (a.output / 'launch.json').write_text(json.dumps(images[-1].launch_events, indent=2) + '\n')
    events = images[-1].launch_events
    for event in events:
        print(event, flush=True)


if __name__ == '__main__':
    main()
