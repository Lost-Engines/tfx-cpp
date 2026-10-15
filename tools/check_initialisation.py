#!/usr/bin/env python3
"""Compare retail INIT results with the complete original mission-script loader.

The original parser, dispatch table, handlers and text allocation/copying run.
Decoded input, allocation, saved-start success and environment loading are the
explicit boundary; no flight, scenery creation or FINISH execution is claimed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from unicorn import x86_const as r
from native_reference import NativeReference


def dataset(filename):
    text = filename.read_text()
    return json.loads(text.split('=', 1)[1].strip().removesuffix(';'))


class InitialisationCapture:
    def __init__(self, executable, source, context):
        self.image = NativeReference(executable)
        self.image.cpu.mem_map(0x300000, 0x40000)
        self.image.cpu.mem_write(0x300000, source + b'\0')
        self.image.write(0x11948, '<I', 0x300000)
        self.allocation = 0x310000
        self.image.intercept(0x79680, 'decoded mission source supplied; tail call original parser reset', self.source)
        self.image.intercept(0xc91f0, 'release externally supplied source buffer', lambda image: image.return_from())
        self.image.intercept(0x747fc, 'environment resource setup deferred; script declaration is captured', lambda image: image.return_from())
        self.image.intercept(0xc90ec, 'allocate zeroed mission text storage in capture-owned memory', self.allocate)
        self.image.intercept(0xa4918, 'saved-start asset request: declared success, no flight state supplied', self.saved_start)
        self.image.intercept(0xb0eb0, 'native fatal diagnostic becomes an explicit test failure', self.fatal)
        x, y, z, speed, weapons = context
        for offset, value in [(0x13424, x), (0x13430, y), (0x1343c, z)]:
            self.image.write(offset, '<i', value)
        self.image.write(0x86f4, '<I', speed)
        self.image.write(0x11b40, '<B', weapons)
        # Seed these with conspicuous old state to prove the native reset.
        self.image.write(0x11b2a, '<H', 2)
        self.image.write(0x86c8, '<3H', 123, 456, 789)

    @staticmethod
    def source(image):
        image.cpu.reg_write(r.UC_X86_REG_EIP, image.native(0x791f4))

    def allocate(self, image):
        size = image.cpu.reg_read(r.UC_X86_REG_EAX)
        if not 0 < size < 20000 or self.allocation + size > 0x340000:
            raise RuntimeError(f'native mission allocation exceeds capture arena: {size}')
        image.cpu.reg_write(r.UC_X86_REG_EAX, self.allocation)
        self.allocation += (size + 15) & ~15
        image.return_from()

    @staticmethod
    def saved_start(image):
        image.cpu.reg_write(r.UC_X86_REG_EAX, 1)
        image.return_from()

    @staticmethod
    def fatal(image):
        stack = image.cpu.reg_read(r.UC_X86_REG_ESP)
        pointer, = struct.unpack('<I', image.cpu.mem_read(stack + 4, 4))
        raise RuntimeError('native mission diagnostic: ' + InitialisationCapture.string(image, pointer))

    @staticmethod
    def string(image, address):
        if not address:
            return None
        result = bytearray()
        for index in range(20000):
            value = image.cpu.mem_read(address + index, 1)[0]
            if not value:
                return result.decode('latin1')
            result.append(value)
        raise RuntimeError('unterminated native mission string')

    def run(self):
        image = self.image
        image.call(0x7a4f8, limit=2000000)
        read = lambda offset, format: image.read(offset, format)[0]
        text = lambda offset: self.string(image, image.data + offset)
        indirect = lambda offset: self.string(image, read(offset, '<I'))
        targets = []
        for index in range(read(0x11b22, '<H')):
            offset = 0x5c40 + index * 26
            targets.append([read(offset + delta, '<i') for delta in (0, 4, 8, 18)] + [indirect(offset + 22)])
        completion = None
        kind = read(0x11b30, '<B')
        if kind != 255:
            completion = [kind, 0 if kind == 2 else read(0x11b31, '<i'), indirect(0x11b35)]
        flak = [list(image.read(0x11824 + index * 16, '<4i')) for index in range(read(0x11b41, '<B'))]
        messages = [[read(0x11ac8 + index * 9, '<i'), indirect(0x11acc + index * 9)] for index in range(read(0x11b42, '<B'))]
        events = []
        for index in range(read(0x11b43, '<B')):
            offset = 0x11874 + index * 11
            events.append([read(offset + 3, '<i'), *image.read(offset, '<3B')])
        result = [text(0x11974), text(0x11960), text(0x11988),
                  [read(offset, '<i') for offset in (0x13424, 0x13430, 0x1343c)] + [read(0x11b3c, '<B')],
                  read(0x11b2a, '<H') + 1, list(image.read(0x86c8, '<3H')), read(0x86f4, '<I'),
                  read(0x11b40, '<B'), read(0x11b3d, '<B'), text(0x11abc) if read(0x11b39, '<B') else None,
                  read(0x11b28, '<h'), read(0x11b2c, '<h'), read(0x1194c, '<i'), read(0x1199c, '<i'),
                  targets, completion, flak, messages, events]
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--research', type=Path, required=True)
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    data = args.research / 'installs/cd_1994_09/TFX'
    metadata = dataset(args.research / 'analysis/missions/data.js')
    missions = sorted((m for m in metadata['missions'] if m['category'] != 'retained'), key=lambda m: m['name'])
    assert len(missions) == 128
    catalog = json.loads((args.research / 'analysis/resources/catalog.json').read_text())['entries']
    catalog = {e['identifier']: e for e in catalog}
    cases, requests = [], []
    for context in ([0, 0, 0, 0x3f800000, 0], [-12345, -6789, 54321, 0x3f200000, 173]):
        for mission in missions:
            resource = catalog[mission['id']]
            source = (args.research / 'extracted/cd_1994_09/resources' / resource['path']).read_bytes()
            assert hashlib.sha256(source).hexdigest() == resource['output_sha256']
            capture = InitialisationCapture(data / 'TFX.DAT', source, context)
            expected = capture.run()
            cases.append({'mission': mission['name'], 'context': context, 'expected': expected})
            requests.append(' '.join(map(str, [mission['name'], *context])))
    result = subprocess.run([str((args.build / 'mission_probe').resolve()), str(data)], input='\n'.join(requests) + '\n', text=True, capture_output=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == len(cases)
    names = ['world', 'environment', 'waypoints', 'position/landed', 'aircraft', 'angles', 'speed bits', 'weapons', 'default weapons', 'saved-start extension', 'stationary ID', 'mobile ID', 'timer', 'clock', 'targets', 'completion', 'flak', 'messages', 'parameter events']
    for case, line in zip(cases, lines):
        observed = json.loads(line)
        if observed != case['expected']:
            differences = [(names[i], a, b) for i, (a, b) in enumerate(zip(observed, case['expected'])) if a != b]
            raise AssertionError((case['mission'], case['context'], differences))
    if args.record:
        args.record.write_text(json.dumps({'scope': __doc__, 'dependencies': {hex(k): v for k, v in capture.image.dependencies.items()}, 'cases': cases}, separators=(',', ':')) + '\n')
    print(f'{len(cases)} native/C++ mission initialisations passed: all 128 retail scripts in fresh and retained-state contexts')


if __name__ == '__main__':
    main()
