#!/usr/bin/env python3
"""Compare C++ against original TFX 2.05 x86 routines using controlled inputs.

Requires Unicorn; reads the original executable but never runs a DOS session.
"""
import argparse
import hashlib
from itertools import product
from pathlib import Path
import random
import struct
import subprocess
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn import x86_const as r

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=Path('build'))
parser.add_argument('--data-dir', type=Path, required=True)
args = parser.parse_args()
exe = (args.data_dir / 'TFX.DAT').read_bytes()
assert hashlib.sha256(exe).hexdigest() == '2cc41a39fa95a2c9fd883c4220d7bdd9cca00c543c89b019eb270763f59d1d9a', 'Native offsets require the reference TFX 2.05 executable'
probe = str((args.build / 'tfx_probe').resolve())


def cpp(mode, rows=()):
    data = ''.join(' '.join(map(str, row)) + '\n' for row in rows)
    return subprocess.check_output([probe, mode], input=data.encode()).decode().splitlines()


native_sine = struct.unpack_from('<1024h', exe, 0xc77d8)
assert tuple(map(int, cpp('sine')[0].split())) == native_sine
cpu = Uc(UC_ARCH_X86, UC_MODE_32)
cpu.mem_map(0, 0x400000)
cpu.mem_write(0xdad88, exe[0xdad88:0xdaf2d])
cpu.mem_write(0x56d34, exe[0xc77d8:0xc77d8 + 2560])
generator = random.Random(205)
angles = [[0, 0, 0], [0, 32768, 0], [16384, 0, 0], [0, 16384, 0], [0, 0, 16384]]
angles += [[generator.randrange(65536) for _ in range(3)] for _ in range(200)]
expected = []
for triple in angles:
    cpu.mem_write(0x380000, struct.pack('<I', 0x200000))
    cpu.reg_write(r.UC_X86_REG_ESP, 0x380000)
    for reg, value in zip([r.UC_X86_REG_EBX, r.UC_X86_REG_ESI, r.UC_X86_REG_EDI], triple):
        cpu.reg_write(reg, value)
    cpu.emu_start(0xdad88, 0x200000, count=10000)
    assert cpu.reg_read(r.UC_X86_REG_EIP) == 0x200000
    expected.append(struct.unpack('<9h', cpu.mem_read(0x47c5c, 18)))
actual = [tuple(map(int, line.split())) for line in cpp('rotation', angles)]
assert actual == expected, next(((angles[i], a, b) for i, (a, b) in enumerate(zip(actual, expected)) if a != b), 'matrix count differs')

cpu.mem_write(0xc9898, exe[0xc9898:0xc98c4])
cpu.mem_write(0x380000, struct.pack('<I', 0x200000))
cpu.reg_write(r.UC_X86_REG_ESP, 0x380000)
cpu.emu_start(0xc9898, 0x200000, count=100)
counts = [1, 2, 10, 3, 7, 4, 1, 10] * 8
random_expected = []
for count in counts:
    cpu.mem_write(0x380000, struct.pack('<I', 0x200000))
    cpu.reg_write(r.UC_X86_REG_ESP, 0x380000)
    cpu.emu_start(0xc98a3, 0x200000, count=100)
    low, high = struct.unpack('<2H', cpu.mem_read(0x58df0, 4))
    random_expected.append((high % count, low, high))
assert [tuple(map(int, line.split())) for line in cpp('random', [[c] for c in counts])] == random_expected

cpu.mem_write(0xbb574, exe[0xbb574:0xbb81c])
cpu.mem_write(0x4a814, struct.pack('<I', 0x200000))
taken = None


def stop(machine, at, size, unused):
    global taken
    if at in (0xbb574, 0xbb584, 0x200000):
        taken = at in (0xbb574, 0xbb584)
        machine.emu_stop()


cpu.hook_add(UC_HOOK_CODE, stop)
values = [0, 1, 127, 128, 255, 256, 32767, 32768, 65535]
conditions, results = [], []
for opcode in [23, 24, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 63, 64, 65, 66, 67, 68, 69, 70]:
    for operand, state in product(values, [0, 1, 127, 128, 255] if opcode in (23, 24, 32, 33, 34, 35, 36, 37) else values):
        cpu.mem_write(0x47cae, bytes([state & 255]))
        cpu.mem_write(0x47c80, struct.pack('<H', state))
        cpu.mem_write(0x47c82, struct.pack('<H', state))
        cpu.mem_write(0x300000, struct.pack('<3H', operand, 0, 0))
        cpu.reg_write(r.UC_X86_REG_ESI, 0x300000)
        cpu.reg_write(r.UC_X86_REG_ESP, 0x380000)
        cpu.reg_write(r.UC_X86_REG_EAX, 0)
        taken = None
        target = struct.unpack_from('<I', exe, 0xbb2b8 + opcode * 4)[0] + 0x70aa4
        cpu.emu_start(target, 0x200001, count=100)
        assert taken is not None
        conditions.append([opcode, operand, state])
        results.append(int(taken))
assert list(map(int, cpp('conditions', conditions))) == results
print(f'Native comparisons passed: 1024 sine samples, {len(angles)} component matrices, {len(counts)} random updates, {len(conditions)} branch predicates')
