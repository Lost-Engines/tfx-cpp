#!/usr/bin/env python3
"""Compare complete advanced player/engine startup and first placement.

Original 0x8c184, its full 0x95f3c initializer, engine priming 0x8c318, route
selection initialization and first-placement prefix of 0x8f56c execute. Host
mouse setup and supplied start-surface classification are explicit boundaries;
no numerical startup/placement/physical-reset helper is replaced. Instrument
system conditions are the separately verified native startup inputs.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r
from native_x87 import hardware_fpatan,hardware_sine_cosine,hardware_tangent
from aerodynamic_snapshot import fields,tail,snapshot
from aerodynamic_autopilot_snapshot import snapshot as autopilot_snapshot

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
a=p.parse_args();path=a.research/'installs/cd_1994_09/TFX/TFX.DAT';im=NativeReference(path);im.call(0xde851);im.cpu.mem_map(0x300000,0x4000);backends=(hardware_fpatan(im,a.build),hardware_sine_cosine(im,a.build),hardware_tangent(im,a.build));rng=random.Random(0x8c184)
data_size=(im.layout['objects'][2]['virtual_size']+4095)&~4095;baseline=bytes(im.cpu.mem_read(im.data,data_size));terrain_type=[50]
im.intercept(0x744e4,'Host mouse availability is supplied without a DOS driver',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
im.intercept(0x74614,'Host mouse setup/reset delivery',lambda image:image.return_from())
im.intercept(0xb0d80,'Supply start-cell terrain lookup, not placement arithmetic',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
im.intercept(0xb7a3c,'Supply checked runway/carrier start classification',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,terrain_type[0]),image.return_from()))
cases=[]
for i in range(768):
 craft=1+i%3;model=(i//3)%2;landed=(i//6)%2;height=0 if (i//12)%2 else -20
 cases.append([craft,model,landed,height,rng.choice([0,1,2,15]),rng.randrange(10),rng.randrange(27),(i//24)%2,rng.randrange(65536),rng.randrange(65536),rng.randrange(-10000,410000),rng.choice([-10000,-800,0,5]),rng.randrange(-10000,410000),rng.randrange(65536),rng.randrange(65536),rng.randrange(65536),(i//48)%2,rng.randrange(-20,51),(i//96)%2,(i//192)%2])
output=subprocess.check_output([str((a.build/'aerodynamic_launch_probe').resolve()),str(path)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
for case,(row,line) in enumerate(zip(cases,output)):
 craft,model,landed,height,count,slot,weapon,occupied,low,high=row[:10];position=row[10:13];angles=row[13:16];temperature,celsius,terrain_boost,weather_boost=row[16:]
 im.cpu.mem_write(im.data,baseline);terrain_type[0]=50 if height==0 else 0
 for field,value,fmt in ((0x11b2a,craft-1,'<H'),(0x1347a,6 if model else 1,'<B'),(0x11b3c,landed,'<B'),(0x1347b,255,'<B'),(0x8f30,temperature,'<B'),(0x14956,0,'<H'),(0x8c98,celsius,'<h'),(0xe762,terrain_boost,'<H'),(0xe774,128 if weather_boost else 0,'<B')):im.write(field,fmt,value)
 for field,value in zip((0x13424,0x13430,0x1343c),position):im.write(field,'<i',value)
 im.write(0x86c8,'<3H',*angles)
 for system in range(12):im.write(0x7d70+system,'<B',1 if (system in (2,5) and not landed) or (system==10 and landed) else 2)
 im.cpu.mem_write(im.data+0x13374,bytes(20));im.write(0x13374+slot*2,'<2B',weapon,occupied);im.cpu.mem_write(im.native(0xc9894),struct.pack('<2H',low,high))
 im.cpu.mem_write(0x300100,struct.pack('<H',count)+bytes(count*2));im.call(0x75228,eax=0x3000ff)
 im.call(0x8c184,limit=2000000);im.call(0x8c318)
 im.cpu.mem_write(im.STACK,struct.pack('<I',im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
 im.cpu.emu_start(im.native(0x8f56c),im.native(0x8f686),count=2000000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x8f686)
 expected=snapshot(im)+autopilot_snapshot(im)+[im.read(0x1347c,'<B')[0],im.read(0x13280,'<H')[0]];actual=list(map(int,line.split()))
 assert actual==expected,(case,row,[(i,hex(fields[i][0]) if i<len(fields) else hex(tail[i-260][0]) if 260<=i<282 else 'startup',x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
print(f'{len(cases)} complete advanced player/engine startups and first placements agree across all 316 flight/control fields and random states; runway/carrier/airborne, raw angles, stores, temperature and wind inputs')
