#!/usr/bin/env python3
"""Compare original/C++ targeting controls through complete flight frames.

Uses the ordinary complete-session harness, original assets and a private
silent window. Only declared key events, held keys and timer inputs are
supplied; no target, camera, flight or outcome state is injected.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


CASES = {
    'search': (601, 'arcade', 16, [
        {'frame': 1, 'event': 'o'},
        {'frame': 3, 'event': 'z'},
        {'frame': 5, 'event': 'period'},
        {'frame': 7, 'event': 'z'},
        {'frame': 9, 'event': 'x'},
        {'frame': 11, 'event': 'f1'},
        {'frame': 13, 'event': 'z'},
    ]),
    'held': (601, 'realistic', 22, [
        {'frame': 1, 'event': 'o'},
        {'frame': 3, 'event': 'z', 'held': ['z', 'up']},
        {'frame': 4, 'held': ['down', 'right']},
        {'frame': 5, 'event': 'period', 'held': ['period', 'down']},
        {'frame': 7, 'event': 'z'},
        {'frame': 9, 'event': 'iso-extra'},
        {'frame': 11, 'event': 'x'},
        {'frame': 13, 'event': 'f1'},
        {'frame': 15, 'event': 'z'},
        {'frame': 17, 'event': 'comma'},
        {'frame': 19, 'event': 'f1'},
        {'frame': 21, 'event': 'enter'},
    ]),
    'clear': (501, 'arcade', 8, [
        {'frame': 1, 'event': 'enter'},
        {'frame': 3, 'event': 'c'},
        {'frame': 5, 'event': 'x'},
        {'frame': 7, 'event': 'c'},
    ]),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--case', choices=CASES, help='run only one sequence')
    parser.add_argument('--output', type=Path, help='retain captures in a new directory')
    args = parser.parse_args()
    harness = Path(__file__).resolve().with_name('check_flight_session.py')
    with tempfile.TemporaryDirectory(prefix='tfx-targeting-sessions-') as temporary:
        root = args.output.resolve() if args.output else Path(temporary)
        if args.output:
            root.mkdir(parents=True, exist_ok=False)
        for name in ([args.case] if args.case else CASES):
            mission, model, frames, inputs = CASES[name]
            tape = root / f'{name}.json'
            tape.write_text(json.dumps(inputs, indent=2) + '\n')
            subprocess.run([
                sys.executable, '-B', str(harness),
                '--research', str(args.research.resolve()),
                '--build', str(args.build.resolve()),
                '--mission', str(mission), '--flight-model', model,
                '--frames', str(frames), '--inputs', str(tape),
                '--strict-pixels', '--output', str(root / name),
            ], check=True)


if __name__ == '__main__':
    main()
