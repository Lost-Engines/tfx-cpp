#!/usr/bin/env python3
"""Compare every shipped menu with its original interpreter and hit-test routine.

Script loading, VGA background output, pointer output and selection-box flashing
are boundaries. Native tokenisation, box registration, label lookup, numeric
assignment/return and inclusive mouse hit testing execute unchanged.
"""
import argparse
from pathlib import Path
import json
import random
import struct
import subprocess
from unicorn import x86_const as r
from native_reference import NativeReference

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
args=parser.parse_args();directory=args.research/'installs/cd_1994_09/TFX';image=NativeReference(directory/'TFX.DAT');cpu=image.cpu;cpu.mem_map(0x300000,0x40000);rng=random.Random(0xd52d0)
backdrop=''
def string(pointer):return bytes(cpu.mem_read(pointer,128)).split(bytes(1))[0].decode('ascii')
def background(im):
    global backdrop
    backdrop=string(im.cpu.reg_read(r.UC_X86_REG_EAX));im.cpu.reg_write(r.UC_X86_REG_EAX,1);im.return_from()
image.intercept(0xc6f64,'Capture the menu bitmap filename without loading/drawing VGA planes.',background)
for file in (0xc72c0,0xc734c,0xc6348,0xd5750,0xd53e4):image.intercept(file,'Mouse/graphics initialisation, interactive display and selection-box flash are outside script execution.',lambda im:im.return_from())
image.intercept(0xd21a4,'Custom cursor drawing is outside hit testing.',lambda im:im.return_from(16))
variables=next(p for p in json.loads((args.research/'analysis/presentations/programs.json').read_text()) if p['name']=='tfx')['variables'];image.write(0x1afee,'<H',len(variables))
for index,variable in enumerate(variables):
    image.write(0x1ad44+index,'<B',variable['string_value']);cpu.mem_write(image.data+0x1ad62+index*21,variable['name'].encode()+bytes(21-len(variable['name'])))
rows=[];expected=[];choices=points=0
for path in sorted((args.research/'extracted/cd_1994_09/resources/lev').glob('*.opt')):
    source=path.read_bytes();cpu.mem_write(0x300000,source+bytes(1));image.write(0x24bec,'<I',0x300000);backdrop='';image.call(0xd58ac,limit=1000000)
    animated=image.read(0x24c97,'<B')[0];count=image.read(0xd85c,'<H')[0];mouse=image.read(0xdf5a,'<H')[0];nobox=image.read(0x24c99,'<B')[0]
    expected.append(f"{backdrop if not animated else ''}|{string(image.data+0x24bd8) if animated else ''}|{mouse}|{int(not nobox)}")
    positions=[(-32768,-32768),(32767,32767),(0,0),(319,199)]
    for index in range(count):
        bounds=struct.unpack('<4h',cpu.mem_read(image.data+0x24700+index*19,8));label=string(image.data+0x24708+index*19).removesuffix(':');before=[]
        for ordinal,variable in enumerate(variables):
            value=0x12345678+ordinal;image.write(0x1a400+ordinal*4,'<I',value);before.append(value)
        image.call(0xd5560,eax=index);image.call(0xd5618,limit=1000000)
        assignments=[]
        for ordinal,variable in enumerate(variables):
            value=image.read(0x1a400+ordinal*4,'<I')[0]
            if value!=before[ordinal]:assignments.append(f"{variable['name']}={value},")
        expected.append(' '.join(map(str,bounds))+' '+label+':'+''.join(assignments));choices+=1
        x1,y1,x2,y2=bounds
        positions.extend((x,y) for x in (x1-1,x1,x2,x2+1) for y in (y1-1,y1,y2,y2+1))
    positions.extend((rng.randrange(-20,341),rng.randrange(-20,221)) for _ in range(2048))
    values=[]
    for x,y in positions:values.append(str(image.call(0xd52d0,eax=x&0xffffffff,edx=y&0xffffffff)&65535));points+=1
    expected.append(' '.join(values)+' ')
    rows.append(path.stem+' '+str(len(positions))+' '+' '.join(f'{x} {y}' for x,y in positions)+'\n')
result=subprocess.run([str(args.build/'menu_probe'),str(directory)],input=''.join(rows),capture_output=True,text=True);assert result.returncode==0,result.stderr
actual=result.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
for index,(a,b) in enumerate(zip(actual,expected)):assert a==b,(index,a[:150],b[:150])
print(len(rows),'native menu scripts,',choices,'label/assignment paths and',points,'mouse positions agree')
