#!/usr/bin/env python3
"""Compare accelerated-time requests, steering gates and radio state with DOS 2.05.

The original input/controller executes. A declared already-acquired six-word
steering state is supplied in designator view, which skips raw-key acquisition.
The player physics callback is the output boundary; all later numerical warp
behaviour has its separate native flight/clock comparisons.
"""
import argparse
from pathlib import Path
import subprocess
from native_reference import NativeReference

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--save-fixture',type=Path)
a = p.parse_args()
im = NativeReference(a.data_dir/'TFX.DAT')
im.cpu.mem_map(0x300000,4096)
im.write(0x1b238,'<I',0x300000)
im.write(0x1b23c,'<I',0x300100)
im.write(0x12bcc,'<I',im.native(0x75954))
im.dependencies[0x75954] = 'Original empty return stands at the player physics output boundary; no numerical flight runs in this control comparison.'
im.write(0x87b6,'<H',19)
im.call(0x839d0)
im.cpu.mem_write(0x300200,b'PREVIOUS MESSAGE\0')
rows = []
expected = []
for requested in range(2):
 for toggle in range(2):
  for steering in range(64):
   for autopilot in range(2):
    for mode in (0,1,4,5):
     persistent = (steering+mode)%2
     source = [requested,toggle,steering,autopilot,mode,persistent]
     im.call(0x81198 if not persistent else 0x81254,eax=0x300200)
     im.write(0x13248,'<H',requested)
     im.write(0x14958,'<H',autopilot)
     im.write(0x14960,'<H',mode)
     for bit,address in enumerate((0x13256,0x1325c,0x13258,0x1325e,0x1323e,0x13240)):
      im.write(address,'<H',bool(steering & (1<<bit)))
     im.cpu.mem_write(0x300000,bytes([0x14 if toggle else 0]))
     im.call(0x86898)
     result = [im.read(at,fmt)[0] for at,fmt in ((0x13248,'<H'),(0xe780,'<B'),(0x7612,'<B'),(0x7613,'<B'),(0x7614,'<B'))]
     rows.append(source)
     expected.append(result)
request = ''.join(' '.join(map(str,row))+'\n' for row in rows)
output = subprocess.check_output([str((a.build/'acceleration_probe').resolve())],input=request.encode()).decode().splitlines()
assert len(output)==len(expected)
for source,want,line in zip(rows,expected,output):
 got=list(map(int,line.split()))
 assert got==want,(source,got,want)
if a.save_fixture:
 indices=list(range(0,len(rows),17))
 a.save_fixture.write_text(''.join(' '.join(map(str,rows[i]+expected[i]))+'\n' for i in indices))
 subprocess.run([str((a.build/'acceleration_probe').resolve()),str(a.save_fixture)],check=True)
print(f'{len(rows)} original accelerated-time requests, steering/autopilot gates and retained radio states agree')
