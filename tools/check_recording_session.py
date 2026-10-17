#!/usr/bin/env python3
"""Compare actual Alt+V recordings and flight frames against original TFX.

Only device/timer inputs and capture-owned DOS files are supplied. Recorded
resource handles are resolved to names before comparing the complete queues.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


CASES = {
    'camera': (501, 12, [
        {'frame': 1, 'event': 'alt'},
        {'frame': 2, 'event': 'v', 'held': ['alt', 'v']},
        {'frame': 3, 'event': 'f5'},
        {'frame': 5, 'event': 'enter'},
        {'frame': 7, 'event': 'f1'},
        {'frame': 9, 'event': 'alt'},
        {'frame': 10, 'event': 'v', 'held': ['alt', 'v']},
    ]),
    'designator': (601, 16, [
        {'frame': 1, 'event': 'o'},
        {'frame': 2, 'event': 'alt'},
        {'frame': 3, 'event': 'v', 'held': ['alt', 'v']},
        {'frame': 5, 'event': 'z'},
        {'frame': 7, 'event': 'period'},
        {'frame': 9, 'event': 'z'},
        {'frame': 11, 'event': 'x'},
        {'frame': 13, 'event': 'alt'},
        {'frame': 14, 'event': 'v', 'held': ['alt', 'v']},
        {'frame': 15, 'event': 'f1'},
    ]),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--build', type=Path, default=Path('build'))
    p.add_argument('--case', choices=CASES)
    p.add_argument('--output', type=Path, help='retain captures in a new directory')
    a = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='tfx-recording-sessions-') as temporary:
        root = a.output.resolve() if a.output else Path(temporary)
        if a.output:
            root.mkdir(parents=True, exist_ok=False)
        for name in ([a.case] if a.case else CASES):
            mission, frames, inputs = CASES[name]
            tape = root / f'{name}.json'
            tape.write_text(json.dumps(inputs, indent=2) + '\n')
            subprocess.run([
                sys.executable, '-B', str(Path(__file__).resolve().with_name('check_flight_session.py')),
                '--research', str(a.research.resolve()), '--build', str(a.build.resolve()),
                '--mission', str(mission), '--frames', str(frames),
                '--inputs', str(tape), '--strict-pixels', '--output', str(root / name),
            ], check=True)


if __name__ == '__main__':
    main()
