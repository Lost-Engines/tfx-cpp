#!/usr/bin/env python3
"""Execute original OSL release/reuse and pool exhaustion with a synthetic bank."""
import argparse
from pathlib import Path
import struct
import subprocess
from native_osl import NativeOSL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    bank = bytearray(0x500)
    bank[:4], bank[7] = b'OSL1', 4
    for at, value in ((0x26, 1), (0x92, 1), (0x94, 1), (0xaa, 50), (0xce, 1), (0x202, 4)):
        struct.pack_into('<H', bank, at, value)
    for at, value in ((0x48, 0x80), (0x1d0, 0x200)):
        struct.pack_into('<I', bank, at, value)
    bank[0x96:0xa6], bank[0xac] = bytes([127] * 16), 1
    native = NativeOSL((args.research / 'installs/cd_1994_09/TFX/START.EXE').read_bytes())
    native.initialise()
    rows = []

    def snapshot(count):
        values = []
        for index in range(count):
            data = bytes(native.cpu.mem_read(0x10037 + index * 0x39, 0x39))
            values += [data[0], data[1], data[2], struct.unpack_from('<H', data, 3)[0],
                       data[5], data[6], data[7], struct.unpack_from('<H', data, 10)[0]]
        values.append(sum(bool(native.channels()[index * 21]) for index in range(32)))
        rows.append(' '.join(map(str, values)))

    def ticks(count):
        for _ in range(count):
            native.tick()

    assert native.load(bytes(bank)) == native.play() == (0, False)
    snapshot(1)
    ticks(3);snapshot(1)
    native.call(0x9b4, 'iret', AX=0x300, BX=0);snapshot(1)
    ticks(8);snapshot(1)
    assert native.load(bytes(bank)) == (0, False)
    snapshot(1)
    assert native.play() == (1, False)
    snapshot(2)
    ticks(3);snapshot(2)
    native.call(0x9b4, 'iret', AX=0x600, BX=0);snapshot(2)
    native.call(0x9b4, 'iret', AX=0x600, BX=1);snapshot(2)
    native.call(0x9b4, 'iret', AX=0x300, BX=0);snapshot(2)
    assert native.load(bytes(bank)) == (0, False)
    for index in range(16):
        assert native.play() == (index, False)
    assert native.play()[1]
    snapshot(16)
    for index in range(16):
        native.call(0x9b4, 'iret', AX=0x600, BX=index)
    snapshot(16)
    args.record.write_text('\n'.join(rows) + '\n')
    subprocess.run([str((args.build / 'osl_lifetime_test').resolve()), str(args.record)], check=True)
    print('Original synthetic OSL playback agrees after active-bank release, eight further ticks, handle reuse, overlapping playback, explicit stop, full 16-song pool rejection and ordered global stop; no game resource bytes retained')


if __name__ == '__main__':
    main()
