#!/usr/bin/env python3
"""Compare original 32/16-bit LAPC effects setup/cues/release and MIDI timing.

Uses the original fxonly.rld and master/LA driver, including pool exhaustion
and repeated loading. No synthesizer ROMs or desktop audio devices are needed.
"""
import argparse
from pathlib import Path
import subprocess
from native_lapc_effects import NativeLAPCEffects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--cycles',type=int,default=1)
    parser.add_argument('--report',type=Path)
    args = parser.parse_args()
    if not 1<=args.cycles<=1024:parser.error('--cycles must be between 1 and 1024')
    native = NativeLAPCEffects(args.research)
    events, pending, system = [], [], []
    status, now = 0, 0

    def collect():
        nonlocal status, pending, system
        for value in native.device.events:
            if value >= 248:
                events.append([now, 3, value, 0, 0])
                continue
            if system:
                if value == 247:
                    system.append(value)
                    events.append([now, len(system), *system])
                    system, pending, status = [], [], 0
                    continue
                if value < 128:
                    system.append(value)
                    continue
                system, pending, status = [], [], 0
            if value >= 128:
                pending, status = [], value
                if value == 240:
                    system, status = [value], 0
                elif value in (246, 247):
                    events.append([now, 3, value, 0, 0])
                    status = 0
                elif value in (244, 245):
                    status = 0
                continue
            if not status:
                continue
            pending.append(value)
            length = 1 if status & 240 in (192, 208) or status in (241, 243) else 2
            if len(pending) == length:
                events.append([now, 3, status, *pending, *([0] if length == 1 else [])])
                pending = []
                if status >= 240:
                    status = 0
        native.device.events.clear()

    collect()
    now = settling = 4800
    irq = 0
    cues = (0, 1, 2, 3, 5, 16, 18, 20)
    for cycle in range(args.cycles):
        native.begin()
        collect()
        for frame in range(1000):
            if frame == 150:
                native.enable_music(False)
                collect()
            if frame == 250:
                native.enable_music(True)
                collect()
            if frame == 400:
                native.end()
                collect()
            if frame == 500:
                native.begin()
                collect()
            if frame < 12 or frame % 17 == 0:
                native.cue(cues[frame % len(cues)])
                collect()
            end = now + 480
            while (when := settling + ((irq + 1) * 48000 * 21845 + 1193181) // 1193182) < end:
                now = when
                native.tick()
                collect()
                irq += 1
            now = end
        native.end()
        collect()
    directory = args.research / 'installs/cd_1994_09/TFX'
    result = subprocess.run([str((args.build / 'music_session_probe').resolve()),
        str(directory / 'START.EXE'), str(directory / 'DID.DAT'), 'lapc-effects',str(args.cycles)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    actual = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    for index, (found, wanted) in enumerate(zip(actual, events)):
        assert found == wanted, (index, 'cpp', found[:28], 'original', wanted[:28])
    assert len(actual) == len(events), (len(actual), len(events))
    if args.report:
        import json
        args.report.write_text(json.dumps({'cycles':args.cycles,'events':len(events),'shared_irqs':irq,'audio_frames':now-settling,'matched':True},indent=2)+'\n')
    print(f'{args.cycles} lifecycles; {len(events)} complete LAPC effects MIDI events and sample timestamps agree through unchanged setup/cue/release wrappers, real OSL/LA playback, overlapping requests, channel exhaustion, music mute/resume and bank reuse; {irq} shared IRQ ticks')


if __name__ == '__main__':
    main()
