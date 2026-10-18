#!/usr/bin/env python3
"""Compare a complete original/C++ refuelling connection and fuel transfer.

A clearly test-authored loose mission reuses the unmodified miss500 tanker
routes. Both executables load that source normally. Ordinary throttle keys
establish a safe separation, then apostrophe engages and disengages refuelling.
No pose, controller phase, fuel amount or successful outcome is assigned.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


INPUTS = [
    {'frame': 1, 'event': 'minus'},
    *({'frame': frame, 'held': ['minus']} for frame in range(2, 27)),
    {'frame': 65, 'event': 'apostrophe', 'held': ['apostrophe', 'equal']},
    {'frame': 66, 'held': ['equal']},
    {'frame': 241, 'event': 'apostrophe'},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--output', type=Path, help='retain captures in a new directory')
    parser.add_argument('--native-capture', type=Path, help='reuse a matching original capture')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='tfx-refuelling-session-') as temporary:
        root = args.output.resolve() if args.output else Path(temporary)
        if args.output:
            root.mkdir(parents=True, exist_ok=False)
        tape = root / 'inputs.json'
        tape.write_text(json.dumps(INPUTS, indent=2) + '\n')
        tools = Path(__file__).resolve().parent
        command = [sys.executable, '-B', str(tools / 'check_flight_session.py'),
                   '--research', str(args.research.resolve()), '--build', str(args.build.resolve()),
                   '--mission', '1999', '--mission-file', str(tools.parent / 'tests/scenarios/refuelling.mis'),
                   '--flight-model', 'arcade', '--frames', '256', '--inputs', str(tape),
                   '--strict-pixels', '--output', str(root / 'session')]
        if args.native_capture:
            command += ['--native-capture', str(args.native_capture.resolve())]
        subprocess.run(command, check=True)
        native = args.native_capture or root / 'session/native'
        capture = json.loads((native / 'session.json').read_text())
        snapshots = capture['snapshots']
        assert capture['test_mission_sha256'], 'test-authored source must be explicitly identified'
        connected = [snapshot['frame'] for snapshot in snapshots if snapshot['refuelling'][2] == 3]
        assert len(connected) >= 32, ('no sustained original refuelling connection', connected)
        fuel = [struct.unpack('<d', struct.pack('<Q', snapshot['armament'][-1]))[0] for snapshot in snapshots]
        first = connected[0]
        assert fuel[first + 1] > fuel[first] + 1, 'connected fuel transfer did not replenish consumed fuel'
        assert all(snapshot['refuelling'][0] == 0 and snapshot['refuelling'][2] == 0
                   for snapshot in snapshots[241:]), 'ordinary toggle did not disconnect the tanker'
        assert fuel[-1] < fuel[241], 'fuel continued to replenish after disengagement'
        print('Complete approach, sustained coupling, fuel transfer and ordinary disengagement verified')


if __name__ == '__main__':
    main()
