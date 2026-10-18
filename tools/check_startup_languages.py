#!/usr/bin/env python3
"""Check saved LANG and explicit language overrides at the real front-end entry.

Expected names come from the original executable's language-directory table,
also consumed by its caption loader at B165B. GDB only observes the selected
language; the ordinary CLI/configuration loaders and headless enrolment run.
Original installations are never written.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from native_reference import NativeReference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', type=Path, default=Path('../tfx-reverse'))
    parser.add_argument('--build', type=Path, default=Path('build'))
    args = parser.parse_args()
    original = (args.research / 'installs/cd_1994_09/TFX').resolve()
    image = NativeReference(original / 'TFX.DAT')
    names = [bytes(image.cpu.mem_read(pointer, 24)).split(b'\0')[0].decode('ascii').rstrip('\\')
             for pointer in image.read(0xab1c, '<6I')][1:]
    with tempfile.TemporaryDirectory(prefix='tfx-startup-languages-') as temporary:
        root = Path(temporary)
        for name in ('DID.DAT', 'TFX.DAT'):
            (root / name).symlink_to(original / name)
        observer = root / 'observe.gdb'
        observer.write_text('''set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
break tfx::platform::play_game
commands
silent
printf "TFX_STARTUP_LANGUAGE:%s\\n", language._M_dataplus._M_p
continue
end
run
''')
        environment = dict(os.environ)
        environment['ASAN_OPTIONS'] = environment.get('ASAN_OPTIONS', '') + ':detect_leaks=0'
        for number, name in enumerate(names, 1):
            (root / 'TFX.CFG').write_bytes(f'LANG={number}\r\nSOUNDFX=0\r\nMUSIC=0\r\n'.encode())
            for override in (None, names[number % len(names)]):
                expected = override or name
                command = ['gdb', '--quiet', '--batch', '--return-child-result', '-x', str(observer),
                           '--args', str((args.build / 'tfx').resolve()), '--data-dir', str(root),
                           '--skip-intro', '--frames', '2', '--screenshot', str(root / 'enrol.ppm')]
                if override:
                    command += ['--language', override]
                result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, timeout=30)
                output = result.stdout + result.stderr
                selected = [line.removeprefix('TFX_STARTUP_LANGUAGE:') for line in output.splitlines()
                            if line.startswith('TFX_STARTUP_LANGUAGE:')]
                assert result.returncode == 0 and 'exited normally' in output and 'ERROR:' not in output, output[-3000:]
                assert selected == [expected], ('saved LANG', number, 'override', override, 'selected', selected, 'original directory', name)
    print('All five original saved languages and five explicit overrides reach the real front end correctly')


if __name__ == '__main__':
    main()
