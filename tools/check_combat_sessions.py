#!/usr/bin/env python3
"""Compare controlled combat inputs through complete original/C++ flight frames.

Only keyboard events, held keys and external timer samples are supplied.
Targets, locks, projectiles, damage, scores and completion state are reached
through the real game loops. Original resources stay outside the repository.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


CASES = {
    'training-result': (501, 'arcade', 256, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    'ejection-result': (501, 'arcade', 128, [
        {'frame': 1, 'event': 'escape'},
        {'frame': 3, 'event': 'escape'},
        {'frame': 65, 'event': 'escape'},
    ]),
    'ejection-recording': (501, 'arcade', 68, [
        {'frame': 1, 'event': 'v', 'held': ['alt', 'v']},
        {'frame': 3, 'event': 'escape'},
        {'frame': 5, 'event': 'escape'},
        {'frame': 67, 'event': 'v', 'held': ['alt', 'v']},
    ]),
    'training-intercept': (501, 'arcade', 220, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    'ground-designation': (507, 'arcade', 96, [
        {'frame': 1, 'event': 'o'},
        {'frame': 3, 'event': 'z'},
        {'frame': 5, 'event': 'period'},
        {'frame': 7, 'event': 'space'},
        {'frame': 9, 'event': 'x'},
        {'frame': 33, 'event': 'o'},
        {'frame': 35, 'event': 'space'},
    ]),
    'ground-bomb': (502, 'arcade', 256, [
        {'frame': 1, 'event': 't'},
        {'frame': 3, 'event': 'o'},
        {'frame': 5, 'event': 'z'},
        {'frame': 7, 'event': 'z'},
        {'frame': 9, 'event': 'f1'},
        {'frame': 70, 'event': 'space'},
    ]),
    'held-cannon': (501, 'arcade', 32, [
        {'frame': 1, 'event': 'f'},
        {'frame': 3, 'event': 'space'},
        {'frame': 4, 'held': ['space']},
        {'frame': 5, 'held': ['space']},
        {'frame': 6, 'held': ['space']},
        {'frame': 9, 'event': 'space'},
        {'frame': 11, 'event': 'space'},
    ]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--case', choices=CASES)
    parser.add_argument('--output', type=Path, help='retain captures in a new directory')
    parser.add_argument('--native-root', type=Path, help='reuse matching prior case/native captures')
    parser.add_argument('--capture-only', action='store_true', help='execute only the original game')
    args = parser.parse_args()
    if args.capture_only and args.native_root:
        parser.error('--capture-only cannot reuse a native capture')
    harness = Path(__file__).resolve().with_name('check_flight_session.py')
    with tempfile.TemporaryDirectory(prefix='tfx-combat-sessions-') as temporary:
        root = args.output.resolve() if args.output else Path(temporary)
        if args.output:
            root.mkdir(parents=True, exist_ok=False)
        for name in ([args.case] if args.case else CASES):
            mission, model, frames, inputs = CASES[name]
            tape = root / f'{name}.json'
            tape.write_text(json.dumps(inputs, indent=2) + '\n')
            command = [
                sys.executable, '-B', str(harness),
                '--research', str(args.research.resolve()),
                '--build', str(args.build.resolve()),
                '--mission', str(mission), '--flight-model', model,
                '--frames', str(frames), '--inputs', str(tape),
                '--strict-pixels', '--output', str(root / name),
            ]
            if args.capture_only:
                command = [sys.executable, '-B', str(harness.with_name('capture_native_flight.py')),
                           '--research', str(args.research.resolve()), '--mission', str(mission),
                           '--flight-model', model, '--frames', str(frames), '--inputs', str(tape),
                           '--output', str(root / name / 'native')]
            elif args.native_root:
                command.extend(['--native-capture', str((args.native_root / name / 'native').resolve())])
            if name.endswith('-result'):
                command.append('--until-result')
            subprocess.run(command, check=True)
            native = args.native_root / name / 'native' if args.native_root else root / name / 'native'
            capture = json.loads((native / 'session.json').read_text())
            snapshots = capture['snapshots']
            if name.endswith('-result'):
                assert capture['terminal']['returned'], 'original mission did not return through its result'
                assert snapshots[-1]['mission_progress']['ended'], 'flight ended without the mission result gate'
            if name in ('training-intercept', 'training-result'):
                assert any(s['projectiles'] for s in snapshots), 'intercept never released a store'
                assert any(s['mission_progress']['results'][3] for s in snapshots), 'intercept never downed the enemy'
                assert any(s['mission_progress']['results'][5] for s in snapshots), 'intercept never completed its objective'
            elif name == 'ground-designation':
                weapons = {shot[1] for s in snapshots for shot in s['projectiles']}
                assert {0, 21} <= weapons, 'ground sequence never fired its cannon and Sidearm'
            elif name == 'ground-bomb':
                assert any(shot[1] == 12 for s in snapshots for shot in s['projectiles']), 'ground sequence never released its GBU-12'
                assert any(shot[1] == 12 and shot[6] > -2048 for s in snapshots for shot in s['projectiles']), 'bomb never approached ground contact'
                assert not snapshots[-1]['projectiles'], 'ground sequence ended before bomb retirement'
            elif name == 'held-cannon':
                assert snapshots[2]['cannon'][0] - snapshots[3]['cannon'][0] == 20, 'initial press did not reach both cannon dispatches'
                assert snapshots[3]['cannon'][0] - snapshots[4]['cannon'][0] == 10, 'held poll did not continue firing'
                assert snapshots[6]['cannon'] == snapshots[7]['cannon'], 'released trigger kept firing'


if __name__ == '__main__':
    main()
