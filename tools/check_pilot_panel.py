#!/usr/bin/env python3
"""Compare complete load/save pilot-menu frames with the original painters.

Test-authored pilot summaries and matching DOS saves supply the same records to
both implementations. The archive background is a supplied graphics boundary;
original headings, rows, alignment, shadows, statistics and confirmation prompts
execute unchanged. Disk enumeration, cursor and physical page changes are hosted.
The reference installation and its saves are never changed.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from native_reference import NativeReference, r
from native_vga import VgaCapture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    parser.add_argument('--output', type=Path, help='save matching native/C++ menu screenshots')
    args = parser.parse_args()
    directory = args.research / 'installs/cd_1994_09/TFX'
    schema = next(p for p in json.loads((args.research / 'analysis/presentations/programs.json').read_text()) if p['name'] == 'tfx')
    image = NativeReference(directory / 'TFX.DAT')
    image.call(0xde547)
    cpu = image.cpu
    video = VgaCapture(image)
    background = b''

    def restore_background(im):
        video.reset()
        for plane in range(4):
            video.planes[plane][:] = background[plane::4]
        im.return_from()

    image.intercept(0xca5aa, 'Supply the original archived slot bitmap on the selected capture page.', restore_background)
    for address in (0xc6348, 0xc6f64):
        image.intercept(address, 'Physical VGA page selection and archive bitmap loading are hosted.', lambda im: im.return_from())
    image.intercept(0xd21a4, 'Cursor setup is outside the captured menu text and background.', lambda im: im.return_from(16))

    current_case = (True, 0, False)

    def select_case(im):
        load, selected, confirm = current_case
        cpu.reg_write(r.UC_X86_REG_EDI, selected)
        if confirm:
            frame = cpu.reg_read(r.UC_X86_REG_EBP)
            cpu.mem_write(frame + (0x76 if load else 0x7a), b'\1')

    image.intercept(0xa18d2, 'Supply the selected row and confirmation phase before the original paints its menu.', select_case)

    def native_frame(load, selected, confirm):
        nonlocal current_case
        current_case = (load, selected, confirm)
        cpu.mem_write(image.STACK, struct.pack('<I', image.RETURN))
        cpu.reg_write(r.UC_X86_REG_ESP, image.STACK)
        cpu.reg_write(r.UC_X86_REG_EAX, int(load))
        cpu.reg_write(r.UC_X86_REG_EFLAGS, 0x202)
        cpu.emu_start(image.native(0xa1868), image.native(0xc62d4), count=3000000)
        assert cpu.reg_read(r.UC_X86_REG_EIP) == image.native(0xc62d4)
        return bytes(video.pixels())

    def string(pointer):
        return bytes(cpu.mem_read(pointer, 64)).split(b'\0')[0].decode('ascii')

    ranks = [string(pointer) for pointer in image.read(0x90c0, '<7I')]
    statuses = [string(pointer) for pointer in image.read(0x90dc, '<5I')]
    checked = 0
    with tempfile.TemporaryDirectory(prefix='tfx-pilot-panel-') as temporary:
        saves = Path(temporary)
        records = []
        for slot in range(10):
            if slot in (2, 7, 9):
                records.append(None)
                continue
            values = {v['name']: '' if v['string_value'] else 0 for v in schema['variables']}
            values.update(firstname='SLOW' if slot < 2 else 'ADA', pilotname='RIOT' if slot < 2 else 'LOVELACE', callsign='RIOT' if slot < 2 else 'INFERNO',
                          status=2 if slot == 0 else 0 if slot == 1 else slot % 5, rank=slot % 7,
                          score=slot * 123456, a2akills=slot * 7, a2gkills=slot * 3, num_miss=slot * 11, num_hours=slot * 13)
            records.append(values)
            raw = bytearray()
            for variable in schema['variables']:
                value = values[variable['name']]
                raw.extend(value.encode('ascii').ljust(21, b'\0') if variable['string_value'] else struct.pack('<I', value))
            raw.extend(bytes((30 - len(schema['variables'])) * 4) + struct.pack('<3H', 0, 0xffff, 0xffff))
            (saves / f'TFXSAV.{slot}').write_bytes(raw)
        for slot, record in enumerate(records):
            offset = 0x14a20 + slot * 0x73
            image.write(offset, '<115s', bytes(115))
            if record is None:
                image.write(offset, '<B', 1)
                continue
            for field, name in ((1, 'firstname'), (0x16, 'pilotname'), (0x2b, 'callsign')):
                image.write(offset + field, '<21s', record[name].encode('ascii'))
            image.write(offset + 0x40, '<21s', ranks[record['rank']].encode('ascii'))
            image.write(offset + 0x61, '<10s', statuses[record['status']].encode('ascii'))
            for field, name in ((0x55, 'score'), (0x59, 'a2akills'), (0x5d, 'a2gkills'), (0x6b, 'num_miss'), (0x6f, 'num_hours')):
                image.write(offset + field, '<I', record[name])
        cases = [(load, selected, False) for load in (True, False) for selected in range(10)]
        cases += [(True, slot, True) for slot, record in enumerate(records) if record and record['status'] != 0]
        cases += [(False, slot, True) for slot, record in enumerate(records) if record and record['status'] == 0]
        request = ''.join(f'{int(load)} {selected} {int(confirm)}\n' for load, selected, confirm in cases)
        output = subprocess.check_output([str((args.build / 'pilot_panel_probe').resolve()), str(directory), str(saves)], input=request.encode())
        palette, background = output[:768], output[768:64768]
        assert len(output) == 64768 + len(cases) * 64000
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
        for index, (load, selected, confirm) in enumerate(cases):
            actual = output[64768 + index * 64000:64768 + (index + 1) * 64000]
            expected = native_frame(load, selected, confirm)
            differences = [(at % 320, at // 320, a, b) for at, (a, b) in enumerate(zip(actual, expected)) if a != b]
            if args.output and load and selected == 7 and not confirm:
                from PIL import Image
                for name, pixels in (('cpp', actual), ('original', expected)):
                    rendered = Image.frombytes('P', (320, 200), pixels)
                    rendered.putpalette(palette)
                    rendered.convert('RGB').resize((1280, 960), Image.Resampling.NEAREST).save(args.output / f'pilot-load-{name}.png')
            assert not differences, (load, selected, confirm, len(differences), differences[:12])
            checked += 1
    print(f'{checked} complete original pilot-menu frames agree pixel for pixel: load/save, every selected row, empty/occupied slots, rank/status, statistics, and overwrite/delete prompts')


if __name__ == '__main__':
    main()
