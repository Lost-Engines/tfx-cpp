#!/usr/bin/env python3
"""Compare complete native altitude/fixed-colour/flash/blackout palette bytes.

Executes original startup, altitude selection, protected-colour blending and
flash/redout/blackout painters. Authored palette banks and supplied view/effect
state are inputs. Stops before the separately checked hardware-upload selector;
blackout sound requests are observed at the pending audio boundary. Darkside
planet traversal and the controllers generating effect state are outside scope.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
a=parser.parse_args();profiles=[c for c in json.loads((a.research/'analysis/lighting/environments.json').read_text())['environments'] if c['status']=='decoded'];directory=a.research/'installs/cd_1994_09/TFX'
im=NativeReference(directory/'TFX.DAT');sounds=[]
im.intercept(0xa4dfc,'Observe blackout/redout sample requests without audio playback',lambda image:(sounds.append(image.cpu.reg_read(r.UC_X86_REG_EAX)),image.return_from()))
rng=random.Random(0x73214);cases=[];profiles_by_name={c['environment']:c for c in profiles}
for profile in profiles:
    boundaries=[profile['distance_fields'][offset] for offset in ('0x10bc8','0x10bd0','0x10bcc','0x10b9c','0x10b98')]
    heights=[-100,-1,0,1]+[height+edge for height in boundaries for edge in (-51,-1,0,1,49,51)]+[boundaries[-1]+100,20000]
    for index in range(128):
        height=heights[index%len(heights)] if index<80 else rng.randrange(-2000,25000)
        pitch=[0,0x2000,0x4000,0x8000,0xc000,65535][index%6] if index<64 else rng.randrange(65536)
        roll=[0,0,0x4000,0x8000,0xc000,65535][index%6] if index<64 else rng.randrange(65536)
        cases.append([profile['environment'],int(index==0),int(index%5==0),-height,pitch,roll,28 if index%7==0 else index%29,int(index%11!=0),index%3,[0,9,10,24,25,50,-1,51][index%8],[50,25,24,10,9,0,51,-1][index%8],[0,63,90,125,127,128,255][index%7],[0,1,12,49,50,255][index%6] if index%13==0 else -1])
stride=788;output=subprocess.check_output([str((a.build/'palette_lighting_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode());assert len(output)==len(cases)*stride
for index,row in enumerate(cases):
    name,reset,dirty,y,pitch,roll,view,effects,mode,black,red,green,flash=row
    if reset:
        profile=profiles_by_name[name];banks={bank['data_offset']:bank for bank in profile['banks']}
        for at in (0x21000,0xf688,0xf388,0xf088,0xed88):im.cpu.mem_write(im.data+at,(a.research/'extracted/cd_1994_09/resources'/banks[hex(at)]['path']).read_bytes())
        for offset,at in zip((0x10bc8,0x10bd0,0x10bcc,0x10b9c,0x10b98),(0x21000,0xf688,0xf388,0xf088,0xed88)):
            im.write(offset,'<i',profile['distance_fields'][hex(offset)])
        im.write(0x10bb4,'<5I',*(im.data+at for at in (0x21000,0xf688,0xf388,0xf088,0xed88)));im.write(0x10bec,'<B',0)
        im.write(0x5956,'<h',0);im.write(0x595c,'<h',0);im.call(0x73f5c)
    im.write(0x5950,'<B',dirty);im.write(0x134f8,'<i',y);im.write(0x86c8,'<H',pitch);im.write(0x86cc,'<H',roll);im.write(0x87b6,'<h',view)
    im.write(0x10bea,'<B',mode);im.write(0x10bda,'<h',black);im.write(0x10bdc,'<h',red);im.write(0xe774,'<H',effects)
    if flash>=0:im.write(0x10beb,'<B',flash)
    sounds.clear();im.call(0x73214,limit=500000)
    im.write(0xf988+19,'<B',green)
    im.cpu.mem_write(im.STACK,struct.pack('<I',im.RETURN));im.cpu.reg_write(r.UC_X86_REG_ESP,im.STACK);im.cpu.reg_write(r.UC_X86_REG_EAX,pitch);im.cpu.reg_write(r.UC_X86_REG_EDX,roll);im.cpu.reg_write(r.UC_X86_REG_EFLAGS,0x202)
    im.cpu.emu_start(im.native(0x73a0c),im.native(0x73b76),count=1000000);assert im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x73b76)
    expected=struct.pack('<5i',*im.read(0x5956,'<h'),*im.read(0x595c,'<h'),*im.read(0x10beb,'<B'),*im.read(0x5950,'<B'),sounds[0] if sounds else -1)+bytes(im.cpu.mem_read(im.data+0xf988,768));actual=output[index*stride:(index+1)*stride]
    assert len(sounds)<=1
    assert actual==expected,(index,row,struct.unpack('<5i',actual[:20]),struct.unpack('<5i',expected[:20]),[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y][:20])
print(f'Complete native palettes, retained lighting state and effect requests agree in {len(cases)} updates across {len(profiles)} environments')
