#!/usr/bin/env python3
"""Compare the original automatic descent warning/recovery producer.

The bounded original 0x991e9..0x992f8 region and complete 0x85a7c engagement
handler execute. Synthetic caller scratch is supplied; only sound/radio/model
output delivery is intercepted. Both original return paths are observed.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x991e9);events=[]
for file,kind in ((0xa4dfc,'play'),(0xa4edc,'sound'),(0xb52d4,'model'),(0x81198,'radio'),(0x7dde4,'warning')):
 def callback(image,kind=kind):
  events.append((kind,image.cpu.reg_read(r.UC_X86_REG_EAX)));image.return_from()
 im.intercept(file,'Observe '+kind+' delivery without substituting prediction/recovery',callback)
for file in (0x99297,0x992f8):im.cpu.hook_add(UC_HOOK_CODE,lambda cpu,address,size,unused:cpu.emu_stop(),begin=im.native(file),end=im.native(file))
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0];fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];cases=[]
for i in range(8192):
 stages=rng.choice([0,4]);after=rng.randrange(stages+1)
 flags=[int(i%2==0),int(i%13==0),int(i%17==0),int(i%19==0),int(i%23==0)]
 velocity=rng.choice([-.1,0,.099999,.1,.100001,1,50,200])
 crossing=rng.choice([-1,0,4.999999,5,5.000001,6,6.999999,7,7.000001,7.999999,8,8.000001,20])
 cases.append([*flags,stages,rng.randrange(8),rng.randrange(8),rng.randrange(5),rng.randrange(4),i%2,(i//2)%2,rng.choice([1,2,11,14]),rng.choice([1,2,11,14]),after,0,rng.randrange(4),rng.randrange(4),(i//4)%2,fbits(rng.uniform(0,1)),*map(bits,[rng.uniform(0,1),rng.uniform(0,1),1,1,1000]),*map(bits,[-velocity*crossing,velocity,rng.choice([199.999,200,200.001,400]),rng.choice([0,-0.,.0001,.5,1])]),rng.choice([1,2,11,14])])
output=subprocess.check_output([str((a.build/'aerodynamic_recovery_probe').resolve()),'--descent'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];engaged=warnings=0
for index,(row,line) in enumerate(zip(cases,output)):
 available,inhibited,crashed,ejected,landed,stages,configuration,saved_configuration,mode,saved_mode,enabled,saved_enabled,brake,saved_brake,after,saved,control,display,pending,throttle,saved_throttle,target,left,right,fuel=row[:25]
 down,velocity,speed,gear,condition=row[25:];craft=1 if stages==0 else 0
 for field,value,fmt in ((0x8867,available,'<B'),(0xabe9,inhibited,'<B'),(0x12c04,crashed,'<H'),(0x86ce,ejected,'<B'),(0x8d3a,landed,'<H'),(0x11b2a,craft,'<H'),(0x8cd8+craft,stages,'<B'),(0x14962,configuration,'<H'),(0x1327a,saved_configuration,'<H'),(0x14960,mode,'<H'),(0x1327c,saved_mode,'<H'),(0x14958,enabled,'<H'),(0x1327e,saved_enabled,'<H'),(0x7d77,brake,'<B'),(0x13278,saved_brake,'<H'),(0x1496d,after,'<B'),(0x13269,saved,'<B'),(0x10bed,control,'<B'),(0x6c38,display,'<B'),(0x1347b,255 if pending else 1,'<B'),(0x133f8,throttle,'<I'),(0x13270,saved_throttle,'<Q'),(0x14890,target,'<Q'),(0x14880,left,'<Q'),(0x14888,right,'<Q'),(0x14858,fuel,'<Q'),(0x14768,down,'<Q'),(0x14830,velocity,'<Q'),(0x14700,speed,'<Q'),(0x146d8,gear,'<Q'),(0x7d7a,condition,'<B')):im.write(field,fmt,value)
 im.write(0xe76c,'<H',23);events.clear();im.cpu.reg_write(r.UC_X86_REG_EBP,im.STACK+0x200);im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x991e9),im.RETURN,count=200000)
 assert im.cpu.reg_read(r.UC_X86_REG_EIP) in (im.native(0x99297),im.native(0x992f8))
 change=int(mode!=4 and im.read(0x14960,'<H')[0]==4);warning=int(('play',0x3d) in events)
 assert events==([('play',0x3e),('radio',im.data+0x1990)] if change else [('play',0x3d),('warning',im.data+0x6f12)] if warning else []),(index,events)
 expected=[im.read(field,fmt)[0] for field,fmt in ((0x14962,'<H'),(0x1327a,'<H'),(0x1327c,'<H'),(0x1327e,'<H'),(0x13278,'<H'),(0x13270,'<Q'),(0x13269,'<B'))]+[int(im.read(0x1347b,'<B')[0]==255)]+[im.read(field,fmt)[0] for field,fmt in ((0x14958,'<H'),(0x14960,'<H'),(0x7d77,'<B'),(0x133f8,'<I'),(0x14890,'<Q'),(0x1496d,'<B'),(0x10bed,'<B'),(0x6c38,'<B'))]+[change,0,warning]
 actual=list(map(int,line.split()));assert actual==expected,(index,row,actual,expected)
 engaged+=change;warnings+=warning
 if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert engaged>20 and warnings>20
print(f'{len(cases)} original descent predictions agree: {engaged} automatic recovery engagements and {warnings} warnings, including exact 0.1/5/7/8/200 boundaries; only output delivery intercepted')
