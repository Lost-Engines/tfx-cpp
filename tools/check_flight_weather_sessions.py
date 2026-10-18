#!/usr/bin/env python3
"""Compare storm flight and real configuration-to-flight weather changes.

Supplies saved REALISM bytes, ordinary keys, modal mouse clicks and timer
samples. Wind state, aircraft trajectories, rain and palettes are original
outputs; neither flight implementation receives an assigned weather outcome.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


CASES = {
    'storm': [],
    'live-wind': [
        {'frame': 3, 'event': 'grave', 'configuration': [[228, 172], [128, 124], [152, 172]]},
        {'frame': 35, 'event': 'grave', 'configuration': [[228, 172], [104, 124], [152, 172]]},
        {'frame': 67, 'event': 'grave', 'configuration': [[228, 172], [128, 124], [152, 172]]},
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--x87-backend', type=Path, default=Path('build'), help='hardware reference adapter build; may differ from the tested sanitizer build')
    parser.add_argument('--case', choices=CASES, default='live-wind')
    parser.add_argument('--flight-model', choices=('realistic', 'military-spec'), default='realistic')
    parser.add_argument('--output', type=Path, help='retain captures in a new directory')
    parser.add_argument('--native-capture', type=Path, help='reuse a matching original capture')
    args = parser.parse_args()
    frames = 96 if args.case == 'live-wind' else 64
    with tempfile.TemporaryDirectory(prefix='tfx-weather-session-') as temporary:
        root = args.output.resolve() if args.output else Path(temporary)
        if args.output:
            root.mkdir(parents=True, exist_ok=False)
        tape = root / 'inputs.json'
        tape.write_text(json.dumps(CASES[args.case], indent=2) + '\n')
        command = [sys.executable, '-B', str(Path(__file__).with_name('check_flight_session.py')),
                   '--research', str(args.research.resolve()), '--build', str(args.build.resolve()),
                   '--mission', '507', '--flight-model', args.flight_model,
                   '--realism', '0,1,1,1,1,1,1', '--x87-backend', str(args.x87_backend.resolve()),
                   '--frames', str(frames), '--inputs', str(tape), '--strict-pixels',
                   '--output', str(root / 'session')]
        if args.native_capture:
            command += ['--native-capture', str(args.native_capture.resolve())]
        subprocess.run(command, check=True)
        native = args.native_capture or root / 'session/native'
        capture = json.loads((native / 'session.json').read_text())
        snapshots = capture['snapshots']
        assert snapshots[0]['realism_state'][4] == 0, 'launch did not apply the original wind reset'
        assert len(capture['precipitation_events']) == frames, 'the storm did not produce rain throughout the flight'
        if args.case == 'live-wind':
            for first, last, enabled in ((1, 2, 0), (3, 34, 1), (35, 66, 0), (67, 96, 1)):
                assert all(snapshot['realism_state'][4] == enabled for snapshot in snapshots[first:last + 1]), ('wind menu state', first, last, enabled)
            assert len(capture['configuration_events']) == 3, 'not all configuration dialogs completed'
            assert any(snapshot['aerodynamic_wind'][-3:] != [0, 0, 0] for snapshot in snapshots[3:35]), 'enabled wind never produced a velocity'
        else:
            assert not any(snapshot['realism_state'][4] for snapshot in snapshots), 'saved wind flag unexpectedly survived initialization'


if __name__ == '__main__':
    main()
