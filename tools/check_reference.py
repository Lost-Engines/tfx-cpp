#!/usr/bin/env python3
"""Compare the C++ loaders against every externally retained reference resource."""
import argparse
from pathlib import Path
import struct
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, default=Path('build'))
parser.add_argument('--research', type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.research / 'did-unpack'))
from did_unpack import Archive

archive_path = args.research / 'installs/cd_1994_09/TFX/DID.DAT'
archive = Archive.read(archive_path)
result = subprocess.run([str((args.build / 'tfx_probe').resolve()), 'archive', str(archive_path)], check=True, capture_output=True).stdout
count, = struct.unpack_from('<I', result)
assert count == len(archive.entries)
at = 4
for entry in archive.entries:
    identifier, size = struct.unpack_from('<II', result, at)
    at += 8
    assert identifier == entry.identifier
    assert result[at:at + size] == archive.unpack(entry), f'payload differs: {identifier:08x}'
    at += size
assert at == len(result)
print(f'Byte-exact archive comparison passed: {count} resources')
