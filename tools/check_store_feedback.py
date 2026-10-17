#!/usr/bin/env python3
"""Compare native release sound selection, bay notification and launch order.

The complete 0x8bd8c caller executes. Host audio, SSD event and projectile
construction are observed boundaries; their playback/animation/motion are
verified independently. Covers every byte-valued category, all aircraft,
jettison, and the caller's inhibited branch.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference,r
from unicorn import UC_HOOK_CODE

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--save-fixture',type=Path)
a=p.parse_args()
im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
im.write(0xa3f4,'<h',-1) # Original absent optional external-control-device branch.
im.write(0xac74,'<I',0x300800)
im.cpu.mem_write(0x300100,struct.pack('<2I',1,0)) # Arcade, not simulator: retain the pylon.
im.intercept(0xb1334,'Supply unchanged Arcade/simulator configuration; native inventory and selector gates execute.',lambda im:(im.cpu.reg_write(r.UC_X86_REG_EAX,0x300100 if im.cpu.reg_read(r.UC_X86_REG_EAX)==im.data+0x2148 else 0x300104),im.return_from()))
events=[]
def audio(cpu,address,size,unused):
    priority,first,second,end=struct.unpack('<4I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+4,16))
    assert priority==1 and end==0
    ids=[(ptr-im.data-0x9860)//26 for ptr in (first,second)]
    assert all(ptr==im.data+0x9860+sample*26 for ptr,sample in zip((first,second),ids))
    events.append(['sound',*ids]);im.return_from()
im.cpu.hook_add(UC_HOOK_CODE,audio,begin=0x300800,end=0x300800)
def bay(im):
    assert im.cpu.reg_read(r.UC_X86_REG_EAX)==777 and im.cpu.reg_read(r.UC_X86_REG_EDX)==5
    events.append(['bay',5]);im.return_from()
im.intercept(0xb52d4,'Observe the actual player bay entry, without executing its separately tested SSD program.',bay)
def launch(im):
    events.append(['launch']);im.return_from(stack_bytes=24)
im.intercept(0xa2f84,'Observe construction after the native sound and bay requests.',launch)
im.write(0xe76c,'<H',777)
im.write(0x86ce,'<B',0);im.write(0xabe9,'<B',0);im.write(0x86c8,'<3H',0,0,0)
for at in (0x13424,0x13430,0x1343c,0x13444,0x135d0):im.write(at,'<I',0)
actual=[list(map(int,line.split()))for line in subprocess.check_output([str(a.build/'loadout_probe'),'--feedback'],input=''.join(f'{i}\n'for i in range(256)).encode()).decode().splitlines()]
assert len(actual)==256
fixtures=[];count=0
for category in range(256):
    for plane in range(3):
        for jettison in (0,1):
            for inhibited in (0,1):
                im.write(0x809c+48+29,'<B',category)
                im.write(0x11b2a,'<H',plane);im.write(0x9170,'<H',jettison);im.write(0x12c04,'<H',inhibited)
                im.write(0x93b0,'<h',0);im.write(0x13374,'<2B',1,1)
                events.clear();im.call(0x8bd8c)
                want=[] if inhibited else ([]if jettison else [['sound',*actual[category]]])+([]if plane==0 else [['bay',5]])+[['launch']]
                assert events==want,(category,plane,jettison,inhibited,events,want)
                if plane==0 and not jettison and not inhibited:fixtures.append([category,*events[0][1:]])
                count+=1
if a.save_fixture:a.save_fixture.write_text(''.join(' '.join(map(str,row))+'\n'for row in fixtures))
print(f'{count} complete native release cases agree: all category bytes, three aircraft, jettison silence, inhibition, bay entry and sound-before-bay-before-launch ordering')
