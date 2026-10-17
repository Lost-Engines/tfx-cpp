#!/usr/bin/env python3
"""Compare environment palette/map bindings with the independent native parser captures."""
import argparse
import json
from pathlib import Path
import subprocess
from native_environment import environment_image

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX'
records=json.loads((args.research/'analysis/lighting/environments.json').read_text())['environments']
grids={'yugosmap':'yugoslav','libyamap':'libya','colummap':'columbia','somalmap':'somalia','seamap':'seaworld'}
cases=[row for row in records if row['status']=='decoded']
requests=[];expected=[]
for row in cases:
    map_name=row['schematic'].replace('\\','/').rsplit('/',1)[-1].removesuffix('.spr')
    requests.append(grids[map_name]+' '+row['environment'])
    image=environment_image(args.research,row['environment'])
    assert bool(image.read(0x5951,'<B')[0]) == (not bool(int(row['night_flag']))),row['environment']
    layered=image.read(0xe762,'<H')[0]!=0
    grid=bytes(image.cpu.mem_read(image.data+0xe6a0,64)).split(b'\0')[0].decode() if layered else ''
    expected.append([int(row['night_flag'])*128,row['banks'][0]['name'].rsplit('/',1)[-1].removesuffix('.col'),map_name,int(int(str(row['flags']),0)&64!=0),int(layered),image.read(0xe75a,'<h')[0] if layered else 0,image.read(0xe760,'<h')[0] if layered else 0,grid])
output=subprocess.check_output([str((args.build/'tfx_probe').resolve()),'environment_bindings',str(directory)],input=('\n'.join(requests)+'\n').encode()).splitlines()
assert len(output)==len(expected)
for row,got,want in zip(cases,output,expected):assert json.loads(got)==want,(row['environment'],got,want)
print(f'Palette, night/day-glare flags, schematic and original altitude-layer bindings agree for all {len(cases)} decoded native environments')
