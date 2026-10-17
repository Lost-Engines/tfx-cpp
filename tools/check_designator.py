#!/usr/bin/env python3
"""Compare complete original designator controllers, cameras and overlays.

Search/tracking gimbals, zoom, integer camera cache, view matrix, point projection,
reticle sprite, T/L labels and independent blink phases execute in the reference.
World submission, horizon drawing and VGA batching are explicit boundaries; their
pixels are not part of this supplied-world-background comparison. Asset lookup
supplies the exact original target-reticle bank. No installation is modified.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from unicorn import UC_HOOK_CODE
from native_reference import NativeReference,r
from native_vga import VgaCapture
from native_planner import NativePlanner

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--cases',type=int,default=1024)
p.add_argument('--record',type=Path,help='retain compact asset-free camera/projection inputs and expected native state')
a=p.parse_args();directory=a.research/'installs/cd_1994_09/TFX'
resources=NativePlanner(directory,a.research)
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000)
im.cpu.mem_map(0x300000,0x20000);im.cpu.mem_write(0x310000,resources.read('spr/targcros.spr'))
code=lambda off:im.native(0x70aa4+off)
im.cpu.emu_start(im.native(0xb9110),im.native(0xb9133),count=10000)
im.write(0x1b23c,'<I',0x300000);im.write(0xac58,'<i',-16384);im.write(0xac5c,'<i',0)
im.write(0x12c2c,'<H',42)
for address,pop,reason in (
 (0xc488d,0,'Keep direct VGA drawing rather than opening the separate batching cache.'),
 (0xc48e1,0,'No batching cache was opened; native sprite and glyph painters remain active.'),
 (0xb0ba8,4,'Supply an already drawn world background at terrain submission.'),
 (0xa30cc,0,'Exclude the separate weather/world submission phase.'),
 (0x74fc0,0,'Exclude moving-world submissions from this overlay comparison.'),
 (0x7b10c,0,'Exclude separately drawn selected-world-object geometry.'),
 (0x7572c,0,'No world queue was submitted; its separately checked flush is outside this comparison.'),
):im.intercept(address,reason,lambda im,pop=pop:im.return_from(pop))
horizon=[];destination=[]
def background(im):
 horizon[:]=[im.cpu.reg_read(r.UC_X86_REG_EAX)&65535,im.cpu.reg_read(r.UC_X86_REG_EDX)&65535,struct.unpack('<h',im.cpu.mem_read(code(0x47c08),2))[0]];im.return_from()
im.intercept(0x8fcd4,'Observe the original pitch/roll/height handoff; original horizon VGA is checked separately.',background)
def resolve(im):
 assert im.cpu.reg_read(r.UC_X86_REG_EAX)&65535==42
 im.cpu.reg_write(r.UC_X86_REG_EAX,0x310000);im.return_from()
im.intercept(0xc8568,'Supply the exact original targcros.spr bytes at its retained asset handle.',resolve)
def projection(cpu,address,size,unused):
 destination[:]=[struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+16,4))[0]]
im.cpu.hook_add(UC_HOOK_CODE,projection,begin=im.native(0xc5759),end=im.native(0xc5759))
rng=random.Random(0x92c24);rows=[]
for case in range(a.cases):
 tracking=(case//3)%2;pitch=rng.randrange(0x100,0x4000);heading=rng.randrange(65536);zoom=rng.choice((0,1,2,4,8,10,16,255));player=[rng.randrange(-500000,500001),rng.randrange(-12000,-30),rng.randrange(-500000,500001)];angles=[rng.randrange(65536),rng.randrange(65536)];aircraft=case%3;flags=rng.randrange(16)
 target=[(player[0]+rng.randrange(-10000,10001))*256,rng.randrange(-1000,1)*256,(player[2]+rng.randrange(-10000,10001))*256]
 centre=[(159,99),(1,1),(318,198),(-3,100),(320,100),(160,-3),(160,200)][(case//7)%7]
 rows.append([tracking,pitch,heading,zoom,*player,*angles,aircraft,flags,*target,*centre])
output=subprocess.check_output([str((a.build/'designator_probe').resolve()),str(directory)],input=('\n'.join(' '.join(map(str,row)) for row in rows)+'\n').encode());stride=128112
assert len(output)==stride*len(rows),(len(output),stride*len(rows))
fixtures=[];painted=0
for case,row in enumerate(rows):
 tracking,pitch,heading,zoom=row[:4];player=row[4:7];angles=row[7:9];aircraft,flags=row[9:11];target=row[11:14];centre=row[14:16]
 im.cpu.mem_write(0x300000,bytes(256))
 for offset,bit in ((72,1),(80,2),(75,4),(77,8)):im.cpu.mem_write(0x300000+offset,bytes([int(bool(flags&bit))]))
 for address,value in zip((0x13424,0x13430,0x1343c),player):im.write(address,'<i',value)
 im.write(0x86c8,'<3H',*angles,0);im.write(0x11b2a,'<H',aircraft);im.write(0x8828,'<2H',pitch,heading);im.write(0x883c,'<B',zoom);im.write(0x883d,'<B',0);im.write(0x8840,'<I',0x135a0 if tracking else 0);im.write(0x8844,'<i',0);im.write(0x135a0,'<3i',*target);im.write(0x87dc,'<B',0)
 im.call(0xca780);im.call(0xb9238,stack=(0,319,0,199));im.call(0xb94da,stack=(*(x&0xffffffff for x in centre),319,199));im.call(0xc0634,stack=(199,0,319,0))
 video.reset(99);horizon.clear();destination.clear();im.call(0x92c24,limit=3000000)
 assert len(horizon)==3 and len(destination)==1 and im.read(0x87dc,'<B')[0]==1,(case,horizon,destination)
 camera=[struct.unpack('<i',im.cpu.mem_read(code(off),4))[0] for off in (0x491e1,0x491e7,0x491ed)]
 matrix=list(struct.unpack('<9h',im.cpu.mem_read(code(0x47c4a),18)))
 projected=list(struct.unpack('<2h',im.cpu.mem_read(destination[0],4)))
 new_pitch,new_heading=im.read(0x8828,'<2H');new_zoom=im.read(0x883c,'<B')[0]
 # The camera origin handed to B9A6C is the rotated cache undone, not a
 # reconstruction from the marker projection or another C++ output field.
 signed=lambda value:struct.unpack('<i',struct.pack('<I',value&0xffffffff))[0]
 new_camera=[signed(((x&65535)<<16)|((x&0xffffffff)>>16)) for x in camera]
 point=[x>>8 for x in target] if tracking else [im.read(0x882c,'<i')[0],0,im.read(0x135ac,'<i')[0]]
 pose=[*camera,*matrix,*projected,*horizon]
 header=[new_pitch,new_heading,new_zoom,*new_camera,*point,*pose,im.read(0x884a,'<h')[0],im.read(0x8848,'<h')[0]]
 want=struct.pack('<28i',*header)+bytes(video.pixels())+bytes(video.coverage());got=output[case*stride:(case+1)*stride]
 if got!=want:
  got_header=struct.unpack_from('<28i',got);print('header mismatches',[(i,x,y) for i,(x,y) in enumerate(zip(got_header,header)) if x!=y])
  raise AssertionError((case,row,len([(x,y) for x,y in zip(got,want) if x!=y]),[(i,(i-112)%64000%320,(i-112)%64000//320,x,y) for i,(x,y) in enumerate(zip(got,want)) if x!=y][:24]))
 painted+=any(v!=99 for v in video.pixels())
 if case<64 or case%31==0:fixtures.append([new_pitch,new_heading,*new_camera,*point,*centre,*pose])
 if case and case%128==0:print(f'Checked {case} complete designator controllers/overlays',flush=True)
if a.record:a.record.write_text('\n'.join(' '.join(map(str,row)) for row in fixtures)+'\n')
print(f'{len(rows)} complete original designator controllers agree; {painted} nonempty overlays: gimbals, zoom, integer camera caches, native view matrices, projection, sprite/glyph pixels, coverage, horizon inputs and separate search/tracking blink phases. World and horizon pixels remain separate comparisons.')
