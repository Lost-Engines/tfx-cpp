#!/usr/bin/env python3
"""Compare complete original flight-recording files and both frame codecs.

Only DOS create/read/write/seek/close are hosted in memory. The original
header, compression, queue-array layout, resource dictionary, final patching
and frame decompression execute unchanged. Inputs are synthetic scene queues,
not an assertion that live rendering/recording integration is complete.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference, r


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
p.add_argument('--build', type=Path, default=Path('build'))
p.add_argument('--cases', type=int, default=48)
a = p.parse_args()
im = NativeReference(a.research / 'installs/cd_1994_09/TFX/TFX.DAT')
im.cpu.mem_map(0x300000, 0x40000)
code = lambda offset: im.native(0x70aa4 + offset)
output = bytearray()
cursor = 0


def create(current):
    global output, cursor
    output = bytearray()
    cursor = 0
    current.cpu.reg_write(r.UC_X86_REG_EAX, 7)
    current.return_from()


def write(current):
    global cursor
    size = current.cpu.reg_read(r.UC_X86_REG_EDX)
    raw = bytes(current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_EAX), size))
    if cursor + size > len(output):
        output.extend(bytes(cursor + size - len(output)))
    output[cursor:cursor + size] = raw
    cursor += size
    current.cpu.reg_write(r.UC_X86_REG_EAX, size)
    current.return_from()


def read(current):
    global cursor
    size = current.cpu.reg_read(r.UC_X86_REG_EDX)
    raw = bytes(output[cursor:cursor + size])
    if raw:
        current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX), raw)
    cursor += len(raw)
    current.cpu.reg_write(r.UC_X86_REG_EAX, len(raw))
    current.return_from()


def seek(current):
    global cursor
    offset = struct.unpack('<i', struct.pack('<I', current.cpu.reg_read(r.UC_X86_REG_EAX)))[0]
    origin = current.cpu.reg_read(r.UC_X86_REG_EDX)
    cursor = (0, cursor, len(output))[origin] + offset
    current.cpu.reg_write(r.UC_X86_REG_EAX, cursor)
    current.return_from()


im.intercept(0xcc3f8, 'Create the capture-owned memory file; no installation is written.', create)
im.intercept(0xc8ff0, 'Write native file bytes into capture-owned memory.', write)
im.intercept(0xc8f6c, 'Read previously captured bytes at the DOS boundary.', read)
im.intercept(0xcc44c, 'Seek the memory file for native header patching and reads.', seek)
im.intercept(0xcc410, 'Close the capture-owned DOS handle.', lambda current: current.return_from())

rng = random.Random(0xc5bec)
cases = []
counts = (0, 1, 2, 14, 15, 16, 31, 127, 128, 254, 255, 256, 347, 348)
for case in range(a.cases):
    resources = [(0, ''), (1, 'badshape.3')]
    count = (2, 3, 17, 127, 999, 1000)[case % 6]
    resources += [(rng.randrange(2, 65536), f'3/model_{case}_{i}.3') for i in range(2, count)]
    frames = []
    for frame in range(1 + case % 3):
        count = counts[(case + frame) % len(counts)]
        slots = list(range(count))
        rng.shuffle(slots)
        order = [(rng.randrange(-32768, 32768), slot) for slot in slots]
        models = []
        for index in range(count):
            sparse = count > 127 or case % 4 == 0
            parameters = [rng.randrange(1, 256) if not sparse or rng.randrange(20) == 0 else 0 for _ in range(8)]
            models.append([
                (40, 44, 56)[index % 3], 0 if case % 3 == 0 else rng.randrange(256),
                rng.randrange(16), 1 if index < 256 else (0, 2, 127, 255)[index % 4],
                resources[rng.randrange(len(resources))][0],
                *[rng.choice((0, 0, 65535, rng.randrange(65536))) for _ in range(3)],
                *[rng.randrange(-2147483648, 2147483648) for _ in range(3)],
                *parameters,
            ])
        frames.append((list(rng.randbytes(8)), [rng.randrange(65536) for _ in range(3)], order, models))
    cases.append((resources, frames))

request = [str(len(cases))]
for resources, frames in cases:
    request.append(f'{len(frames)} {len(resources)}')
    for reserved, angles, order, models in frames:
        request.append(' '.join(map(str, [*reserved, *angles, len(models), *[v for row in order for v in row], *[v for row in models for v in row]])))
    request += [f'{handle} "{name}"' for handle, name in resources]
actual = subprocess.check_output([str((a.build / 'recording_probe').resolve())], input=('\n'.join(request) + '\n').encode())
at = 0
total = 0

# Array bases and element widths in the native CODE object, in file order.
fields = ((0x510de, 'B', 0), (0x5123a, 'B', 1), (0x51396, 'B', 2), (0x514f2, 'B', 3),
          (0x5164e, 'H', 4), (0x51906, 'H', 5), (0x51bbe, 'H', 6), (0x51e76, 'H', 7),
          (0x5212e, 'i', 8), (0x5269e, 'i', 9), (0x52c0e, 'i', 10))


def arrays(frame):
    reserved, angles, order, models = frame
    count = len(models)
    result = [(im.data + 0xac9c, bytes(reserved)),
              (code(0x47c20), struct.pack('<3H', *angles)),
              (code(0x50b68), struct.pack('<H', count)),
              (code(0x50b6e), struct.pack(f'<{count}h', *[row[0] for row in order])),
              (code(0x50e26), struct.pack(f'<{count}H', *[row[1] for row in order]))]
    result += [(code(offset), struct.pack(f'<{count}{kind}', *[model[column] for model in models])) for offset, kind, column in fields]
    result.append((code(0x5317e), bytes(v for model in models for v in model[11:])))
    return result


for case, (resources, frames) in enumerate(cases):
    im.write(0xad28, '<H', len(resources))
    im.cpu.mem_write(im.data + 0x21870, struct.pack(f'<{len(resources)}H', *[row[0] for row in resources]))
    im.write(0x23f80, '<I', 0x300000)
    name_at = 0x310000
    for index, (_, name) in enumerate(resources):
        im.cpu.mem_write(0x300000 + index * 4, struct.pack('<I', name_at))
        raw = name.encode() + b'\0'
        im.cpu.mem_write(name_at, raw)
        name_at += len(raw)
    im.call(0xc5ac0, eax=im.data + 0x8868)
    for frame in frames:
        for address, raw in arrays(frame):
            if raw:
                im.cpu.mem_write(address, raw)
        im.call(0xc5bec)
    im.call(0xc5b3c, limit=5000000)
    size, = struct.unpack_from('<I', actual, at)
    at += 4
    got = actual[at:at + size]
    at += size
    assert got == output, (case, len(got), len(output), [(i, x, y) for i, (x, y) in enumerate(zip(got, output)) if x != y][:20])
    # Independently execute the original reader on every written frame.
    cursor = 10
    im.write(0xac96, '<h', 7)
    for frame in frames:
        im.call(0xc5ff0)
        for address, raw in arrays(frame):
            assert bytes(im.cpu.mem_read(address, len(raw))) == raw, (case, hex(address))
        total += 1
assert at == len(actual)
print(f'{len(cases)} complete original recording files / {total} frames agree byte for byte, including queue limits, 255-byte runs, resource dictionaries and header patching; original frame decoding also agrees.')
