#!/usr/bin/env python3
"""Compare carried-store effects with the original x87 accumulator, bit for bit.

All 27 original store records, three aircraft and ten mount slots are covered,
plus mixed loadouts with fractional mounts. This checks the isolated store
contribution, not a complete aerodynamic update or flight trajectory.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference


OUTPUTS = [0x14358, 0x142a0, 0x14350, 0x13d08, 0x142d0, 0x142d8, 0x14770]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--inventory',action='store_true',help='also check current weapon-ID/quantity to flight-loadout binding')
    args = parser.parse_args()
    if args.inventory and args.record:parser.error('inventory binding checks do not use the direct-accumulator fixture format')
    image = NativeReference(args.data_dir / 'TFX.DAT')
    image.call(0xde851)
    generator = random.Random(0x95dc8)
    requests, cases = [], []
    for aircraft, preset in enumerate((0x98234, 0x97598, 0x96918), 1):
        image.call(preset)
        mounts = [list(image.read(offset, '<10d')) for offset in (0x13bd0, 0x13c20, 0x13c70)]
        selections = [[]] + [[(slot, weapon)] for slot in range(10) for weapon in range(27)]
        selections += [[(slot, generator.randrange(27)) for slot in range(10) if generator.randrange(3)] for case in range(128)]
        for case, selection in enumerate(selections):
            image.write(0x11b2a, '<H', aircraft - 1)
            image.cpu.mem_write(image.data + 0x13374, bytes(20))
            bases = [1000., 2000., 100.]
            if case >= 271:
                bases = [generator.uniform(0, 10000) for _ in range(3)]
            for offset, value in zip((0x142c8, 0x14258, 0x14850), bases):
                image.write(offset, '<d', value)
            stores = [];inventory=[]
            selected = dict(selection)
            for slot in range(10):
                position = [axis[slot] for axis in mounts] if case < 271 else [generator.uniform(-30, 30) for _ in range(3)]
                for offset, value in zip((0x13bd0, 0x13c20, 0x13c70), position):
                    image.write(offset + slot * 8, '<d', value)
                weapon = selected.get(slot, 0)
                record = 0x809c + weapon * 48
                mass = image.read(record + 31, '<h')[0]
                drag = image.read(record + 44, '<I')[0]
                tank = int(image.read(record + 20, '<B')[0] == 6)
                occupied = int(slot in selected)
                image.write(0x13374 + slot * 2, '<2B', weapon, occupied)
                stores.extend([*position, mass, drag, tank, occupied])
                inventory.extend([*position,weapon,occupied])
            image.call(0x95dc8)
            expected = [image.read(offset, '<Q')[0] for offset in OUTPUTS] + [image.read(0x14968, '<H')[0]]
            source = [aircraft, *bases, *(inventory if args.inventory else stores)]
            requests.append(' '.join(map(str, source)))
            cases.append({'input': source, 'expected': expected})
    command=[str((args.build / 'stores_probe').resolve())]+(['--inventory',str(args.data_dir.resolve())]if args.inventory else [])
    result = subprocess.run(command, input='\n'.join(requests) + '\n', text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(cases)
    for index, (case, line) in enumerate(zip(cases, lines)):
        observed = list(map(int, line.split()))
        if observed != case['expected']:
            raise AssertionError((index, case, observed))
    if args.record:
        args.record.write_text(json.dumps({'scope': __doc__, 'x87_control_word': '0x127f (executed original detection/reset)', 'intercepted_dependencies': [], 'cases': cases}, separators=(',', ':')) + '\n')
    print(f'{len(cases)} native/C++ loadouts passed bit for bit: all 27 stores, 3 aircraft, 10 slots and fractional mixed-load moments')


if __name__ == '__main__':
    main()
