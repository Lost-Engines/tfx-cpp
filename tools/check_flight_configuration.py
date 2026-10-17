#!/usr/bin/env python3
"""Compare original weapon-key flight configuration and stored response bits.

Original Enter and F bodies execute. Store selection is supplied at its existing
armament boundary; sample delivery is observed without playing audio. No flight
numerical routine is replaced. Complete-session checks cover actual selection,
key acquisition, steering and camera/HUD integration separately.
"""
import argparse
from pathlib import Path
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args()
im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT')
im.intercept(0x8b9c4,'Supply a valid selected pylon at the independently checked armament boundary.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,2),current.return_from()))
notices=[]
im.intercept(0xa4edc,'Observe the original selection sample without host playback.',lambda current:(notices.append(current.cpu.reg_read(r.UC_X86_REG_EAX)),current.return_from()))
rows=[]
for craft in (1,2,3):
 for model in (0,1,2,6):
  for configuration,function in ((0,0x84598),(1,0x846e8)):
   for field,fmt,value in ((0x11b2a,'<H',craft-1),(0x1347a,'<B',model),(0xabe9,'<B',0),(0x12c04,'<H',0),(0x86ce,'<B',0),(0x93b0,'<h',0)):
    im.write(field,fmt,value)
   notices.clear();im.call(function)
   assert notices==[8],(craft,model,configuration,notices)
   expected=[im.read(0x14962,'<H')[0],*[im.read(field,'<Q')[0]for field in (0x14360,0x148b8,0x148b0,0x148a8)]]
   rows.append([craft,model,configuration,*expected])
request=''.join(' '.join(map(str,row[:3]))+'\n'for row in rows)
actual=subprocess.check_output([str((a.build/'flight_configuration_probe').resolve())],input=request.encode()).decode().splitlines()
assert len(actual)==len(rows)
for row,line in zip(rows,actual):assert list(map(int,line.split()))==row[3:],(row,line)
if a.record:a.record.write_text(''.join(' '.join(map(str,row))+'\n'for row in rows))
print(f'{len(rows)} original weapon-key configurations agree: three aircraft, four flight models, combat/cruise configuration and all four response double bit patterns.')
