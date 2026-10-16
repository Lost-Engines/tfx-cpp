#!/usr/bin/env python3
"""Compare native mission-start instruments and animated cockpit positioning."""
import argparse
from pathlib import Path
import random
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';probe=str((args.build/'cockpit_frame_probe').resolve())
cases=[];expected=[]
for aircraft in range(3):
    for landed in range(2):
        im=NativeReference(directory/'TFX.DAT')
        for address in (0x81174,0x73630,0x73f5c,0x7dc7c,0x742a0,0x809e4,0x8b6c4,0x81198,0x8c414,0x82744,0x86a60):
            im.intercept(address,'Reset/load the dependent rendering, messaging, inventory or aircraft component outside this owned HUD-state capture.',lambda im:im.return_from())
        im.write(0x11b2a,'<H',aircraft);im.write(0x11b3c,'<B',landed)
        im.call(0x7df30,limit=1000000)
        left,centre,right=im.read(0x713a,'<3H');horizontal,bvr=im.read(0x7d7c,'<2H')
        cases.append([aircraft,landed]);expected.append([left,centre,right,horizontal,bvr,im.read(0x10be8,'<h')[0],im.read(0x10be6,'<h')[0],im.read(0x6c3c,'<h')[0],im.read(0x6c3a,'<h')[0],*im.read(0x6c3e,'<2B'),im.read(0x12f26,'<B')[0],*im.read(0x7d70,'<12B')])
output=subprocess.check_output([probe,str(directory),'setup'],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).splitlines()
assert len(output)==len(expected)
for row,got,want in zip(cases,output,expected):assert list(map(int,got.split()))==want,(row,got,want)
im=NativeReference(directory/'TFX.DAT');im.write(0x10be8,'<h',0);im.write(0x10be6,'<h',28);im.write(0x12bf8,'<H',0)
im.write(0xe70c,'<I',im.native(0x70b44));rng=random.Random(0x7d82c);steps=[];expected=[]
for index in range(2048):
    action=2 if index==0 else 1 if index==32 else 0 if index<64 else rng.choice((0,0,0,1,2))
    view=1 if index>=64 and index%7==0 else 0;im.write(0x87b6,'<H',view)
    if action:im.call(0x84540 if action==1 else 0x8456c)
    callback=im.read(0xe70c,'<I')[0]
    if callback!=im.native(0x70b44):
        file=callback-im.layout['objects'][0]['preferred_base']+im.layout['objects'][0]['file'];assert file in (0x7d82c,0x7d8bc)
        im.call(file)
    callback=im.read(0xe70c,'<I')[0]
    movement={im.native(0x70b44):0,im.native(0x7d82c):1,im.native(0x7d8bc):2}[callback]
    steps.append([action,view]);expected.append([im.read(0x10be8,'<h')[0],im.read(0x10be6,'<h')[0],im.read(0x12bf8,'<H')[0],movement])
output=subprocess.check_output([probe,str(directory),'position'],input=('\n'.join(' '.join(map(str,row)) for row in steps)+'\n').encode()).splitlines()
assert len(output)==len(expected)
for row,got,want in zip(steps,output,expected):assert list(map(int,got.split()))==want,(row,got,want)
print(f'Native instrument setup agrees for all {len(cases)} aircraft/start cases; animated cockpit positioning agrees over {len(steps)} steps')
