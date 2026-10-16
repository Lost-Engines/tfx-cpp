#!/usr/bin/env python3
"""Compare environment palette bindings against independent native parser captures."""
import argparse
import json
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();captures=json.loads((a.research/'analysis/lighting/environments.json').read_text())['environments'];cases=[c for c in captures if c['status']=='decoded']
rows=subprocess.check_output([str((a.build/'environment_palette_probe').resolve()),str(a.research/'installs/cd_1994_09/TFX')],input=('\n'.join(c['environment'] for c in cases)+'\n').encode()).decode().splitlines();assert len(rows)==len(cases)
for capture,row in zip(cases,rows):
    banks={bank['data_offset']:Path(bank['name']).stem for bank in capture['banks']}
    expected=[banks[offset] for offset in ('0x21000','0xf688','0xf388','0xf088','0xed88')]
    expected.extend(str(capture['distance_fields'][offset]) for offset in ('0x10bc8','0x10bd0','0x10bcc','0x10b9c','0x10b98'))
    expected.extend([banks['0xea88'],Path(capture['schematic'].replace('\\','/')).stem,str(128 if capture['night_flag'] else 0)])
    assert row.split()==expected,(capture['environment'],row,expected)
print(f'All five altitude palettes/boundaries, infrared, schematic and night bindings agree for {len(cases)} native environment captures')
