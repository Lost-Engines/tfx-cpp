#!/usr/bin/env python3
"""Compare every replay pixel and the IR palette with the original REC player.

The original reads its own actual flight recording, or a supplied C++ REC.
Only DOS file I/O, video hardware and the retained final-flight context are
hosted. Animation prefaces and real-time waiting have separate coverage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from check_recording_session import CASES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--build', type=Path, default=Path('build'))
    p.add_argument('--case', choices=CASES, default='camera')
    p.add_argument('--output', type=Path, help='retain the comparison in a new directory')
    p.add_argument('--native-capture', type=Path, help='reuse a matching original replay capture')
    p.add_argument('--recording', type=Path, help='check an independently written REC through both readers')
    a = p.parse_args()
    tools = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='tfx-recording-playback-') as temporary:
        root = a.output.resolve() if a.output else Path(temporary)
        if a.output:
            root.mkdir(parents=True, exist_ok=False)
        native = a.native_capture.resolve() if a.native_capture else root / 'native'
        if not a.native_capture:
            subprocess.run([
                sys.executable, '-B', str(tools / 'capture_recording_playback.py'),
                '--research', str(a.research.resolve()), '--output', str(native), '--case', a.case,
                *(['--recording', str(a.recording.resolve())] if a.recording else []),
            ], check=True, timeout=300)
        context = json.loads((native / 'playback.json').read_text())
        session = json.loads((native / 'session.json').read_text())
        mission, frames, inputs = CASES[a.case]
        assert context['mission'] == session['mission'] == mission
        assert session['resource_root'] == 'TFX' and len(session['snapshots']) == frames + 1
        from flight_inputs import FlightInputs
        assert session['inputs'] == FlightInputs(inputs).rows(frames), 'native capture inputs differ'
        install = (a.research / 'installs/cd_1994_09/TFX').resolve()
        for name, key in (('TFX.DAT', 'executable_sha256'), ('DID.DAT', 'archive_sha256')):
            assert hashlib.sha256((install / name).read_bytes()).hexdigest() == session['reference'][key]
        recording = a.recording.resolve() if a.recording else Path(context['recording'])
        assert hashlib.sha256(recording.read_bytes()).hexdigest() == context['recording_sha256'], 'recording differs'
        target = root / 'cpp'
        subprocess.run([
            str((a.build / 'recording_playback_probe').resolve()), str(install), str(recording), str(target),
        ], input=(native / 'context.txt').read_bytes(), check=True, timeout=120)
        assert (native / 'infrared.dac').read_bytes() == (target / 'infrared.dac').read_bytes(), 'replay palette'
        for index in range(context['frames']):
            name = f'replay-{index}.indices'
            expected, actual = (native / name).read_bytes(), (target / name).read_bytes()
            assert len(expected) == len(actual) == 64000
            different = sum(a != b for a, b in zip(expected, actual))
            assert not different, (name, different, 'different pixels')
        print(f"{context['frames']} complete original replay frames and the infrared palette agree pixel for pixel")


if __name__ == '__main__':
    main()
