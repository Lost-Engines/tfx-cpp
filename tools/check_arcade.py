#!/usr/bin/env python3
"""Compare Arcade flight sequences to the relocated September 1994 executable.

Native player initialisation, attitude, throttle, fuel and flight run unmodified.
Only host mouse acquisition and scene/audio notifications are intercepted.
The x87 control word is the harness's controlled 0x037f, not a DOS startup capture.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess

from native_reference import NativeReference, r

FLOAT_FIELDS = (0x13480, 0x13484, 0x13488, 0x87a0, 0x87a4, 0x8798, 0x879c, 0x86f4, 0x133f8, 0x133bc, 0x133b8, 0x133cc, 0x133e8, 0x133d8, 0x133c0)
NAMES = ['x', 'y', 'z', 'int_x', 'int_y', 'int_z'] + [f'basis{i}' for i in range(9)] + ['pitch_remainder', 'heading_remainder', 'roll_remainder', 'pitch_target', 'roll_target', 'pitch_filtered', 'roll_filtered', 'speed', 'throttle', 'minimum', 'maximum', 'target_speed', 'metres_per_second', 'altitude', 'movement'] + ['unrounded_speed', 'fixed_speed', 'landed', 'moving_ground', 'collision', 'recovering', 'afterburner', 'fuel_readout', 'fuel', 'fuel_flow', 'pitch', 'heading', 'roll']


def capture(aircraft, position, angles, speed, controls, warp=False):
    image = NativeReference(DATA / 'TFX.DAT')
    image.intercept(0x744e4, 'Host mouse initialisation; report no DOS mouse driver', lambda im: (im.cpu.reg_write(r.UC_X86_REG_EAX, 0), im.return_from()))
    image.intercept(0x74614, 'Host mouse range/position reset has no flight-state effect', lambda im: im.return_from())
    image.intercept(0x74508, 'Mouse samples supplied explicitly before each flight step', lambda im: im.return_from())
    image.intercept(0xb52d4, 'Scenery engine event notification; no callback modifies player physics', lambda im: im.return_from())
    image.intercept(0xa4edc, 'Sound event output outside this flight-only capture', lambda im: im.return_from())
    image.intercept(0xa6068, 'HUD message output outside this flight-only capture', lambda im: im.return_from())
    for address, value in zip((0x13424, 0x13430, 0x1343c), position):
        image.write(address, '<i', value)
    image.write(0x86c8, '<3H', *angles)
    image.write(0x86f4, '<f', speed)
    image.write(0x11b2a, '<H', aircraft - 1)
    image.write(0x1347a, '<B', 0)
    image.write(0x11b3c, '<B', 0)
    image.call(0x8c184, limit=2000000)
    image.call(0x8c318)
    image.write(0xe780, '<B', int(warp))
    expected = []
    previous_buttons = 0
    for ticks, pitch, roll, buttons, accelerate, decelerate in controls:
        image.write(0x13476, '<H', ticks)
        image.write(0x10bf2, '<h', pitch)
        image.write(0x10bf0, '<h', roll)
        image.write(0x5968, '<H', buttons)
        image.write(0x596a, '<H', previous_buttons)
        image.write(0x1325a, '<B', accelerate)
        image.write(0x13260, '<B', decelerate)
        # The normal outer player callback refreshes engine display flags.
        for engine, visual in ((0x14880, 0x7d72), (0x14888, 0x7d75)):
            image.write(visual, '<B', 1 if image.read(engine, '<d')[0] else 2)
        image.call(0x8dc50, limit=2000000)
        previous_buttons = buttons
        row = [image.read(a, '<I')[0] for a in (0x1341c, 0x13428, 0x13434)]
        row += [image.read(a, '<i')[0] for a in (0x13424, 0x13430, 0x1343c)]
        row += list(image.read(0x1345e, '<9h'))
        row += [image.read(a, '<I')[0] for a in FLOAT_FIELDS]
        row += [image.read(0x14778, '<Q')[0]]
        row += [image.read(0x13444, '<i')[0]]
        row += [image.read(a, '<h')[0] for a in (0x8d3a, 0x8d38, 0x12c04, 0x13474)]
        row += [image.read(0x1496d, '<B')[0], image.read(0x6c3c, '<h')[0]]
        row += [image.read(a, '<Q')[0] for a in (0x14858, 0x14308)]
        row += list(image.read(0x86c8, '<3H'))
        expected.append(row)
    return expected


def main():
    global DATA
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--save-fixture', type=Path)
    args = parser.parse_args()
    DATA = args.data_dir
    generator = random.Random(0x8dc50)
    cases = []
    for aircraft in (1, 2, 3):
        for speed, altitude in ((0.65, -800), (0.1, -400), (1.1, -5000), (0.8, -9500)):
            controls = [(generator.randrange(2, 19), generator.randrange(-8, 9), generator.randrange(-8, 9), 0, int(i < 80), int(150 <= i < 210)) for i in range(256)]
            cases.append((aircraft, (293888, altitude, 236544), (0, 32767, 0), speed, controls))
        controls = [(4, 0, 0, (i % 4 == 0) + 2 * (i % 4 == 2), int(i < 100), 0) for i in range(512)]
        cases.append((aircraft, (293888, -800, 236544), (0, 32767, 0), 0.65, controls))
    inputs, expected, origins, fixture = [], [], [], []
    for case_index, (aircraft, position, angles, speed, controls) in enumerate(cases):
        inputs.append(' '.join(map(str, (aircraft, len(controls), *position, *angles, speed))))
        inputs += [' '.join(map(str, control)) for control in controls]
        native = capture(aircraft, position, angles, speed, controls)
        expected += native
        fixture += inputs[-len(controls)-1:]
        digest = 14695981039346656037
        for byte in ''.join(''.join(f'{word} ' for word in row) + '\n' for row in native).encode('ascii'):
            digest = ((digest ^ byte) * 1099511628211) & ((1 << 64) - 1)
        fixture.append(str(digest))
        origins += [(case_index, frame) for frame in range(len(controls))]
    result = subprocess.run([str((args.build / 'arcade_probe').resolve())], input='\n'.join(inputs) + '\n', capture_output=True, text=True, check=True)
    observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    assert len(observed) == len(expected), (len(observed), len(expected))
    for row, (actual, wanted) in enumerate(zip(observed, expected)):
        differences = [(NAMES[i], a, b) for i, (a, b) in enumerate(zip(actual, wanted)) if a != b]
        assert not differences, (origins[row], differences)
    if args.save_fixture:
        args.save_fixture.write_text('\n'.join(fixture) + '\n')
    print(f'{len(expected)} native Arcade flight steps match exactly across all three player aircraft')


if __name__ == '__main__':
    main()
