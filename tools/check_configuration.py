#!/usr/bin/env python3
"""Compare native configuration dispatch and numeric setting readers.

0xa65f0 executes keyword lookup and original readers. Audio hardware selection
is an output boundary; no numeric conversion, sscanf or setting reader is
replaced. Legacy DOS calibration/BLASTER/ULTRASND are retained outside these
portable simulation settings.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
p.add_argument('--document',action='store_true')
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);im.call(0xde547);im.cpu.mem_map(0x300000,0x1000);rng=random.Random(0xa65f0)
size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,size))
im.intercept(0xc4f0c,'Audio hardware selection output; setting writes execute',lambda image:image.return_from())
fields=[(f,'<B') for f in (0x13478,0x8864,0x1347a,0xa4e8,0xa4e9,0x13267,0xab36,0xa4ea)]+[(0xd4ec,'<i')]+[(f,'<B') for f in (0x5954,0x8f31,0x8e22,0x8e23,0x8e25,0x8f30,0x8867)]+[(0xac68,'<I'),(0xa4ec,'<H')]
documents=['','CONTROL=2\r\nMODEL=2\r\nHUDCOL=97','hudcol=90\nHUDCOL=110\nHUDCOL=95','REALISM=2,1,1,1,1,1\r\nJOYSCALE=0.75','SOUNDFX=1\nMUSIC=0','CONTROL=1\nMODEL=3\nLANG=2','DETAIL=1\n'+'#'*1014,'DETAIL=1\n'+'#'*1015,'DETAIL=1\n'+'#'*1016]
for i in range(128):documents.append('\r\n'.join(k+'='+v for k,v in [('MODEL',str(i)),('REALISM',','.join(str((i>>bit)&1) for bit in range(i%9))),('HUDCOL',str(i+90)),('JOYSCALE',str(i/8)),('UNKNOWN','123')]))
if a.document:
 def file_length(image):image.cpu.reg_write(r.UC_X86_REG_EAX,len(content[0]));image.return_from()
 def file_read(image):image.cpu.mem_write(image.cpu.reg_read(r.UC_X86_REG_EDX),content[0]);image.return_from()
 content=[''];im.intercept(0xc9c24,'Supplied configuration file length',file_length);im.intercept(0xc9d4c,'Supplied configuration file contents',file_read);im.intercept(0xa5ce0,'Coupled audio driver output; native settings coercion executes',lambda image:image.return_from())
 payload='\n'.join((text.encode().hex() or '-')+'|' for text in documents)+'\n'
 output=subprocess.check_output([str((a.build/'configuration_probe').resolve()),'--document'],input=payload.encode()).decode().splitlines();assert len(output)==len(documents)
 fixtures=[]
 for text,line in zip(documents,output):
  im.cpu.mem_write(im.data,baseline);content[0]=text.encode();im.call(0xa664c,limit=300000)
  expected=[im.read(f,fmt)[0] for f,fmt in fields];actual=list(map(int,line.split()));assert actual==expected,(text[:100],[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
  fixtures.append((text.encode().hex() or '-')+'|'+' '.join(map(str,expected)))
 if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
 print(f'{len(documents)} complete original configuration file reads agree: CRLF, repeated/case-sensitive keys, legacy fields, SB coupling and exact 1024-byte fallback boundary')
 raise SystemExit
cases=[]
keys=['CONTROL','DETAIL','MODEL','SOUNDFX','MUSIC','STICK','LANG','LOWMEM','IRQBASE','HUDCOL','hudcol','HUDCOL ','LOADLOW','UNKNOWN']
for key in keys:
 for value in ('',' ','-1','+2','256','65537','2147483648','4294967296','-2147483649','12junk','0x20','--2','5,6'):cases.append((key,value))
for i in range(2048):
 key=rng.choice(keys+['REALISM','REALISM','JOYSCALE'])
 if key=='REALISM':value=','.join(str(rng.randrange(-300,301)) for _ in range(i%9))
 elif key=='JOYSCALE':value=rng.choice(['512','+0.75','-2.5','junk','1.2junk',' 3.141592653589793','0','-0'])
 else:value=str(rng.randrange(-2**32,2**32))
 cases.append((key,value))
for value in ('2,1,1,1,1,1','2,1','2,,1','2 ,1','2, 1','+,1','--1,2','2,1junk,3','2,1,1,1,1,1,1,99'):cases.append(('REALISM',value))
payload='\n'.join(key+'|'+value for key,value in cases)+'\n'
output=subprocess.check_output([str((a.build/'configuration_probe').resolve())],input=payload.encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,((key,value),line) in enumerate(zip(cases,output)):
 im.cpu.mem_write(im.data,baseline);im.cpu.mem_write(0x300000,key.encode()+b'\0');im.cpu.mem_write(0x300100,value.encode()+b'\0')
 try:im.call(0xa65f0,eax=0x300000,edx=0x300100)
 except Exception as error:raise RuntimeError((index,key,value,hex(im.cpu.reg_read(r.UC_X86_REG_EIP)))) from error
 expected=[im.read(f,fmt)[0] for f,fmt in fields];actual=list(map(int,line.split()));assert actual==expected,(index,key,value,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
 if index<182 or index%17==0 or index>len(cases)-12:fixtures.append(key+'|'+value+'|'+' '.join(map(str,expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'{len(cases)} original configuration dispatch/readers agree, including keyword case, integer truncation/overflow, MODEL mapping, partial REALISM lists and float parsing; calibration/hardware setup are explicit boundaries')
