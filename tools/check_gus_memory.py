#!/usr/bin/env python3
"""Compare native TFX sample sorting/loading with GUS.COM RAM allocation.

C52D0, C4F5C and DDE2C execute unchanged in the 32-bit game. Allocation calls
execute the real 16-bit GUS.COM interrupt dispatcher and command 5. Detected
RAM size and sample metadata are supplied; filesystem transfer and GF1 upload
are observed. No ordering, allocation arithmetic or residency flags are replaced.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference, r
from native_gus_memory import GusMemoryReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path)
    args = parser.parse_args()
    directory = args.research / 'installs/cd_1994_09/TFX'
    image = NativeReference(directory / 'TFX.DAT')
    driver = GusMemoryReference(directory / 'GUS.COM')
    image.cpu.mem_map(0x300000, 0x10000)
    image.write(0x20c74, '<I', 0x302000)
    uploads = []

    def allocation(current):
        address = driver.allocate(current.cpu.reg_read(r.UC_X86_REG_EAX))
        current.cpu.reg_write(r.UC_X86_REG_EAX, address or 0)
        current.return_from()

    def upload(current):
        uploads.append((current.cpu.reg_read(r.UC_X86_REG_EAX),
                        current.cpu.reg_read(r.UC_X86_REG_EBX)))
        current.return_from()

    image.intercept(0xd5da0, 'Supply sufficient caller stack for the two original sorting arrays.',
                    lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0x100000), current.return_from()))
    image.intercept(0xe6b68, 'Execute the actual GUS.COM allocator at the real-mode service boundary.', allocation)
    image.intercept(0xc5214, 'Supply a synthetic sample filename at the filesystem boundary.',
                    lambda current: (current.cpu.reg_write(r.UC_X86_REG_EAX, 0x301000), current.return_from()))
    image.intercept(0xc8cf0, 'Supply the declared sample transfer without accessing external files.', lambda current: current.return_from())
    image.intercept(0xe6ab8, 'Observe GF1 sample upload; descriptor flags and addresses are written by original code.', upload)
    rng = random.Random(0xc52d0)
    cases = []
    for case in range(1024):
        ram = (256, 512, 768, 1024)[case % 4]
        count = 256 if case % 127 == 0 else 106 if case % 17 == 0 else 1 + case % 50
        sizes = [rng.choice([0, 1, 32768, 65535, rng.randrange(65536)]) for _ in range(count)]
        if case % 23 == 0:
            sizes = [rng.choice([0, 1, 100])] * count
        if case % 29 == 0:
            # Sixteen equal allocations would fill all remaining RAM exactly.
            sizes = [(ram * 1024 - 32768) // 16] * 16
        cases.append((ram, sizes))
    rows = [[ram, len(sizes), *sizes] for ram, sizes in cases]
    output = subprocess.check_output([str((args.build / 'gus_memory_probe').resolve())],
        input=('\n'.join(' '.join(map(str, row)) for row in rows) + '\n').encode()).decode().splitlines()
    assert len(output) == len(rows)
    fixtures = []
    resident_count = streamed_count = allocations = 0
    for case, ((ram, sizes), line) in enumerate(zip(cases, output)):
        driver.reset(ram)
        for index, size in enumerate(sizes):
            at = 0x9860 + index * 26
            image.cpu.mem_write(image.data + at, bytes(26))
            image.write(at, '<I', image.data + 0x3874)
            image.write(at + 14, '<I', size)
        image.cpu.mem_write(image.data + 0x9860 + len(sizes) * 26, bytes(26))
        image.call(0xc52d0, eax=image.data + 0x9860, limit=5000000)
        uploads.clear()
        image.call(0xc4f5c, eax=image.data + 0x9860, edx=image.native(0xdde2c), limit=5000000)
        expected = []
        for index, size in enumerate(sizes):
            at = 0x9860 + index * 26
            flags = image.read(at + 24, '<H')[0]
            resident = flags & 7 == 7 and size != 0
            expected.append(image.read(at + 18, '<I')[0] if resident else -1)
            resident_count += resident
            streamed_count += bool(size and not resident)
        expected.append(driver.remaining())
        assert len(uploads) == sum(address != -1 for address in expected[:-1]), (case, uploads)
        allocations += len(sizes)
        driver.reset(ram)
        for size in sizes:
            address = driver.allocate(size)
            expected.append(address if address is not None else -1)
        expected.append(driver.remaining())
        actual = list(map(int, line.split()))
        assert actual == expected, (case, ram, sizes, actual, expected)
        if case < 128:
            fixtures.append(rows[case] + expected)
    assert resident_count and streamed_count
    if args.record:
        args.record.write_text('\n'.join(' '.join(map(str, row)) for row in fixtures) + '\n')
    print(f'{len(cases)} complete original sample-RAM plans and {allocations} direct GUS.COM allocations agree: 256/512/768/1024 KiB, pairwise sorting/ties, zero samples, failed-large/successful-small requests, exact-fit rejection and retained addresses; {resident_count} resident and {streamed_count} streamed nonempty samples')


if __name__ == '__main__':
    main()
