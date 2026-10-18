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
    'career-carrier-landing': (1111, 'realistic', 1024, [
        {'frame': 1, 'event': 'p', 'held': ['right-shift', 'p']},
        {'frame': 3, 'event': 'l', 'held': ['right-shift', 'l']},
        {'frame': 5, 'event': 'o', 'held': ['right-shift', 'o']},
        {'frame': 7, 'event': 'p', 'held': ['right-shift', 'p']},
        {'frame': 9, 'event': 'l', 'held': ['alt', 'l']},
        {'frame': 11, 'event': 't'},
    ]),
    'career-airfield-landing': (511, 'simple', 1024, [
        {'frame': 1, 'event': 'l', 'held': ['alt', 'l']},
        {'frame': 3, 'event': 't'},
    ]),
    # The automatic selector in mission 512 chooses Columbia's runway too,
    # despite the authored instruction to land on a carrier.
    'career-raptor-runway-landing': (512, 'realistic', 1024, [
        {'frame': 1, 'event': 'l', 'held': ['alt', 'l']},
        {'frame': 3, 'event': 't'},
    ]),
    # This sea sortie has no eligible runway/deck. Keep the original refusal
    # and subsequent loss rather than calling it a successful carrier approach.
    'career-no-runway-result': (605, 'realistic', 96, [
        {'frame': 1, 'event': 'l', 'held': ['alt', 'l']},
        {'frame': 3, 'event': 't'},
    ]),
    # Open-loop mouse steering, actual PLOP key sequence and a timed AGM-88
    # release. This reaches a SAM objective and a natural return, without
    # changing position, target, damage or campaign state in either game.
    'ground-strike-result': (503, 'arcade', 384, 'ground-strike.json'),
    'crash-result': (501, 'arcade', 96, [
        {'frame': 2, 'mouse': [0, -256]},
        {'frame': 3, 'event': 't'},
    ]),
    'career-crash-result': (501, 'arcade', 96, [
        {'frame': 2, 'mouse': [0, -256]},
        {'frame': 3, 'event': 't'},
    ]),
    'career-intercept-result': (501, 'arcade', 256, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    # Escape the airspace through ordinary PLOP, time-warp and reheat keys.
    # Neither the violation counter nor the forced-return result is supplied.
    'career-airspace-result': (501, 'arcade', 1024, [
        {'frame': 1, 'event': 'p', 'held': ['right-shift', 'p']},
        {'frame': 3, 'event': 'l', 'held': ['right-shift', 'l']},
        {'frame': 5, 'event': 'o', 'held': ['right-shift', 'o']},
        {'frame': 7, 'event': 'p', 'held': ['right-shift', 'p']},
        {'frame': 9, 'event': 't'},
        {'frame': 11, 'event': 'keypad-multiply'},
        {'frame': 13, 'event': 'keypad-multiply'},
        {'frame': 15, 'event': 'keypad-multiply'},
        {'frame': 17, 'event': 'keypad-multiply'},
    ]),
    'training-result': (501, 'arcade', 256, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    'training-simple-result': (501, 'simple', 256, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    # The same launch misses in the original Military Spec model. Keep that
    # trajectory as a comparison, rather than imposing the Arcade outcome.
    'training-military': (501, 'military-spec', 384, [
        {'frame': 1, 'event': 't'},
        {'frame': 2, 'event': 'enter'},
        {'frame': 70, 'event': 'space'},
    ]),
    'training-realistic': (501, 'realistic', 384, [
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
    'ground-radiation': (503, 'arcade', 64, [
        {'frame': 1, 'event': 'o'},
        {'frame': 5, 'event': 'space'},
        {'frame': 7, 'event': 't'},
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
            if isinstance(inputs, str):
                inputs = json.loads((Path(__file__).resolve().parent.parent / 'tests/inputs' / inputs).read_text())
            ticks = 18 if name in ('ground-strike-result', 'crash-result', 'career-crash-result', 'career-airspace-result', 'career-airfield-landing', 'career-raptor-runway-landing', 'career-no-runway-result', 'career-carrier-landing') else 4
            tape = root / f'{name}.json'
            tape.write_text(json.dumps(inputs, indent=2) + '\n')
            command = [
                sys.executable, '-B', str(harness),
                '--research', str(args.research.resolve()),
                '--build', str(args.build.resolve()),
                '--mission', str(mission), '--flight-model', model,
                '--frames', str(frames), '--inputs', str(tape),
                '--ticks-per-frame', str(ticks),
                '--strict-pixels', '--output', str(root / name),
            ]
            if args.capture_only:
                command = [sys.executable, '-B', str(harness.with_name('capture_native_flight.py')),
                           '--research', str(args.research.resolve()), '--mission', str(mission),
                           '--flight-model', model, '--frames', str(frames), '--inputs', str(tape),
                           '--ticks-per-frame', str(ticks),
                           '--output', str(root / name / 'native')]
            elif args.native_root:
                command.extend(['--native-capture', str((args.native_root / name / 'native').resolve())])
            if name.startswith('career-'):
                command.append('--career-rules')
            if name == 'career-carrier-landing':
                command.append('--default-rearming')
            if name.endswith('-result'):
                command.append('--until-result')
            if name.endswith('-landing'):
                command.append('--until-landed')
            subprocess.run(command, check=True)
            native = args.native_root / name / 'native' if args.native_root else root / name / 'native'
            capture = json.loads((native / 'session.json').read_text())
            snapshots = capture['snapshots']
            if name.endswith('-result'):
                assert capture['terminal']['returned'], 'original mission did not return through its result'
                assert snapshots[-1]['mission_progress']['ended'], 'flight ended without the mission result gate'
            if name.endswith('-landing'):
                assert capture['landing_checkpoint'], 'automatic landing never stopped'
                assert any(s['automatic_landing'][0] for s in snapshots), 'landing controller never ran'
                assert snapshots[-1]['automatic_landing'][0] == 0 and capture['landing_checkpoint']['finalizer'], 'landing did not reach its finalizer and release the controller'
            if name in ('training-intercept', 'training-result', 'training-simple-result', 'career-intercept-result'):
                assert any(s['projectiles'] for s in snapshots), 'intercept never released a store'
                assert any(s['mission_progress']['results'][3] for s in snapshots), 'intercept never downed the enemy'
                assert any(s['mission_progress']['results'][5] for s in snapshots), 'intercept never completed its objective'
                if name == 'career-intercept-result':
                    assert snapshots[0]['armament'][7] == 1 and snapshots[70]['armament'][7] == 0, 'career missile was replenished'
                    assert any('PERMISSION TO FIRE' in event['message'] for event in capture['radio_events']), 'career sortie never exercised the permission notice'
            elif name in ('training-military', 'training-realistic'):
                assert any(s['projectiles'] for s in snapshots), 'advanced-model sortie never launched a weapon'
            elif name == 'ground-strike-result':
                assert any(shot[1] == 20 for s in snapshots for shot in s['projectiles']), 'strike never released its AGM-88'
                assert snapshots[-1]['mission_progress']['credited_targets'] == 1, 'strike never credited its bound objective'
                assert capture['terminal']['campaign']['a2gkills'] >= 1, 'strike never reached a ground kill'
            elif name in ('crash-result', 'career-crash-result'):
                assert capture['terminal']['campaign']['status'] == 4, 'crash did not report the aircraft lost'
                assert capture['terminal']['campaign']['outcome'] == 1, 'crash did not reach the failure outcome'
            elif name == 'career-airspace-result':
                assert snapshots[-1]['mission_progress']['violations'] > 0, 'airspace departure never violated orders'
                assert capture['terminal']['campaign']['status'] == 2, 'departure did not report orders violated'
                assert capture['terminal']['campaign']['outcome'] == 2, 'departure did not reach the court-martial outcome'
            elif name == 'career-no-runway-result':
                assert any(event['message'] == 'NO RUNWAYS TO LAND ON' for event in capture['radio_events']), 'sortie did not refuse an unavailable approach'
                assert capture['terminal']['campaign']['status'] == 4, 'sortie did not reach its natural aircraft-loss result'
            elif name == 'ground-designation':
                weapons = {shot[1] for s in snapshots for shot in s['projectiles']}
                assert {0, 21} <= weapons, 'ground sequence never fired its cannon and Sidearm'
            elif name == 'ground-bomb':
                assert any(shot[1] == 12 for s in snapshots for shot in s['projectiles']), 'ground sequence never released its GBU-12'
                assert any(shot[1] == 12 and shot[6] > -2048 for s in snapshots for shot in s['projectiles']), 'bomb never approached ground contact'
                assert not snapshots[-1]['projectiles'], 'ground sequence ended before bomb retirement'
            elif name == 'ground-radiation':
                assert any(shot[1] == 20 for s in snapshots for shot in s['projectiles']), 'anti-radiation sequence never released its AGM-88'
                assert any(event['weapon'] == 20 and event['target'][1] == 0 for event in capture['projectile_guidance']), 'anti-radiation weapon never followed a ground point'
                assert not snapshots[-1]['projectiles'], 'anti-radiation sequence ended before retirement'
            elif name == 'held-cannon':
                assert snapshots[2]['cannon'][0] - snapshots[3]['cannon'][0] == 20, 'initial press did not reach both cannon dispatches'
                assert snapshots[3]['cannon'][0] - snapshots[4]['cannon'][0] == 10, 'held poll did not continue firing'
                assert snapshots[6]['cannon'] == snapshots[7]['cannon'], 'released trigger kept firing'


if __name__ == '__main__':
    main()
