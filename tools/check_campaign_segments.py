#!/usr/bin/env python3
"""Compare post-flight campaign segments using original parser handlers.

Flight outcome/status variables and the actual mission caller are supplied at
the flight-return boundary. Original branches, assignments and gosub/return
handlers execute; media are observed, not painted. Stop at the next external
launch/menu/planner/child-parser boundary. This is campaign control-flow
coverage, separate from naturally completed flight and complete front-end tests.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    args = parser.parse_args()
    program = next(p for p in json.loads((args.research / 'analysis/presentations/programs.json').read_text()) if p['name'] == 'tfx')
    variables, functions = program['variables'], program['functions']
    mission_function = next(index for index, function in enumerate(functions) if function['name'] == 'mission')
    mission_launch = next(index for index, node in enumerate(functions[mission_function]['nodes']) if node['type'] == 5 and node.get('resource') == '%mission')
    resume = (mission_function, mission_launch + 1)
    image = NativeReference(args.research / 'installs/cd_1994_09/TFX/TFX.DAT')
    image.cpu.mem_map(0x300000, 0x40000)
    image.write(0xab41, '<B', 1)
    image.write(0x1afee, '<H', len(variables))
    descriptors = []
    for index, variable in enumerate(variables):
        name = variable['name'].encode() + b'\0'
        image.cpu.mem_write(image.data + 0x1ad62 + index * 21, name)
        image.write(0x1ad44 + index, '<B', variable['string_value'])
        pointer = 0x300000 + index * 64
        image.cpu.mem_write(pointer, bytes(9) + name)
        descriptors.append(pointer)
    nodes = [(fi, ni) for fi, function in enumerate(functions) for ni in range(len(function['nodes']))]
    addresses = {node: 0x310000 + index * 64 for index, node in enumerate(nodes)}
    locations = {pointer: node for node, pointer in addresses.items()}
    for (fi, ni), pointer in addresses.items():
        node = functions[fi]['nodes'][ni]
        successor = addresses.get((fi, ni + 1), 0)
        image.cpu.mem_write(pointer, struct.pack('<B3I', node['type'], successor, addresses.get((fi, ni - 1), 0), pointer + 16))
        if node['type'] in (3, 10):
            payload = bytearray.fromhex(node['payload_hex'])
            at = 1 if node['type'] == 3 else 0
            ordinal = struct.unpack_from('<I', payload, at)[0]
            struct.pack_into('<I', payload, at, descriptors[ordinal] if ordinal < len(descriptors) else 0)
            if node['type'] == 3:
                struct.pack_into('<I', payload, 13, addresses[(payload[11], payload[12])])
            image.cpu.mem_write(pointer + 16, bytes(payload))
    callers = [(fi, ni) for fi, function in enumerate(functions) for ni, node in enumerate(function['nodes'])
               if node['type'] == 3 and bytes.fromhex(node['payload_hex'])[10:13] == bytes((1, mission_function, 0))]
    assert callers, 'retail mission subroutine callers were not found'
    base = dict(rank=1, mission=501, lives=3, score=10000, miss_val=1, sqd_val=1, soap_val=1)
    def inherited(caller):
        values = dict(base)
        for node in functions[caller[0]]['nodes'][:caller[1]]:
            if node['type'] != 10:
                continue
            raw = bytes.fromhex(node['payload_hex'])
            ordinal = struct.unpack_from('<I', raw)[0]
            if variables[ordinal]['name'] == 'mission' and raw[4] == 0:
                values['mission'] = struct.unpack_from('<I', raw, 5)[0]
        return values
    cases = []
    for caller in callers:
        for outcome in (0, 1, 2, 3, 99):
            cases.append((caller, dict(inherited(caller), outcome=outcome)))
    # Broaden the status, prior ejection, safe-return, promotion and retry gates
    # at one real call site from each mission-bearing function.
    representatives = dict((fi, (fi, ni)) for fi, ni in reversed(callers))
    for caller in representatives.values():
        for status in range(7):
            for safe in (0, 1):
                cases.append((caller, dict(inherited(caller), outcome=3, status=status, safe=safe)))
        for rank in (0, 1, 5, 6):
            cases.append((caller, dict(inherited(caller), outcome=3, rank=rank, promote=1, ejtbust=1)))
        cases.append((caller, dict(inherited(caller), outcome=3, status=1, safe=1, ejtbust=1)))
        cases.append((caller, dict(inherited(caller), outcome=0, redo=1)))
    expected, requests, visited = [], [], Counter()
    for caller, values in cases:
        numeric = [values.get(v['name'], 0) for v in variables if not v['string_value']]
        iterator = iter(numeric)
        for index, variable in enumerate(variables):
            value = 0x303000 if variable['string_value'] else next(iterator)
            image.write(0x1a400 + index * 4, '<I', value)
        image.cpu.mem_write(0x303000, b'TEST\0')
        image.write(0x1afdc, '<H', 1)
        image.write(0x1ab68, '<I', addresses[caller])
        cursor, trace = addresses[resume], []
        for _ in range(16384):
            if not cursor:
                break
            fi, ni = locations[cursor]
            kind = functions[fi]['nodes'][ni]['type']
            visited[functions[fi]['name']] += 1
            successor = addresses.get((fi, ni + 1), 0)
            image.write(0x1ad1c, '<I', cursor)
            image.write(0x1ad14, '<I', successor)
            if kind in (3, 10):
                image.call(0xb22d8 if kind == 3 else 0xb28b8, eax=cursor + 16)
                cursor = image.read(0x1ad14, '<I')[0]
            elif kind == 4:
                assert image.read(0x1afdc, '<H')[0], ('return without caller', caller, values, fi, ni)
                image.call(0xb2574)
                resumed = locations[image.read(0x1ad1c, '<I')[0]]
                cursor = addresses.get((resumed[0], resumed[1] + 1), 0)
            else:
                trace += [fi, ni, image.read(0x1afdc, '<H')[0], kind]
                if kind in (5, 7, 8, 9, 13):
                    break
                cursor = successor
        else:
            raise AssertionError(('native campaign segment exceeded its bound', caller, values))
        trace += [-1, *(image.read(0x1a400 + index * 4, '<I')[0] for index, v in enumerate(variables) if not v['string_value'])]
        depth = image.read(0x1afdc, '<H')[0]
        trace.append(depth)
        for index in range(depth):
            trace += list(locations[image.read(0x1ab68 + index * 4, '<I')[0]])
        expected.append(trace)
        requests.append(' '.join(map(str, ['R', int(program['id'], 16), *resume, 1, *caller, *numeric])))
    output = subprocess.run([str((args.build / 'presentation_probe').resolve()),
                             str((args.research / 'installs/cd_1994_09/TFX').resolve())],
                            input='\n'.join(requests) + '\n', capture_output=True, text=True, check=True)
    actual = [list(map(int, line.split())) for line in output.stdout.splitlines()]
    assert len(actual) == len(expected)
    for case, got, wanted in zip(cases, actual, expected):
        assert got == wanted, (case, got, wanted)
    required = {'outcomes', 'death1', 'mia', 'eject_ok', 'bust_ejc', 'un-defeat'}
    assert required <= visited.keys(), ('missing post-flight branches', required - visited.keys())
    print(f'{len(cases)} original post-flight campaign segments agree across {len(callers)} mission call sites: action order, numeric variables and return stacks; visited {sorted(visited)}')


if __name__ == '__main__':
    main()
