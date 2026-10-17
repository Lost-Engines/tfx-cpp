#!/usr/bin/env python3
"""Render recorded model queues through the original post-flight frame path.

Starts with a bounded original flight, then executes native 3D-mode/viewport
setup, REC open/dictionary/handle remapping, each frame reader, horizon, queue
flush and blinking PLAY text. Animation prefaces, display flips and four-tick
waiting are outside this pixel capture. DOS files remain capture-owned memory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import struct
import sys
from check_recording_session import CASES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--case', choices=CASES, default='camera')
    p.add_argument('--recording', type=Path, help='instead play this file, using the captured original context')
    a = p.parse_args()
    root = a.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    mission, frames, inputs = CASES[a.case]
    tape = root / 'inputs.json'
    tape.write_text(json.dumps(inputs, indent=2) + '\n')
    sys.argv = ['capture_native_flight.py', '--research', str(a.research.resolve()),
                '--output', str(root), '--mission', str(mission), '--frames', str(frames),
                '--inputs', str(tape)]
    source = runpy.run_path(str(Path(__file__).with_name('capture_native_flight.py')), run_name='__main__')
    image, video = source['im'], source['video']
    files = source['memory_files']
    if a.recording:
        files.files['video.rec'] = bytearray(a.recording.read_bytes())
        recording = a.recording.resolve()
    else:
        recording = root / 'recording-0.rec'
    code = lambda offset: image.native(0x70aa4 + offset)
    # Native 7B3B5..7B3E4; the two preceding animation players are a
    # separately identified caller, not silently replaced by this capture.
    image.call(0xc7588)
    image.call(0x7b214, eax=0, edx=319, ebx=0, ecx=199)
    image.call(0xca780)
    if not image.call(0xc5e60, eax=image.data + 0x8868) & 255:
        raise RuntimeError('original replay reader rejected the recording')
    count = image.read(0xac98, '<H')[0]
    camera_y, = struct.unpack('<h', image.cpu.mem_read(code(0x47c08), 2))
    phase = image.read(0xad7c, '<h')[0]
    seed, = struct.unpack('<H', image.cpu.mem_read(image.native(0xe3a3f), 2))
    entries = image.read(0xad28, '<H')[0]
    ids = image.read(0x21870, f'<{entries}H')
    table = image.read(0x23f80, '<I')[0]
    names = {0: '', 1: 'badshape'}
    for i in range(2, entries):
        pointer, = struct.unpack('<I', image.cpu.mem_read(table + i * 4, 4))
        names[ids[i]] = source['string'](pointer)
    carried = struct.unpack('<10H', image.cpu.mem_read(code(0x47c94), 20))
    carried = [names[handle] if handle != 65535 else '' for handle in carried]
    carried = [name.replace('\\', '/').rsplit('/', 1)[-1].lower().removesuffix('.3') for name in carried]
    animation = image.read(0xac90, '<B')[0]
    status, = struct.unpack('<H', image.cpu.mem_read(code(0x47c82), 2))
    context = {'mission': mission, 'camera_y': camera_y, 'ground_phase': phase,
               'pattern_seed': seed, 'animation': animation, 'status': status, 'carried': carried,
               'recording': str(recording), 'recording_sha256': hashlib.sha256(recording.read_bytes()).hexdigest(),
               'frames': count, 'scope': __doc__}
    (root / 'playback.json').write_text(json.dumps(context, indent=2) + '\n')
    (root / 'context.txt').write_text(' '.join(map(str, (mission, camera_y, phase, seed, animation, status))) + '\n' +
                                    '\n'.join(json.dumps(name) for name in carried) + '\n')
    (root / 'infrared.dac').write_bytes(image.cpu.mem_read(image.data + 0xea88, 768))
    image.call(0xc7370)
    for index in range(count):
        image.call(0xc488d)
        image.call(0xc6178, limit=10000000)
        pitch, heading, roll = struct.unpack('<3H', image.cpu.mem_read(code(0x47c20), 6))
        image.call(0xcaf84, eax=pitch, edx=roll, limit=5000000)
        image.call(0xc48e1, limit=30000000)
        if not index % 2:
            image.call(0x7b2a8, eax=284, edx=0, ebx=image.data + 0x1344)
        (root / f'replay-{index}.indices').write_bytes(video.pixels())
    image.call(0xc61fc)
    print(f'{count} original replay frames captured with inherited camera height, ground phase, drawing seed and carried-model bindings; {root}', flush=True)


if __name__ == '__main__':
    main()
