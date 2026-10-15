#!/usr/bin/env python3
"""Execute original retail FINISH scripts with declared combat/target outcomes.

This covers native parsing, condition evaluation, assignments, return handling
and common campaign statistics. Combat outcomes and saved-start persistence are
supplied boundaries; these cases do not claim to simulate a combat engagement.
"""
import argparse
import json
from pathlib import Path
import subprocess

from unicorn import x86_const as r
from check_initialisation import InitialisationCapture, dataset

KEYS = ['a2akills', 'a2gkills', 'num_miss', 'num_hours', 'miss_val', 'score', 'fmobile_down']
BUILTINS = [0x5c14, 0x5c18, 0x5c1c, 0x5c24, 0x5c28, 0x5c30, 0x5c20, 0x5c2c, 0x5c34, 0x5c38]


class ResultCapture:
    def __init__(self, executable, source):
        self.capture = InitialisationCapture(executable, source, [0, 0, 0, 0x3f800000, 0])
        self.capture.run()
        self.image = self.capture.image
        self.image.intercept(0xa4a9c, 'saved-start persistence omitted; no installation writes in capture', lambda image: image.return_from())
        self.image.intercept(0xc8568, 'resolve supplied synthetic target records; original destroyed-flag reader executes', self.target)
        self.alive_mask = 0
        self.image.write(0x1afee, '<H', len(KEYS))
        for index, name in enumerate(KEYS):
            self.image.cpu.mem_write(self.image.data + 0x1ad62 + index * 21, name.encode() + b'\0')
        self.target_queries = []

    def target(self, image):
        handle = image.cpu.reg_read(r.UC_X86_REG_EAX)
        if not 1 <= handle <= 9:
            raise RuntimeError(f'undeclared target handle: {handle}')
        self.target_queries.append(handle)
        address = 0x320000 + handle * 32
        image.cpu.mem_write(address + 2, bytes([0 if self.alive_mask & (1 << (handle - 1)) else 0x10]))
        image.cpu.reg_write(r.UC_X86_REG_EAX, address)
        image.return_from()

    def run(self, state, variables):
        self.target_queries.clear()
        for offset, value in zip(BUILTINS, state[:10]):
            self.image.write(offset, '<i', value)
        self.image.write(0x11b26, '<H', state[10] & 65535)
        self.alive_mask = state[11]
        for index in range(9):
            self.image.write(0x5c4c + index * 26, '<H', index + 1)
        for index, value in enumerate(variables):
            self.image.write(0x1a400 + index * 4, '<i', value)
        self.image.call(0x7ae80, limit=2000000)
        return [self.image.read(0x1a400 + index * 4, '<i')[0] for index in range(len(KEYS))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--research', type=Path, required=True)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    data = args.research / 'installs/cd_1994_09/TFX'
    missions = sorted((m for m in dataset(args.research / 'analysis/missions/data.js')['missions'] if m['category'] != 'retained'), key=lambda m: m['name'])
    catalog = {e['identifier']: e for e in json.loads((args.research / 'analysis/resources/catalog.json').read_text())['entries']}
    cases, requests = [], []
    for mission in missions:
        source = (args.research / 'extracted/cd_1994_09/resources' / catalog[mission['id']]['path']).read_bytes()
        capture = ResultCapture(data / 'TFX.DAT', source)
        for index in range(64):
            down = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 32767, 32768, 65535, 65536, -1][index % 16]
            alive = [0, 1, 2, 3, 4, 5, 6, 7, 255, 0x155][(index % 16 + (index // 16) * 3) % 10]
            state = [(-100 if index % 3 == 0 else 12345), 22, 33, down, (index // 32) % 2, (index // 16) % 2, index % 9, index % 3, index % 4, index % 5, index % 3, alive]
            variables = [10, 20, 30, 40, index % 3, 2147480000 if index % 3 == 1 else -1000, index % 2]
            expected = capture.run(state, variables)
            cases.append({'mission': mission['name'], 'state': state, 'variables': variables, 'expected': expected})
            requests.append(' '.join(map(str, [mission['name'], *state, *variables])))
    result = subprocess.run([str((args.build / 'rules_probe').resolve()), str(data)], input='\n'.join(requests) + '\n', text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    lines = result.stdout.splitlines()
    assert len(lines) == len(cases)
    differences = []
    for case, line in zip(cases, lines):
        observed = json.loads(line)
        if observed != case['expected']:
            differences.append((case, observed))
    if args.record:
        args.record.write_text(json.dumps({'scope': __doc__, 'dependencies': {hex(k): v for k, v in capture.image.dependencies.items()}, 'variable_order': KEYS, 'cases': cases}, separators=(',', ':')) + '\n')
    if differences:
        from collections import Counter
        raise AssertionError((Counter(case['mission'] for case, observed in differences), differences[:3]))
    print(f'{len(cases)} native/C++ retail mission results passed: scoring, target predicates, signed comparisons, branches and campaign handoff')


if __name__ == '__main__':
    main()
