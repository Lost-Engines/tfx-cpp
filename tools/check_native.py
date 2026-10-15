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

# Compare complete update sequences, not just individual predicates.
cpu.mem_write(0x7205c,exe[0x7205c:0x720a7])
patterns = [[2],[4],[6],[8],[12],[18],[2,4,3,10,2,8],[200],[65535,7,1,32768]]
clock_requests, clock_expected = [], []
for pattern in patterns:
    cpu.mem_write(0xe74c,b'\0\0')
    elapsed=[pattern[i%len(pattern)] for i in range(140)]
    clock_requests.append([len(elapsed),*elapsed])
    values=[]
    for step in elapsed:
        cpu.mem_write(0x13476,struct.pack('<H',step))
        cpu.reg_write(r.UC_X86_REG_ESP,0x380000)
        cpu.emu_start(0x7205c,0x720a7,count=50)
        assert cpu.reg_read(r.UC_X86_REG_EIP)==0x720a7
        values.extend([int(bool(cpu.mem_read(0xac90,1)[0])),struct.unpack('<h',cpu.mem_read(0xe74c,2))[0]])
    clock_expected.append(values)
assert [list(map(int,line.split())) for line in cpp('clock',clock_requests)]==clock_expected

cpu.mem_write(0xb6ce0,exe[0xb6ce0:0xb6dd8])
cpu.mem_write(0x46220,b''.join(struct.pack('<I',struct.unpack_from('<I',exe,0xb6cc4+i*4)[0]+0x70aa4) for i in range(7)))
cpu.mem_write(0x20b98,struct.pack('<I',0x300000))
cpu.mem_write(0x20b9c,struct.pack('<I',0x310000))
sequences = [[0,1,0x603,65534,5],[0xff00,1,2,5],[0,1,0x403,65534,0x0400,4,65535],[0,2,0xfd03,65534,5]]
stream_expected=[]
non_returning=[]
for words in sequences:
    cpu.mem_write(0x300000,b'\0'*32+struct.pack(f'<{len(words)}H',*words))
    cpu.mem_write(0x310000,b'\0'*45)
    cpu.mem_write(0x310000+16+11,struct.pack('<H',16))
    states=[]
    for tick in range(40):
        cpu.mem_write(0x380000,struct.pack('<I',0x200000))
        for reg,value in [(r.UC_X86_REG_ESP,0x380000),(r.UC_X86_REG_EAX,0),(r.UC_X86_REG_EDX,0)]:cpu.reg_write(reg,value)
        cpu.emu_start(0xb6ce0,0x200000,count=10000)
        if cpu.reg_read(r.UC_X86_REG_EIP)!=0x200000:
            assert words==sequences[2] and tick==6,(words,tick,hex(cpu.reg_read(r.UC_X86_REG_EIP)))
            non_returning.append((words,states.copy()))
            break
        states.append(cpu.mem_read(0x310010,1)[0])
    stream_expected.append(states)
assert [list(map(int,line.split())) for line in cpp('stream',[[len(words),len(states),*words] for words,states in zip(sequences,stream_expected)])]==stream_expected

assert len(non_returning)==1
for words,states in non_returning:
    request=' '.join(map(str,[len(words),len(states)+1,*words]))+'\n'
    result=subprocess.run([probe,'stream'],input=request.encode(),capture_output=True)
    assert result.returncode!=0 and b'makes no value-changing progress' in result.stderr
    assert list(map(int,result.stdout.split()))==states

cpu.mem_write(0xbc114,exe[0xbc114:0xbc19f])
vertices=[[0,0,0],[32767,-32768,120],[-17,256,-32000]]
jitter_requests,jitter_expected=[],[]
for seed in [[12609,22822],[0,65535],[65535,65535],[1,0]]:
    for shifts in [[14,14,14],[13,12,11],[0,7,15],[16,31,32]]:
        state=seed
        for frame in range(3):
            jitter_requests.append([*state,*shifts,*(v for point in vertices for v in point)])
            cpu.mem_write(0x48632,struct.pack('<2H',*state))
            cpu.mem_write(0x48636,bytes(shifts))
            words=[len(vertices),0]+[value&65535 for point in vertices for value in point]
            cpu.mem_write(0x300000,struct.pack(f'<{len(words)}H',*words))
            cpu.reg_write(r.UC_X86_REG_ESI,0x300000)
            cpu.reg_write(r.UC_X86_REG_ESP,0x380000)
            cpu.emu_start(0xbc114,0xbc19f,count=1000)
            assert cpu.reg_read(r.UC_X86_REG_EIP)==0xbc19f
            expected=[v for i in range(len(vertices)) for v in struct.unpack('<3h',cpu.mem_read(0x47cee+i*6,6))]
            state=list(struct.unpack('<2H',cpu.mem_read(0x48632,4)))
            jitter_expected.append([*expected,*state])
assert [list(map(int,line.split())) for line in cpp('jitter',jitter_requests)]==jitter_expected
print(f'Native sequence comparisons passed: {len(patterns)*140} animation-clock frames, {sum(map(len,stream_expected))} completed stream ticks, 1 non-returning loop rejection and {len(jitter_expected)} jitter cases')
