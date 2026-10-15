#!/usr/bin/env python3
"""Compare Arcade runway/carrier starts and supplied ground contacts with native player updates.

Ground classifications and per-step contact height are explicit inputs. This
checks player contact/takeoff logic, not the still-unimplemented SSD collision query.
Automatic recovery is disabled; ordinary gear/flight handling remains active.
"""
import argparse
from pathlib import Path
import subprocess

import check_arcade as flight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--save-fixture', type=Path)
    args = parser.parse_args()
    flight.DATA = args.data_dir
    inputs, expected, origins, fixture = [], [], [], []
    for aircraft in (1, 2, 3):
        for height in (0, -20):
            for engines in (False, True):
                controls = [(4, (1 if engines and 20 <= i < 250 else 0), 0, 0, 1, 0) for i in range(768)]
                position, angles = (125952, 0, 48128), (0, 0, 0)
                case = [aircraft, len(controls), *position, *angles, 0, 1, height, int(engines)]
                trace = flight.capture(aircraft, position, angles, 0, controls, landed=True, ground=height, engines=engines)
                if engines:
                    assert trace[-1][32] == 0 and trace[-1][34] == 0, ('takeoff did not finish airborne and intact', aircraft, height, trace[-1])
                source = [' '.join(map(str, case))] + [' '.join(map(str, frame)) for frame in controls]
                inputs += source
                expected += trace
                origins += [(aircraft, height, engines, frame) for frame in range(len(controls))]
                digest = 14695981039346656037
                for byte in ''.join(' '.join(map(str, row)) + '\n' for row in trace).encode('ascii'):
                    digest = ((digest ^ byte) * 1099511628211) & ((1 << 64) - 1)
                fixture += source + [str(digest)]
    result = subprocess.run([str((args.build / 'arcade_probe').resolve()), '--ground'], input='\n'.join(inputs) + '\n', capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    assert len(observed) == len(expected)
    names = flight.NAMES + ['gear_down', 'brake_chute']
    for index, (a, b) in enumerate(zip(observed, expected)):
        assert len(a) == len(b) == len(names)
        differences = [(names[i], x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
        assert not differences, (origins[index], differences)
    if args.save_fixture:
        args.save_fixture.write_text('\n'.join(fixture) + '\n')
    print(f'{len(expected)} ground-start/takeoff steps match native player updates for all three aircraft')


if __name__ == '__main__':
    main()
