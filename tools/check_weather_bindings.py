#!/usr/bin/env python3
"""Compare authored environment parsing through original atmosphere/wind initialization.

The original parser executes with supplied resource bytes, allocation and time.
Full 0x95f3c then executes, including its own profile-zero selection and random
calls. Temperature selection is not replaced. Hardware x87 adapters retain
80-bit transcendental results where Unicorn otherwise narrows them.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from native_environment import environment_image
from native_x87 import hardware_fpatan, hardware_sine_cosine, hardware_tangent

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
p.add_argument('--build', type=Path, default=Path('build'))
a = p.parse_args()
profiles = [c['environment'] for c in json.loads((a.research / 'analysis/lighting/environments.json').read_text())['environments'] if c['status'] == 'decoded']
rng = random.Random(0x95f3c)
rows = [[name, enabled, rng.randrange(65536), rng.randrange(65536)] for name in profiles for enabled in (0, 1) for repeat in range(16)]
output = subprocess.check_output([str((a.build / 'weather_probe').resolve()), str(a.research / 'installs/cd_1994_09/TFX')], input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
assert len(output) == len(rows) + 1
fields = [0x13b60,0x14288,0x13ba0,0x8e28,0x8e30,0x13b58,0x13b50,0x13bc8,0x13cc0,0x13b80,0x13cd0,0x13b70,0x13b48,0x13b30,0x13b38,0x8e38,0x13b90,0x13bc0,0x13b98]
image = None
previous = None
flags_seen = set()
for index, (row, line) in enumerate(zip(rows, output[1:])):
    name, enabled, low, high = row
    if name != previous:
        image = environment_image(a.research, name)
        backends = (hardware_fpatan(image, a.build), hardware_sine_cosine(image, a.build), hardware_tangent(image, a.build))
        previous = name
        assert output[0].split() == ['temperatures'] + [str(v) for v in image.read(0x8c98, '<20h')]
    image.write(0x8f30, '<B', enabled)
    # Deliberately dirty the profile selector: original initialization must reset it.
    image.write(0x1496b, '<B', 4)
    image.write(0x11b2a, '<H', index % 3)
    image.write(0x1345e, '<9h', 32767,0,0,0,32767,0,0,0,32767)
    image.write(0x13428, '<f', -800)
    image.write(0x13444, '<i', 400)
    image.write(0x1347a, '<B', 1)
    image.write(0x8d3a, '<H', 0)
    image.write(0x1347c, '<B', 0)
    image.cpu.mem_write(image.data + 0x13374, bytes(20))
    image.cpu.mem_write(image.native(0xc9894), struct.pack('<2H', low, high))
    image.call(0x95f3c, limit=2000000)
    assert image.read(0x1496b, '<B')[0] == image.read(0x14956, '<h')[0] == 0
    cloud = int(image.read(0xe762, '<H')[0] != 0)
    storm = int(image.read(0xe774, '<H')[0] & 128 != 0)
    flags_seen.add((cloud, storm))
    expected = [cloud, storm, image.read(0x14240, '<Q')[0]] + [image.read(field, '<Q')[0] for field in fields] + list(image.read(0x133fc, '<3I')) + list(struct.unpack('<2H', image.cpu.mem_read(image.native(0xc9894), 4)))
    actual = list(map(int, line.split()))
    assert actual == expected, (index, row, [(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x != y])
assert flags_seen == {(0,0), (1,0), (1,1)}, flags_seen
print(f'{len(rows)} complete environment/atmosphere/wind initializations agree across all {len(profiles)} authored environments: native profile zero, temperature toggle/table, cloud/storm strength and ordered random state')
