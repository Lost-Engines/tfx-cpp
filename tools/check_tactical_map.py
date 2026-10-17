#!/usr/bin/env python3
"""Compare the original paused tactical map and changing target/runway markers.

Original 0x86e2c executes: framebuffer clearing, retained map/compiled overlay,
route lines, contact eligibility, name/telemetry formatting, player heading and
blink updates. Resource/name/contact queries, timer samples, key transport and
page presentation are explicit boundaries. No world/flight outcome is supplied.
"""
import argparse
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
from native_reference import NativeReference,r
from native_vga import VgaCapture
from unicorn import UC_HOOK_CODE,UC_HOOK_INSN

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--cases',type=int,default=64,help='cases per regional map')
p.add_argument('--map',choices=('yugosmap','somalmap','colummap','libyamap','seamap'))
p.add_argument('--output',type=Path,help='retain inputs and indexed frames on a mismatch')
a=p.parse_args();root=a.research.resolve();directory=root/'installs/cd_1994_09/TFX'
sys.path.insert(0,str(root/'did-unpack'));from did_unpack import Archive
archive=Archive.read(directory/'DID.DAT');entries={e.identifier:e for e in archive.entries}
im=NativeReference(directory/'TFX.DAT',data_base=0x100000);video=VgaCapture(im,aperture=0xa0000)
im.cpu.mem_map(0x300000,0x30000);im.cpu.mem_map(0x400000,0x30000);im.call(0xde547)
im.cpu.mem_write(0x410000,archive.unpack(entries[archive.hash_name('dat/cockmap.bin')]))
im.write(0x12c30,'<H',1);im.write(0x13284,'<H',2);im.write(0x1b238,'<I',0x300000);im.write(0x5978,'<I',0x300100);im.write(0x5955,'<B',0)
im.intercept(0xc85a0,'Supply retained original map/compiled-overlay resources.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,0x400000+(current.cpu.reg_read(r.UC_X86_REG_EAX)-1)*0x10000),current.return_from()))
contacts=[[],[],[],[]];profile_names={};intervals=[];frames=[];interval=[0]
def query(current,surface):
 index=current.cpu.reg_read(r.UC_X86_REG_EAX)&65535;index=(index if index<32768 else index-65536)+1
 side=current.cpu.reg_read(r.UC_X86_REG_EDX);group=(2 if surface else 0)+side
 current.cpu.reg_write(r.UC_X86_REG_EAX,0x310000+group*0x2000+index*128 if index<len(contacts[group])else 0);current.return_from()
im.intercept(0x786d8,'Supply aircraft poses at the independently checked enumerator boundary.',lambda current:query(current,False))
im.intercept(0x7c7d0,'Supply surface poses at the independently checked enumerator boundary.',lambda current:query(current,True))
im.intercept(0x7889c,'Supply aircraft profile names; original case conversion and formatting execute.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,profile_names[current.cpu.reg_read(r.UC_X86_REG_EAX)]),current.return_from()))
for function in (0xc6304,0xc6362):im.intercept(function,'Keep a fixed supplied VGA page at the external presentation boundary.',lambda current:current.return_from())
def timer(current):
 current.cpu.reg_write(r.UC_X86_REG_EAX,intervals[interval[0]]);current.return_from()
im.intercept(0x74628,'Supply explicit elapsed intervals at the external modal timer boundary.',timer)
def poll(cpu,address,size,unused):
 frames.append(struct.pack('<IB',cpu.reg_read(r.UC_X86_REG_ESI),im.read(0x7888,'<B')[0])+bytes(video.pixels()));interval[0]+=1
 if interval[0]==len(intervals):im.cpu.mem_write(0x300000,b'\1')
im.cpu.hook_add(UC_HOOK_CODE,poll,begin=im.native(0xc9bdc),end=im.native(0xc9bdc))
port_reads=[0]
def input_port(cpu,port,size,unused):
 assert port==0x3da,hex(port)
 port_reads[0]+=1;return 8 if port_reads[0]&1 else 0
im.cpu.hook_add(UC_HOOK_INSN,input_port,None,1,0,r.UC_X86_INS_IN)
rng=random.Random(0x86e2c);total=0
names=('MiG-29 Fulcrum','Efa Eurofighter','F-117','Boeing707 Vip','Air AEW')
for name in ([a.map]if a.map else ('yugosmap','somalmap','colummap','libyamap','seamap')):
 im.cpu.mem_write(0x400000,archive.unpack(entries[archive.hash_name('spr/'+name+'.spr')]))
 cases=[]
 for case in range(a.cases):
  player=[rng.randrange(200)*2048,-rng.randrange(10000),rng.randrange(200)*2048];heading=rng.randrange(65536)
  route=[[rng.randrange(200),rng.randrange(200)]for _ in range(case%8)]
  targets=[[rng.randrange(200)*2048,0,rng.randrange(200)*2048]for _ in range(case%10)]
  groups=[]
  for group in range(4):
   points=[]
   for index in range((case+group)%13 if group==0 else (case+group)%4):
    point=[rng.randrange(200)*2048*256,rng.choice((-37*256,-38*256,-38*256-1,-100*256,-8000*256)),rng.randrange(200)*2048*256]
    points.append([*point,rng.randrange(65536),rng.choice((0,400,32767,-32768))*65536,int(group==0 and index==case%12),names[(case+index)%len(names)]])
   groups.append(points)
  ticks=[0,35,1,80,0]if case%2==0 else [0,1,34,65535,1,36,0]
  cases.append({'player':player,'heading':heading,'route':route,'targets':targets,'landing':case%3!=0,'cell':[rng.randrange(200),rng.randrange(200)],'colour':11 if case%2 else 15,'groups':groups,'ticks':ticks})
 requests=[]
 for case in cases:
  row=[case['colour'],*case['player'],case['heading'],int(case['landing']),*case['cell'],len(case['route']),*[v for point in case['route']for v in point],len(case['targets']),*[v for point in case['targets']for v in point]]
  request=' '.join(map(str,row))
  for group,points in enumerate(case['groups']):
   request+=' '+str(len(points))
   for point in points:request+=' '+' '.join(map(str,point[:6]if group<2 else point[:3]))+(' '+json.dumps(point[6])if group<2 else '')
  request+=' '+' '.join(map(str,[len(case['ticks']),*case['ticks']]))
  requests.append(request)
 actual=subprocess.check_output([str((a.build/'tactical_map_probe').resolve()),str(directory),name],input=('\n'.join(requests)+'\n').encode());offset=0
 for number,case in enumerate(cases):
  for field,value in zip((0x13424,0x13430,0x1343c),case['player']):im.write(field,'<i',value)
  im.write(0x86ca,'<H',case['heading']);im.write(0x8f82,'<B',case['landing']);im.write(0x14984,'<2h',*case['cell']);im.write(0x7888,'<B',case['colour'])
  im.cpu.mem_write(0x300000,b'\0');im.cpu.mem_write(0x300100,struct.pack('<H',len(case['route']))+b''.join(struct.pack('<BB',*point)for point in case['route']))
  im.write(0x11b22,'<H',len(case['targets']))
  for index,point in enumerate(case['targets']):im.write(0x5c40+index*26,'<3i',*point)
  contacts[:]=case['groups'];profile_names.clear();im.write(0x11108,'<I',0)
  for group,points in enumerate(contacts):
   for index,point in enumerate(points):
    address=0x310000+group*0x2000+index*128;im.cpu.mem_write(address,bytes(128));im.cpu.mem_write(address,struct.pack('<3i3Hi',*point[:3],0,point[3],0,point[4]))
    if group<2:
     location=0x320000+group*0x1000+index*64;im.cpu.mem_write(location,point[6].encode()+b'\0');profile_names[address]=location
     if point[5]:im.write(0x11108,'<I',address)
  intervals[:]=case['ticks'];interval[0]=0;frames.clear();video.reset();im.call(0x86e2c,limit=10000000)
  assert len(frames)==len(intervals)
  for frame,want in enumerate(frames):
   got=actual[offset:offset+len(want)];offset+=len(want)
   if got!=want:
    if a.output:
     a.output.mkdir(parents=True,exist_ok=True);(a.output/'case.json').write_text(json.dumps(case,indent=2));(a.output/'native.indices').write_bytes(want[5:]);(a.output/'cpp.indices').write_bytes(got[5:])
    raise AssertionError((name,number,frame,'state',got[:5].hex(),want[:5].hex(),'pixels',sum(x!=y for x,y in zip(got[5:],want[5:])),[(i%320,i//320,x,y)for i,(x,y)in enumerate(zip(got[5:],want[5:]))if x!=y][:20]))
  total+=len(frames)
 assert offset==len(actual)
print(f'{total} original tactical-map frames agree: regional schematics, compiled frame, route, contact cutoff/telemetry, player heading, target/runway overlap and retained blink state.')
