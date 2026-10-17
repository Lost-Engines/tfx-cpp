#!/usr/bin/env python3
"""Establish whether retail environments enable the older sprite explosions.

Executes the original environment parser, explosion-pool initializer, producer
and painter. Only archive/filesystem/time/memory delivery is supplied. Any
legacy model load or drawing request fails this check rather than being stubbed
as successful. This says nothing about non-retail environment configurations.
"""
import argparse
import json
from pathlib import Path
import struct
from native_environment import environment_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    args = parser.parse_args()
    environments = json.loads((args.research / 'analysis/lighting/environments.json').read_text())['environments']
    checked = []
    for environment in environments:
        if environment['status'] != 'decoded':
            continue
        name = environment['environment']
        image = environment_image(args.research, name)
        assert image.read(0xe774, '<H')[0] & 1, (name, 'legacy explosion path enabled')

        def unexpected(current):
            raise AssertionError((name, 'retail environment requested legacy explosion resources/drawing'))

        image.intercept(0xc93bc, 'Fail on any actual legacy model load; none is expected in this environment.', unexpected)
        image.intercept(0xc5507, 'Fail on any actual legacy drawing request; none is expected in this environment.', unexpected)
        image.call(0x74f44)
        free = image.read(0x10c90, '<I')[0]
        assert free and image.read(0x10d20, '<I') == image.read(0x10d28, '<I') == (0,), name
        image.cpu.mem_map(0x600000, 4096)
        for height in (-1000, -10, -1, 0, 100):
            image.cpu.mem_write(0x600000, struct.pack('<3i', 1000, height, 2000))
            image.call(0x75030, eax=0x600000)
            image.call(0x74fc0)
            assert image.read(0x10c90, '<I')[0] == free, name
            assert image.read(0x10d20, '<I') == image.read(0x10d28, '<I') == (0,), name
        checked.append(name)

    source = (args.research / 'analysis/models/data.js').read_text()
    models = json.loads(source.split('=', 1)[1].strip().removesuffix(';'))['models']
    sprites = [model for model in models if any(opcode == 31 for _, opcode, _ in model['instructions'])]
    names = sorted(model['name'] for model in sprites)
    assert names == ['explode', 'explode2'], names
    assert len(checked) == 33, checked
    missions = json.loads((args.research / 'analysis/missions/data.json').read_text())['missions']
    retail = [mission for mission in missions if mission['category'] != 'retained']
    assert len(retail) == 128
    assert {mission['environment'] for mission in retail} <= set(checked)
    print(f'{len(checked)} original environments covering all {len(retail)} retail missions disable the legacy explosion initializer/producer/painter; only {", ".join(names)} contain sprite opcode 31')


if __name__ == '__main__':
    main()
