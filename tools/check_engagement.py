#!/usr/bin/env python3
"""Compare original tracking/firing permission notifications and frame timer.

Complete 0x763fc/0x76398/0x81994 handlers execute, with supplied parser booleans.
Radio and actual sample callback arguments are observed. The exact 0x72372 timer
block and 0x78446 permission-dependent score branch execute to declared next-phase
boundaries; full frame and full credit comparisons remain separate.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path('../tfx-reverse/installs/cd_1994_09/TFX'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();rng=random.Random(0x76398);im=NativeReference(a.data_dir/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
flags=[0,0];events=[]
def variable(image):
 pointer=image.cpu.reg_read(r.UC_X86_REG_EAX)-image.data
 assert pointer in (0x638,0x66c,0x183c,0x1844),hex(pointer)
 image.cpu.reg_write(r.UC_X86_REG_EAX,0x300000+(4 if pointer in (0x66c,0x1844) else 0));image.return_from()
im.intercept(0xb1334,'Supply Arcade/training parser variables; mode decisions execute unchanged.',variable)
def text(image):
 pointer=image.cpu.reg_read(r.UC_X86_REG_EAX)
 assert pointer in (image.data+0x640,image.data+0x1850)
 read=lambda at:bytes(image.cpu.mem_read(at,128)).split(b'\0')[0]
 assert read(pointer)==read(image.data+0x1850)
 events.append(0);image.return_from()
im.intercept(0x81198,'Observe the common permission text; the original references contain identical strings.',text)
def sample(image):
 sp=image.cpu.reg_read(r.UC_X86_REG_ESP);priority,descriptor,end=struct.unpack('<3I',image.cpu.mem_read(sp+4,12))
 assert not end and (descriptor-image.data-0x9860)%26==0
 events.extend((1,priority,(descriptor-image.data-0x9860)//26));image.return_from()
im.write(0xac74,'<I',im.native(0x75954));im.intercept(0x75954,'Observe actual sample priority and descriptor output, without playing audio.',sample)
im.intercept(0x72383,'End immediately after the original per-draw notice decrement; later frame work is out of scope.',lambda image:image.return_from())
im.intercept(0x7848a,'End after the original permission score/violation branch; subsequent kill counters have separate checks.',lambda image:image.return_from())
im.intercept(0x81254,'The score predicate may request its already-compared orders violation text.',lambda image:image.return_from())
rows=[];expected=[];fixtures=[]
for index in range(8192):
 row=[(index//96)%2,rng.choice([-32768,-1,0,1,29,30,32767]),index%2,(index//2)%2,1+(index//4)%3,(index//12)%2,(index//24)%2,(index//48)%2,rng.choice([0,1,29,30,31,64])]
 permitted,notice,kind,player,aircraft,arcade,training,inhibited,frames=row
 for at,fmt,value in [(0xe781,'<B',permitted),(0x763c,'<h',notice),(0x11b2a,'<H',aircraft),(0xabe9,'<B',inhibited)]:im.write(at,fmt,value)
 im.cpu.mem_write(0x300000,struct.pack('<2i',arcade,training));events.clear()
 im.call(0x76398 if kind else 0x763fc,eax=im.data+0x10f28 if player else 0x300800)
 for _ in range(frames):im.call(0x72372)
 # Observe the actual score eligibility branch, rather than deriving its predicate in Python.
 im.write(0x5c14,'<i',0);im.write(0xe75c,'<h',0);im.call(0x78446)
 score=im.read(0x5c14,'<i')[0];violations=im.read(0xe75c,'<h')[0];assert (score,violations) in ((1000,0),(0,1))
 # A sample event has three words, a permission notice one.
 cursor=0;count=0
 while cursor<len(events):cursor+=3 if events[cursor]==1 else 1;count+=1
 values=[im.read(0xe781,'<B')[0],im.read(0x763c,'<h')[0],int(score==1000),count,*events]
 rows.append(row);expected.append(values)
 if index<256:fixtures.append(row+values)
output=subprocess.check_output([str((a.build/'engagement_probe').resolve())],input=('\n'.join(' '.join(map(str,row))for row in rows)+'\n').encode()).decode().splitlines()
assert len(output)==len(expected)
for index,(line,values) in enumerate(zip(output,expected)):
 actual=list(map(int,line.split()));assert actual==values,(index,rows[index],actual,values)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row))for row in fixtures)+'\n')
print('8192 original permission handlers agree: player/nonplayer warnings, aircraft and Arcade/training gates, ordered radio/sample requests, latch state and exact frame-counter wrapping')
print('All resulting authorisation states agree with the original permission-dependent score/violation branch')
