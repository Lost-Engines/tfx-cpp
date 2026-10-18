#!/usr/bin/env python3
"""Boot original GUS.COM on GF1 hardware and exercise actual DMA/wave IRQs.

This checks the reference host and hardware integration, not a physical card
recording or a C++ replacement for the driver. Uploads use test-authored PCM;
no installation, desktop audio device or user configuration is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from native_gus_device import GusDeviceReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--output', type=Path, help='optional small JSON evidence manifest')
    args = parser.parse_args()
    results = []
    for ram in (256, 512, 768, 1024):
        with GusDeviceReference(args.research / 'installs/cd_1994_09/TFX/GUS.COM', args.build, ram) as driver:
            driver.boot()
            assert driver.remaining() == ram * 1024 - 32768
            assert bytes(driver.cpu.mem_read(driver.data + 0x2b5, 1)) == bytes([32])
            driver.events.clear()
            uploads = []
            expected_memory = {}
            for index, size in enumerate((1, 3, 15, 16, 17, 511, 1024, 4095, 11025, 32767, 46354, 65535)):
                address = driver.allocate(size)
                assert address is not None
                pcm = bytes((sample * 37 + index * 17 + 11) & 255 for sample in range(size))
                driver.cpu.mem_write(0x70000, pcm)
                driver.command(0, address, 0x70000000, size)
                uploads.append((address, pcm))
                # GUS.COM writes only address >> 4 to the GF1 DMA register.
                # The allocator does not align addresses: later uploads can
                # overwrite up to fifteen bytes of the preceding sample.
                for offset, value in enumerate(pcm):
                    expected_memory[(address & ~15) + offset] = value ^ 128
            memory = bytearray()
            for position, expected in sorted(expected_memory.items()):
                driver.library.gf1_write(driver.chip, 0x343, 1, 0x43)
                driver.library.gf1_write(driver.chip, 0x344, 2, position & 65535)
                driver.library.gf1_write(driver.chip, 0x343, 1, 0x44)
                driver.library.gf1_write(driver.chip, 0x345, 1, position >> 16)
                actual = driver.library.gf1_read(driver.chip, 0x347, 1)
                assert actual == expected, (ram, position, actual, expected)
                memory.append(actual)
            address, pcm = uploads[6]
            driver.command(2, 1, 256)
            driver.command(1, 1, address, address + len(pcm), 7500)
            output = [driver.sample() for _ in range(14000)]
            assert any(left or right for left, right in output)
            assert any(left != right for left, right in output)
            assert driver.command(4, 1)[1] == 1
            assert all(pair == (0, 0) for pair in output[-100:])
            rendered = b''.join(struct.pack('<2h', *pair) for pair in output)
            results.append({'ram_kib': ram, 'uploaded_bytes': len(memory),
                            'dram_sha256': hashlib.sha256(memory).hexdigest(),
                            'pcm_sha256': hashlib.sha256(rendered).hexdigest(),
                            'last_nonzero_frame': max(index for index, pair in enumerate(output) if pair != (0, 0))})
    assert len({result['pcm_sha256'] for result in results}) == 1, results
    if args.output:
        args.output.write_text(json.dumps(results, indent=2) + '\n')
    print('Original GUS.COM boot, detected RAM, every signed PCM upload byte, unaligned DMA, resident playback, wave IRQ and stereo/stopped tail pass for 256/512/768/1024 KiB; render hashes agree')


if __name__ == '__main__':
    main()
