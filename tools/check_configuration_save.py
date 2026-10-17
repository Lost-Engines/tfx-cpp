#!/usr/bin/env python3
"""Compare complete original preference writing, retaining unrelated configuration.

Only filesystem size/read/write are supplied. Keyword removal, C formatting,
floating rounding and all four original setting writers execute unchanged.
Native overflowing buffers are excluded; the C++ writer refuses oversized output.
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
p.add_argument('--record', type=Path)
a = p.parse_args()
im = NativeReference(a.research / 'installs/cd_1994_09/TFX/TFX.DAT')
im.call(0xde851)
im.call(0xde547)
content, writes = [b''], []
def length(image):
    image.cpu.reg_write(r.UC_X86_REG_EAX, len(content[0]))
    image.return_from()
def read(image):
    image.cpu.mem_write(image.cpu.reg_read(r.UC_X86_REG_EDX), content[0])
    image.return_from()
def write(image):
    writes.append(bytes(image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_EDX), image.cpu.reg_read(r.UC_X86_REG_EBX))))
    image.return_from()
im.intercept(0xc9c24, 'Supply configuration file length', length)
im.intercept(0xc9d4c, 'Supply configuration file bytes', read)
im.intercept(0xc9e7c, 'Observe original configuration file output', write)
rng = random.Random(0xa6808)
fbits = lambda v: struct.unpack('<I', struct.pack('<f', v))[0]
texts = [b'', b'X=Y', b'DETAIL=0\r\nDETAIL=1\r\n', b'\r\n\r\nDETAILER=3\r\nX=2\n\nY=4\r', b'detail=0\r\nDETAIL=1\r\n', b'DETAIL=1\0MORE=2', b'X'*1025, b'REALISM=' + b'0'*1015]
rows = []
for index in range(512):
    if index < len(texts): text = texts[index]
    else:
        lines = [b'CONTROL=2', b'MODEL=3', b'BLASTER=A220 I7 D1 T6', b'UNRECOGNISED=yes', b'HUDCOL=120', b'REALISM=0,1,1,1,0,1', b'JOYSCALE=512', b'DETAIL=2']
        rng.shuffle(lines)
        if index % 3 == 0: lines.extend([b'DETAIL=1', b'REALISM=2,0,0'])
        text = rng.choice([b'\r\n', b'\n', b'\r', b'\r\n\r\n']).join(lines) + rng.choice([b'', b'\r\n', b'\n'])
    scale = [0., -0., .5, 1.5, 2.5, 99.5, 100.5, 512.5, 513.5, 999., -2.5, float('nan'), float('inf'), -float('inf'), rng.uniform(0,999)][index % 15]
    values = [rng.randrange(256), fbits(scale), rng.randrange(65536)] + [rng.randrange(256) for _ in range(7)]
    rows.append((values, text))
payload = '\n'.join(' '.join(map(str, values)) + '|' + (text.hex() or '-') for values, text in rows) + '\n'
output = subprocess.check_output([str((a.build / 'configuration_save_probe').resolve())], input=payload.encode()).decode().splitlines()
assert len(output) == len(rows)
fixtures = []
fields = [(0x8864,'<B'),(0xac68,'<I'),(0xa4ec,'<H')] + [(f,'<B') for f in (0x5954,0x8f31,0x8e22,0x8e23,0x8e25,0x8f30,0x8867)]
for index, ((values, text), actual) in enumerate(zip(rows, output)):
    content[0] = text
    for (offset, fmt), value in zip(fields, values): im.write(offset, fmt, value)
    writes.clear()
    im.call(0xa6808, limit=2000000)
    assert len(writes) <= 1
    expected = writes[0].hex() if writes else '-'
    assert actual == expected, (index, values, text, bytes.fromhex(actual) if actual != '-' else None, writes)
    if index < 128: fixtures.append(' '.join(map(str, values)) + '|' + (text.hex() or '-') + '|' + expected)
if a.record: a.record.write_text('\n'.join(fixtures) + '\n')
print(f'{len(rows)} complete original preference writes agree: retained hardware/unknown lines, sequential first-prefix replacement, line endings, rounding, signed HUD values and skipped unavailable input')
