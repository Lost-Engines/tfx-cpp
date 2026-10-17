#!/usr/bin/env python3
"""Compare complete original/C++ launch sessions across the retail missions.

Uses the checked research catalogue to select actual retail scripts. Native
captures execute real launch and frame loops with declared neutral device and
timer inputs. Every retained state field and every indexed pixel is checked;
this is separate from long C++-only simulation smoke tests.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def dataset(path):
    source = path.read_text()
    return json.loads(source[source.index('=') + 1:].strip().removesuffix(';'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--build', type=Path, default=Path('build'))
    p.add_argument('--output', type=Path, required=True, help='retain cases and logs in a new directory')
    p.add_argument('--frames', type=int, default=16)
    p.add_argument('--flight-model', choices=('arcade', 'simple', 'military-spec', 'realistic'), default='arcade')
    p.add_argument('--missions', help='comma-separated retail mission numbers (default: all 128)')
    p.add_argument('--capture-only', action='store_true', help='collect original sessions before a C++ build is ready')
    p.add_argument('--native-root', type=Path, help='reuse cases from this previous capture-only output')
    a = p.parse_args()
    if not 1 <= a.frames <= 256:
        p.error('--frames must be between 1 and 256')
    research = a.research.resolve()
    world = dataset(research / 'analysis/maps/data.js')
    metadata = dataset(research / 'analysis/missions/data.js')
    ids = {m['id'] for m in metadata['missions'] if m['category'] != 'retained'}
    missions = sorted(int(m['name'].removeprefix('miss')) for m in world['missions'] if m['id'] in ids)
    assert len(missions) == 128
    if a.missions:
        chosen = {int(value) for value in a.missions.split(',')}
        if not chosen <= set(missions):
            p.error('unknown retail missions: ' + ', '.join(map(str, sorted(chosen - set(missions)))))
        missions = [mission for mission in missions if mission in chosen]
    root = a.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    tools = Path(__file__).resolve().parent
    results = []
    for ordinal, mission in enumerate(missions, 1):
        case = root / str(mission)
        log = root / f'{mission}.log'
        if a.capture_only:
            command = [sys.executable, '-B', str(tools / 'capture_native_flight.py'),
                       '--research', str(research), '--output', str(case)]
        else:
            command = [sys.executable, '-B', str(tools / 'check_flight_session.py'),
                       '--research', str(research), '--build', str(a.build.resolve()),
                       '--output', str(case), '--strict-pixels']
            if a.native_root:
                command.extend(['--native-capture', str((a.native_root / str(mission)).resolve())])
        command.extend(['--mission', str(mission), '--frames', str(a.frames), '--flight-model', a.flight_model])
        with log.open('w') as target:
            result = subprocess.run(command, stdout=target, stderr=subprocess.STDOUT)
        results.append({'mission': mission, 'passed': result.returncode == 0, 'log': log.name})
        (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f"{ordinal}/{len(missions)} mission {mission}: {'passed' if result.returncode == 0 else 'FAILED'}", flush=True)
        if result.returncode:
            print(log.read_text()[-2500:], flush=True)
    failures = [result['mission'] for result in results if not result['passed']]
    print(f"{len(results) - len(failures)}/{len(results)} {'original captures' if a.capture_only else 'complete original/C++ sessions'} passed; failures: {failures}", flush=True)
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
