#!/usr/bin/env python3
"""Check carried-store attachment state and every retail preview loadout.

Native checks cover slot lookup, anchor/condition installation and restoration.
The geometry comparison uses the independent research interpreter; it is not a
complete native raster or projection comparison.
"""
import argparse
import json,struct,subprocess,math
from pathlib import Path
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,required=True)
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args()
root=args.research.resolve();repo=Path.cwd();build=args.build.resolve()
image=NativeReference(root/'installs/cd_1994_09/TFX/TFX.DAT')
image.cpu.mem_map(0x300000,0x30000)
relative=lambda offset:image.native(0x70aa4+offset)
current={};entries=[]
def handle(im):
    assert im.cpu.reg_read(r.UC_X86_REG_EAX)&65535==current['handle']
    im.cpu.reg_write(r.UC_X86_REG_EAX,0x320000);im.return_from()
def child(im):
    assert [struct.unpack('<i',im.cpu.mem_read(relative(at),4))[0] for at in (0x489a3,0x489a9,0x489ae)]==current['anchor']
    assert im.cpu.mem_read(relative(0x4b946),1)==b'\xf9'
    entries.append(current['slot']);im.return_from()
image.intercept(0xc8568,'Resolve a supplied synthetic carried-model handle.',handle)
image.intercept(0xbc994,'Observe child entry state; child geometry is outside this native boundary.',child)
for slot in range(10):
    for present in (False,True):
        anchor=[1000+slot,-2000-slot,3000+slot]
        current.update(slot=slot,handle=50+slot,anchor=anchor)
        image.cpu.mem_write(relative(0x47c94+slot*2),struct.pack('<H',current['handle'] if present else 65535))
        for at,value in zip((0x489a3,0x489a9,0x489ae),(100,200,300)):image.cpu.mem_write(relative(at),struct.pack('<i',value))
        image.cpu.mem_write(relative(0x6814c+5*32),struct.pack('<3i',*anchor))
        image.cpu.mem_write(relative(0x4b946),b'\x35\x12')
        image.cpu.mem_write(0x300000,struct.pack('<3H',5*32,slot*2,0))
        image.cpu.reg_write(r.UC_X86_REG_ESI,0x300000)
        before=len(entries);image.call(0xbc8f0)
        assert len(entries)-before==int(present)
        assert image.cpu.mem_read(relative(0x4b946),2)==b'\x35\x12'
        assert [struct.unpack('<i',image.cpu.mem_read(relative(at),4))[0] for at in (0x489a3,0x489a9,0x489ae)]==[100,200,300]
subprocess.run([str(build/'attachment_tests')],check=True)
models=json.loads((root/'analysis/models/data.js').read_text().split('=',1)[1].strip().rstrip(';'))['models'];byname={m['name']:m for m in models};raw=(root/'installs/cd_1994_09/TFX/TFX.DAT').read_bytes();data=973476
weapons=[]
for i in range(1,23):
 ptr=struct.unpack_from('<I',raw,data+0x809c+i*48+8)[0];name=raw[data+ptr:].split(b'\0',1)[0].decode()[:8];weapons.append(byname[name])
cases=[(byname[n],w,slot) for n in ['efa','f117','f22','efa_glob','f17_glob','f22_glob'] for w in weapons for slot in range(11)]
script=r'''
const fs=require('fs'),vm=require('vm');
for(const f of ['analysis/models/data.js','analysis/models/model.js'])vm.runInThisContext(fs.readFileSync(f,'utf8'));
const models=new Map(TFX_DATA.models.map(m=>[m.id,m]));
for(const [id,weapon,slot] of JSON.parse(fs.readFileSync(0,'utf8'))){
const externalModels=Array(10).fill(null);if(slot===10)externalModels.fill(models.get(weapon));else externalModels[slot]=models.get(weapon);
const mesh=TFXModel.inspect(models.get(id),{rules:false,referenceScale:1,externalModels});
console.log(JSON.stringify(mesh.primitives.map(p=>[{face:0,line:1,point:2}[p.kind],p.colour,p.mode??-1,p.pixelSize||0,p.radius||0,p.sourceOffset,(p.vertices||[p.vertex]).map((v,i)=>[...v,p.shades?.[i]??-1])])));
}
'''
expected=subprocess.check_output(['node','-e',script],cwd=root,input=json.dumps([(m['id'],w['id'],s) for m,w,s in cases]).encode()).splitlines()
requests=''.join(f"{int(m['id'],16)} 0 0 0 {int(w['id'],16)} {s}\n" for m,w,s in cases)
actual=subprocess.check_output([str(build/'tfx_probe'),'attachments',str(root/'installs/cd_1994_09/TFX')],input=requests.encode()).splitlines()
for case,a,b in zip(cases,actual,expected):
 a=json.loads(a)[1];b=json.loads(b);label=(case[0]['name'],case[1]['name'],case[2]);assert len(a)==len(b),(label,'count',len(a),len(b))
 for ap,bp in zip(a,b):
  assert ap[:6]==bp[:6],(label,'metadata',ap[:6],bp[:6])
  assert len(ap[6])==len(bp[6])
  for av,bv in zip(ap[6],bp[6]): assert all(math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-9) for x,y in zip(av[:4],bv)),(label,av,bv)
print(f'Carried-store checks passed: 20 native state cases, {len(cases)} retail preview loadouts')
