#!/usr/bin/env python3
"""Compare entire GF1 PCM streams and queues with original TFX + GUS.COM.

The real-mode client callback is copied/patched by original TFX and executes
unchanged on wave IRQs. Uses declared test-authored sample files; no original
game data is included in recorded fixtures. No desktop audio device is opened.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
import sys
from native_reference import NativeReference
from native_gus_samples import GusSamplesReference


def pcm_hash(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--record', type=Path, help='record test-authored INPUT and INPUT.expected')
    parser.add_argument('--retail', action='store_true', help='also use all 106 original sample slots, without recording game assets')
    parser.add_argument('--rate', type=int, default=44100, help='host PCM rate; native GF1 clock remains 44100')
    args = parser.parse_args()
    synthetic = args.record is not None
    if args.record and (args.retail or args.rate != 44100):
        parser.error('fixtures use test-authored PCM at the native mixer rate')
    metadata = [(7500, 0, 1024, 17), (8363, 18, 513, 74), (11025, -1, 11025, 11),
                (9000, 100, 4095, 93), (22050, 1, 32767, 19), (7500, 0, 1, 127),
                (8000, 0, 3, 193), (16000, 2, 15, 37), (7500, 0, 16, 53),
                (30000, 0, 17, 83), (11025, 0, 511, 23), (7500, 0, 0, 0)]
    samples = [(rate, delay, bytes((index * 37 + seed) & 255 for index in range(length)))
               for rate, delay, length, seed in metadata]
    if args.retail:
        directory = args.research / 'installs/cd_1994_09/TFX'
        sys.path.insert(0, str(args.research / 'did-unpack'))
        from did_unpack import Archive
        archive = Archive.read(directory / 'DID.DAT')
        entries = {entry.identifier: entry for entry in archive.entries}
        image = NativeReference(directory / 'TFX.DAT')
        samples = []
        for index in range(106):
            at = 0x9860 + index * 26
            name = bytes(image.cpu.mem_read(image.read(at, '<I')[0], 9)).split(b'\0')[0].decode()
            rate, delay = image.read(at + 4, '<Hh')
            pcm = archive.unpack(entries[archive.hash_name(f'samples/{name}.sam')]) if name else b''
            samples.append((rate, delay, pcm))
    commands = ['s 2 2 0 1', 'r 12000', 's 1 1 2', 's 2 2 3 0', 's 0 1 4',
                's 1 1 0', 'r 1200', 'e 0', 's 2 1 5', 'r 3000', 'e 1', 'a 18']
    rng = random.Random(0xddf68)
    for _ in range(64):
        sequence = [rng.randrange(len(samples)) for _ in range(rng.randrange(1, 9))]
        commands += [f's {rng.randrange(3)} {len(sequence)} ' + ' '.join(map(str, sequence)),
                     f'r {rng.choice([1, 2, 13, 127, 300, 1024, 2048])}', f'a {rng.choice([0, 1, 18, 100, 65535])}']
    commands += ['s 2 30 ' + ' '.join(['0', '1'] * 15), 'r 180000', 'r 1']
    if args.retail:
        commands += [word for index in range(len(samples)) for word in (f'a 32767', f's 2 1 {index}', 'r 1024')]
        commands += ['r 220500']
    header = ['retail'] if args.retail else [str(len(metadata)), *(' '.join(map(str, row)) for row in metadata)]
    text = '\n'.join(header + commands) + '\n'
    original, expected = bytearray(), []
    output_frame, chip_frame, held = 0, -1, (0, 0)
    with GusSamplesReference(args.research / 'installs/cd_1994_09/TFX', samples, args.build, synthetic) as native:
        for command in commands:
            words = command.split()
            pcm = b''
            if words[0] == 's':
                native.submit(int(words[1]), list(map(int, words[3:])))
            elif words[0] == 'e':
                native.enable(int(words[1]))
            elif words[0] == 'a':
                native.advance(int(words[1]))
            elif words[0] == 'r':
                converted = bytearray()
                for _ in range(int(words[1])):
                    required = output_frame * 44100 // args.rate
                    while chip_frame < required:
                        held = native.sample()
                        chip_frame += 1
                    converted += struct.pack('<2f', *(value / 32768 for value in held))
                    output_frame += 1
                pcm = bytes(converted)
                original += pcm
            expected.append(' '.join(map(str, [*native.state(), pcm_hash(pcm)])))
    reference = args.build / 'gus-samples-native.pcm'
    reference.write_bytes(original)
    if args.record:
        args.record.write_text(text)
        args.record.with_suffix('.expected').write_text('\n'.join(expected) + '\n')
        result = subprocess.run([str((args.build / 'gus_samples_probe').resolve()), '--synthetic',
            str(args.record), str(args.record.with_suffix('.expected'))], capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
    else:
        capture = args.build / 'gus-samples-cpp.pcm'
        result = subprocess.run([str((args.build / 'gus_samples_probe').resolve()),
            str(args.research / 'installs/cd_1994_09/TFX/GUS.COM'), str(capture), str(args.rate)],
            input=text.encode(), capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
        actual = result.stdout.decode().splitlines()
        assert len(actual) == len(expected), (len(actual), len(expected))
        for index, (found, wanted) in enumerate(zip(actual, expected)):
            assert found == wanted, (index, commands[index], found, wanted)
        assert capture.read_bytes() == original, 'complete GF1 PCM differs'
    print(f'{len(commands)} complete original Gravis requests/timer updates/callbacks agree, {len(original) // 8} stereo frames at {args.rate} Hz: every PCM sample, resident rotation/busy rejection, priorities, signed cooldowns, disabled submissions, unaligned DMA overlap and a 30-item IRQ-chained queue'+('; all 106 retail slots / 103 PCM resources' if args.retail else ''))


if __name__ == '__main__':
    main()
