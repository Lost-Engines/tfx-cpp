#!/usr/bin/env python3
"""Compare the original post-contact controller, with supplied SSD hit state.

Native 0x7145d..0x71535 executes every branch and state write. SSD state and
model/camera/sample outputs are explicit boundaries; geometric collision and
the subsequent loss controller have their own complete native comparisons.
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
a=p.parse_args();rng=random.Random(0x7145d)
im=NativeReference(a.data_dir/'TFX.DAT');destroyed=[0];events=[]
im.intercept(0xb6e88,'Supply post-query SSD fatal state; the transition executes without substitution.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,destroyed[0]),im.return_from()))
im.intercept(0xb52d4,'Capture the selected SSD handle and entry, not its separately checked bytecode.',lambda im:(events.extend([1,im.cpu.reg_read(r.UC_X86_REG_EAX),im.cpu.reg_read(r.UC_X86_REG_EDX)]),im.return_from()))
im.intercept(0x8fd84,'Capture the queued native camera mode; its motion has separate comparisons.',lambda im:(events.extend([0,im.cpu.reg_read(r.UC_X86_REG_EAX)]),im.return_from()))
im.intercept(0xa4f2c,'Capture the independently checked fixed explosion sample helper.',lambda im:(events.extend([2,12]),im.return_from()))
im.intercept(0x71535,'Stop at the declared post-contact boundary, before refueller contact and loss processing.',lambda im:im.return_from())
rows=[];expected=[];fixtures=[]
for case in range(8192):
 prior=case&1;fatal=(case>>1)&1;special=(case>>2)&1;pilot=(case>>3)&1
 disabled=rng.randrange(2);collision=rng.choice([-1,0,1,2,32767]);ticks=rng.choice([-32768,-1,0,1,199,200,32767]);hold=rng.choice([-32768,-1,0,1,32767]);legacy=rng.choice([-32768,-1,0,1,32767])
 row=[prior,fatal,special,pilot,disabled,collision,ticks,hold,legacy];rows.append(row);destroyed[0]=fatal;events.clear()
 for at,fmt,value in [(0xe76c,'<H',3 if special else 1),(0x12c00,'<H',3),(0xe784,'<B',pilot),(0x86ce,'<B',disabled),(0x12c04,'<h',collision),(0x12c02,'<h',ticks),(0x86f8,'<h',hold),(0xe758,'<h',legacy)]:im.write(at,fmt,value)
 im.cpu.reg_write(r.UC_X86_REG_ESI,prior);im.call(0x7145d)
 value=[im.read(0x86ce,'<B')[0],im.read(0x12c04,'<h')[0],im.read(0x12c02,'<h')[0],im.read(0x86f8,'<h')[0],im.read(0xe758,'<h')[0],int(im.read(0xe76c,'<H')[0]==3),len(events),*events];expected.append(value)
 if case<256:fixtures.append(row+value)
result=subprocess.check_output([str((a.build/'player_contact_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode()).decode().splitlines()
assert len(result)==len(expected)
for case,(line,value) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==value,(case,rows[case],line,value)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print('8192 native post-contact transitions agree: prior fatal restoration, new/repeated fatal contacts, pilot and kapow gates, collision, motion hold, countdown and ordered camera/model/explosion outputs')
