#!/usr/bin/env python3
"""Compare original Simple low-speed visual attitude and touchdown stages.

Both complete native routines and their angle/residual/matrix helpers execute
without interception. Ground observations, aircraft limits and preceding speed
stores are explicit inputs; intervening flight movement is not part of this test.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.cpu.mem_map(0x300000,4096)
rng=random.Random(0x8d970);bits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0];identity=[32767,0,0,0,32767,0,0,0,32767];cases=[]
for index in range(8192):
    im.cpu.mem_write(0x300000,struct.pack('<9h',*identity))
    for function in (0xccf4c,0xcd058,0xcd15c):im.call(function,eax=0x300000,edx=rng.randrange(65536))
    body=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    if index%3==0:im.call(0xccf4c,eax=0x300000,edx=1024)
    visible=list(struct.unpack('<9h',im.cpu.mem_read(0x300000,18)))
    gear=[2.675,2.225,2.8][index%3];ground=[0,-20,-200,-1000][index%4];y=[-1000,-20,-1,0,1,ground,ground-gear,ground-gear-.01,ground-gear+.01][index%9]
    stall,reference=[(64.375,61.8),(92.7,79.825),(67.98,77.25)][index%3]
    speed=[0,stall-.01,stall,stall+.01,200][index%5];turn=[0,reference-.01,reference,reference+49.99,reference+50,reference+50.01,200][index%7]
    flags=[int(index&(1<<bit)!=0) for bit in range(5)]
    cases.append([1+index%3,bits(y),rng.randrange(-32768,32768),rng.randrange(-32768,32768),rng.randrange(-32768,32768),flags[0],flags[1],flags[2],index%3,flags[3],*body,*visible,*[bits(rng.uniform(-2048,2048)) for _ in range(3)],[0,1,2,4,18,108,65535][index%7],flags[4],ground,bits(gear),bits(speed),bits(turn),bits(rng.uniform(0,2000)),stall,reference,30,[0,59,60,61,300][index%5],int(index&32!=0),int(index&64!=0),int(index&128!=0),[0,1,3,50][index%4],int(index&256!=0)])
output=subprocess.check_output([str((a.build/'simple_ground_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[]
for index,(row,line) in enumerate(zip(cases,output)):
    action,y,stall_pitch,pitch,roll,landed,previous,low,collision,cut=row[:10];body=row[10:19];visible=row[19:28];remainders=row[28:31];ticks,present,height,gear,speed,turn,reported,stall,reference,rollout,fixed,down,inhibited,pitch_down,kind,chute=row[31:]
    im.write(0x13428,'<I',y);im.write(0x8790,'<3h',stall_pitch,pitch,roll);im.write(0x8d3a,'<H',landed);im.write(0x86b4,'<H',previous);im.write(0x8d38,'<H',low);im.write(0x12c04,'<h',collision);im.write(0x8d14,'<H',cut);im.write(0x1345e,'<9h',*body);im.write(0x1344c,'<9h',*visible);im.write(0x13480,'<3I',*remainders);im.write(0x14418,'<d',0);im.write(0x14290,'<d',0)
    im.write(0x13476,'<H',ticks);im.write(0xabea,'<B',present);im.write(0xabf2,'<h',height);im.write(0x11b2a,'<H',0);im.write(0x86bc,'<I',gear);im.write(0x133e8,'<I',speed);im.write(0x1339c,'<I',turn);im.write(0x13440,'<I',reported);im.write(0x14540,'<d',stall);im.write(0x14548,'<d',reference);im.write(0x8d08,'<d',rollout);im.write(0x13444,'<i',fixed);im.write(0x146d8,'<d',float(down));im.write(0x13474,'<H',inhibited);im.write(0x1325c,'<H',pitch_down);im.write(0xabec,'<h',kind);im.write(0x8d12,'<H',chute)
    if action&1:im.call(0x8d6e8)
    if action&2:im.call(0x8d970)
    expected=[value&0xffffffff for field in (0x1345e,0x1344c) for value in im.read(field,'<9h')]+list(im.read(0x13480,'<3I'))+[im.read(0x13428,'<I')[0]]+[value&0xffffffff for value in im.read(0x8790,'<3h')]+[im.read(field,'<H')[0] for field in (0x8d3a,0x86b4,0x8d38)]+[im.read(0x12c04,'<h')[0]&0xffffffff,im.read(0x8d14,'<H')[0]]+[im.read(field,'<Q')[0] for field in (0x14418,0x14290)]
    actual=list(map(int,line.split()));assert actual==expected,(index,row,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y],len(actual),len(expected))
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Simple stall/ground handling agrees in {len(cases)} original body/visible basis, residual, contact, word and float-bit updates without intercepted dependencies')
