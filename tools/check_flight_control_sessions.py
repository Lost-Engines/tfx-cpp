#!/usr/bin/env python3
"""Compare live flight controls and their cockpit through original/C++ frames.

Supplies keyboard and timer inputs only. The original launch, flight, guidance,
target adjustment and MFD selection execute without substituted game state.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


AUTOPILOT_INPUTS = [
    {'frame': 1, 'event': '7'},
    {'frame': 3, 'event': 'a'},
    {'frame': 5, 'event': 't'},
    {'frame': 17, 'event': '8'},
    {'frame': 19, 'event': 'up'},
    *({'frame': frame, 'held': ['up']} for frame in range(20, 23)),
    {'frame': 25, 'event': '0'},
    {'frame': 27, 'event': 'equal'},
    {'frame': 33, 'event': 'a'},
    {'frame': 35, 'event': '7'},
    {'frame': 37, 'event': 'a'},
    {'frame': 45, 'event': '9'},
    {'frame': 49, 'event': '5'},
    {'frame': 53, 'event': '6'},
    {'frame': 57, 'event': '0'},
    {'frame': 59, 'event': 'minus'},
    {'frame': 61, 'event': '8'},
    {'frame': 63, 'event': 'a'},
]

CASES = {
    'autopilot': ('realistic', 64, AUTOPILOT_INPUTS),
    'air-brake': ('arcade', 16, [{'frame': frame, 'event': 'b'} for frame in (1, 3, 5, 9, 13)]),
    'mouse': ('arcade', 32, [
        *({'frame': frame, 'mouse': [4, -2]} for frame in range(3, 13)),
        {'frame': 14, 'buttons': 1},
        {'frame': 15, 'buttons': 1},
        {'frame': 17, 'event': 't'},
        *({'frame': frame, 'mouse': [-3, 2]} for frame in range(19, 25)),
        {'frame': 25, 'event': 'f5', 'buttons': 2},
        {'frame': 26, 'buttons': 2},
        {'frame': 29, 'event': 'f1'},
    ]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--case', choices=CASES, default='autopilot')
    parser.add_argument('--flight-model', choices=('arcade', 'simple', 'military-spec', 'realistic'))
    parser.add_argument('--output', type=Path, help='retain captures in a new directory')
    parser.add_argument('--native-capture', type=Path, help='reuse a matching original capture')
    parser.add_argument('--capture-only', action='store_true')
    args = parser.parse_args()
    if args.capture_only and args.native_capture:
        parser.error('--capture-only cannot reuse an original capture')
    model, frames, inputs = CASES[args.case]
    model = args.flight_model or model
    if args.case == 'mouse' and model != 'arcade':
        parser.error('the relative mouse sequence exercises Arcade steering')
    with tempfile.TemporaryDirectory(prefix='tfx-autopilot-session-') as temporary:
        root = args.output.resolve() if args.output else Path(temporary)
        if args.output:
            root.mkdir(parents=True, exist_ok=False)
        tape = root / 'inputs.json'
        tape.write_text(json.dumps(inputs, indent=2) + '\n')
        tool = 'capture_native_flight.py' if args.capture_only else 'check_flight_session.py'
        command = [sys.executable, '-B', str(Path(__file__).with_name(tool)),
                   '--research', str(args.research.resolve()), '--mission', '501',
                   '--flight-model', model, '--frames', str(frames),
                   '--inputs', str(tape), '--output', str(root / 'session')]
        if not args.capture_only:
            command += ['--build', str(args.build.resolve()), '--strict-pixels']
        if args.native_capture:
            command += ['--native-capture', str(args.native_capture.resolve())]
        subprocess.run(command, check=True)
        native = args.native_capture or (root / 'session' if args.capture_only else root / 'session/native')
        snapshots = json.loads((native / 'session.json').read_text())['snapshots']
        if args.case == 'autopilot':
            assert snapshots[3]['autopilot_targets'][0] == 1, 'autopilot never engaged'
            assert snapshots[33]['autopilot_targets'][0] == 0, 'autopilot never disengaged'
            assert {snapshot['autopilot_targets'][1] for snapshot in snapshots} >= {0, 1, 2, 3}, 'not all ordinary modes were selected'
            assert snapshots[3]['display_selection'][0] == 8, 'engagement did not select the controls MFD'
        elif args.case == 'air-brake':
            assert snapshots[1]['air_brake'][0] != 0 and snapshots[3]['air_brake'][0] == 0, 'airbrake did not deploy and retract'
        elif args.case == 'mouse':
            assert snapshots[12]['angles'] != snapshots[2]['angles'], 'relative mouse motion did not steer the aircraft'


if __name__ == '__main__':
    main()
