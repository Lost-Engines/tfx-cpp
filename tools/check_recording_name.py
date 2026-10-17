#!/usr/bin/env python3
"""Compare filename edits and whole option-dialog pixels with original TFX.

Clicks and scan codes enter through hosted DOS device input. Original widget
focus, key translation, editing, limits, scrolling and drawing all execute.
"""
import argparse
import json
from pathlib import Path
import subprocess
from native_recording_name import RecordingName


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    p.add_argument('--build', type=Path, default=Path('build'))
    a = p.parse_args()
    executable = a.research / 'installs/cd_1994_09/TFX/TFX.DAT'
    cases = [
        [(scan, shift) for scan in (30, 48, 46, 14, 14, 28) for shift in (False,)],
        [(14, False)] * 15 + [(scan, False) for scan in (19, 18, 44, 24, 19, 32, 52, 19, 18, 46, 28)],
        [(17, True)] * 28 + [(14, False)] * 25 + [(30, False), (28, False)],
        [(scan, shift) for shift in (False, True) for scan in (2, 3, 4, 12, 13, 26, 27, 39, 40, 41, 43, 51, 52, 53)],
    ]
    request = ''.join(str(len(case)) + '\n' + ''.join(f'{scan} {int(shift)}\n' for scan, shift in case) for case in cases)
    result = subprocess.check_output([str((a.build / 'recording_name_probe').resolve()), str(executable)], input=request.encode())
    at = 0
    checked = 0
    for case in cases:
        native = RecordingName(executable)
        native.click()
        for scan, shift in case:
            native.press(scan, shift)
            end = result.index(b'\n', at)
            name = json.loads(result[at:end])
            pixels = result[end + 1:end + 1 + 64000]
            at = end + 1 + 64000
            expected, editing = native.value()
            assert name.encode('cp437') == expected, (checked, scan, name, expected, editing)
            original = native.video.pixels()
            differences = sum(a != b for a, b in zip(pixels, original))
            assert not differences, (checked, scan, differences, 'different pixels')
            checked += 1
    assert at == len(result)
    print(f'{checked} original filename edits and complete dialog frames agree: typing, shifted/unshifted case, backspace, empty/full names, scrolling and Enter')


if __name__ == '__main__':
    main()
