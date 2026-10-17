#!/usr/bin/env python3
"""Compare the complete original ECM, stealth and player decoy key handlers.

All inventory/mode gates and target-clearing writes execute unchanged. The
countermeasure constructors are observed output boundaries; their population,
diversion/random consumption and motion have separate native comparisons.
"""
import argparse
from pathlib import Path
import random
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0x86124);im=NativeReference(a.data_dir/'TFX.DAT')
events=[]
def release(image,radar):
 assert image.cpu.reg_read(r.UC_X86_REG_EAX)==image.data+0x10f28
 events.append((radar,image.cpu.reg_read(r.UC_X86_REG_EDX)));image.return_from()
im.intercept(0xa353c,'Observe chaff launch and strength; projectile diversion is checked separately.',lambda image:release(image,1))
im.intercept(0xa3588,'Observe flare launch and strength; projectile diversion is checked separately.',lambda image:release(image,0))
cases=[];expected=[];fixtures=[]
for index in range(8192):
 row=[index%4,1+(index//4)%3,rng.choice([0,1,15,255,rng.randrange(256)]),rng.choice([0,1,15,255,rng.randrange(256)]),rng.randrange(2),rng.randrange(2),*[int(rng.randrange(8)==0)for _ in range(3)],rng.choice([0,1,2,255])]
 key,aircraft,chaff,flares,ecm,stealth,ejecting,collision,disabled,afterburner=row
 for at,fmt,value in [(0x11b2a,'<H',aircraft),(0x6c3e,'<B',chaff),(0x6c3f,'<B',flares),(0x12f29,'<B',ecm),(0x12f26,'<B',stealth),(0xabe9,'<B',ejecting),(0x12c04,'<H',collision),(0x86ce,'<B',disabled),(0x1496d,'<B',afterburner),(0x11108,'<I',0x300000),(0x135c8,'<I',0x300100),(0x135d0,'<I',0x300200)]:im.write(at,fmt,value)
 events.clear();im.call((0x85f50,0x86258,0x86124,0x86168)[key])
 cleared=[im.read(at,'<I')[0]==0 for at in (0x11108,0x135c8,0x135d0)];assert len(set(cleared))==1
 assert len(events)<=1
 values=[*im.read(0x6c3e,'<2B'),im.read(0x12f29,'<B')[0],im.read(0x12f26,'<B')[0],int(cleared[0]),len(events)]
 if events:values.extend(events[0])
 cases.append(row);expected.append(values)
 if index<256:fixtures.append(' '.join(map(str,row+values)))
result=subprocess.check_output([str((a.build/'defence_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in cases)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for index,(line,values) in enumerate(zip(result,expected)):
 actual=list(map(int,line.split()));assert actual==values,(index,cases[index],actual,values)
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(cases)} complete original defensive-key states agree, including aircraft restrictions, ECM/stealth exclusion, target clearing, inventory and loss gates, and afterburner-dependent decoy strengths')
