#!/usr/bin/env python3
"""Compare surface route/movement updates with native 0x7c2bc.

The supplied context contains no eligible combat targets. Nearby weapon
selection, scenery lookup and radio output are declared host boundaries;
route commands, controller stacks, steering, acceleration and movement run.
"""
import argparse
from pathlib import Path
import struct
import subprocess

from check_actors import dataset, original
from native_reference import NativeReference, r


def original_steps(data_dir, pose, body, profile, ticks):
    image = NativeReference(data_dir / 'TFX.DAT')
    image.cpu.mem_map(0x300000, 0x40000)
    image.cpu.mem_write(0x300000, body)
    image.cpu.mem_write(0x330000, bytes.fromhex(profile['hex']))
    state = bytearray(49)
    struct.pack_into('<3i3Hi', state, 0, *pose[5:8], *pose[8:11], pose[11])
    struct.pack_into('<HII', state, 36, 1, 0x300000, 0x330000)
    state[47] = pose[12]
    image.cpu.mem_write(0x320000, bytes(state))
    image.write(0xac58, '<i', -16384)
    image.write(0xac5c, '<i', 0)
    image.intercept(0x7be44, 'No nearby eligible aircraft in the supplied noncombat context', lambda im: im.return_from())
    image.intercept(0xb0d80, 'Ground targets unavailable in the supplied noncombat context', lambda im: (im.cpu.reg_write(r.UC_X86_REG_EAX, 65535), im.return_from()))
    image.intercept(0x81198, 'Radio text output is captured outside movement state', lambda im: im.return_from())
    digest = 14695981039346656037
    for tick in range(ticks):
        image.call(0x7c2bc, eax=0x320000, limit=200000)
        source = bytes(image.cpu.mem_read(0x320000, 49))
        fields = [*struct.unpack_from('<3i', source), struct.unpack_from('<H', source, 14)[0], struct.unpack_from('<i', source, 18)[0], struct.unpack_from('<h', source, 22)[0], struct.unpack_from('<i', source, 24)[0], *struct.unpack_from('<2hI', source, 28), struct.unpack_from('<I', source, 38)[0] - 0x300000, source[47]]
        for value in fields:
            for byte in struct.pack('<I', value & 0xffffffff):
                digest = ((digest ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--ticks', type=int, default=128)
    parser.add_argument('--verify-fixture', type=Path)
    args = parser.parse_args()
    data_dir = args.research / 'installs/cd_1994_09/TFX'
    if args.verify_fixture:
        tokens = args.verify_fixture.read_text().split()
        assert len(tokens) % 4 == 0
        for at in range(0, len(tokens), 4):
            ticks, profile_hex, program_hex, expected = tokens[at:at+4]
            header, raw = bytes.fromhex(profile_hex), bytes.fromhex(program_hex)
            profiles, cursor = [], 4
            for _ in range(int.from_bytes(header[2:4], 'little')):
                size = {14: 74, 15: 58, 16: 46, 17: 34}[header[cursor] & 127]
                record = header[cursor:cursor+size]
                profiles.append({'id': int.from_bytes(record[32:34], 'little'), 'hex': record.hex()})
                cursor += size
            assert not any(header[cursor:])
            poses = original(data_dir, raw, profiles)
            assert len(poses) == 1 and poses[0][0] == 16
            pose = poses[0]
            offset = pose[1]
            length = int.from_bytes(raw[offset-2:offset], 'little')
            profile = next(p for p in profiles if p['id'] == pose[2])
            digest = original_steps(data_dir, pose, raw[offset:offset+length], profile, int(ticks))
            assert digest == int(expected), (at // 4, digest, expected)
        subprocess.run([str((args.build / 'surface_tests').resolve()), str(args.verify_fixture)], check=True)
        print(f'{len(tokens) // 4} saved surface trajectories verified against original execution')
        return
    import json
    programs = json.loads((args.research / 'analysis/waypoints/programs.json').read_text())['programs']
    profiles = dataset(args.research / 'analysis/entities/data.js')['records']
    by_id = {p['id']: p for p in profiles}
    names = [p['names'][0] if p['names'] else p['id'] for p in programs]
    result = subprocess.run([str((args.build / 'actor_probe').resolve()), str(data_dir), 'surface'], input='\n'.join(f'{name} {args.ticks}' for name in names) + '\n', text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    lines = iter(result.stdout.splitlines())
    actors = 0
    for name, program in zip(names, programs):
        header = next(lines).split()
        assert header[0] == name
        actual = [list(map(int, next(lines).split())) for _ in range(int(header[1]))]
        raw = (args.research / 'extracted/cd_1994_09/resources' / program['path']).read_bytes()
        poses = [pose for pose in original(data_dir, raw, profiles) if pose[0] == 16]
        assert len(actual) == len(poses)
        for output, pose in zip(actual, poses):
            offset = pose[1]
            length = int.from_bytes(raw[offset-2:offset], 'little')
            digest = original_steps(data_dir, pose, raw[offset:offset+length], by_id[pose[2]], args.ticks)
            assert output == [offset, pose[2], pose[3], digest], (name, output, pose, digest)
            actors += 1
    print(f'{actors} native surface actors x {args.ticks} ticks match in route, controls, pose and movement ({actors * args.ticks} updates)')


if __name__ == '__main__':
    main()
