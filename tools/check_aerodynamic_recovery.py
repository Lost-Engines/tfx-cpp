#!/usr/bin/env python3
"""Compare complete original 0x85a7c recovery engage/restore state and requests.

Original startup and reheat handlers execute; only sound/radio/SSD delivery is
observed separately. Saved reheat targets are restricted to reachable states:
the original loop does not terminate otherwise.
"""
import argparse
from pathlib import Path
import random
import struct
import subprocess
from native_reference import NativeReference,r

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--record',type=Path)
a=p.parse_args();im=NativeReference(a.research/'installs/cd_1994_09/TFX/TFX.DAT');im.call(0xde851);rng=random.Random(0x85a7c);events=[]
for file,kind in ((0xa4dfc,'play'),(0xa4edc,'sound'),(0xb52d4,'model'),(0x81198,'radio')):
    def callback(image,kind=kind):
        events.append((kind,image.cpu.reg_read(r.UC_X86_REG_EAX),image.cpu.reg_read(r.UC_X86_REG_EDX)));image.return_from()
    im.intercept(file,'Observe recovery/reheat '+kind+' delivery without substituting control logic',callback)
bits=lambda v:struct.unpack('<Q',struct.pack('<d',v))[0]
fbits=lambda v:struct.unpack('<I',struct.pack('<f',v))[0]
cases=[]
for i in range(8192):
    stages=rng.choice([0,4]);after=rng.randrange(stages+1);saved=rng.randrange(stages+1);fuel=rng.choice([0,1000]);left=rng.choice([0,1]);right=rng.choice([0,1])
    if saved>after and (fuel==0 or left==right==0):saved=after
    flags=[int(i%2==0),int(i%13==0),int(i%17==0),int(i%19==0),int(i%23==0)]
    cases.append([*flags,stages,rng.randrange(8),rng.randrange(8),rng.randrange(5),rng.randrange(4),i%2,(i//2)%2,rng.choice([1,2,11,14]),rng.choice([1,2,11,14]),after,saved,rng.randrange(4),rng.randrange(4),(i//4)%2,fbits(rng.uniform(0,1)),*map(bits,[rng.uniform(0,1),rng.uniform(0,1),left,right,fuel])])
output=subprocess.check_output([str((a.build/'aerodynamic_recovery_probe').resolve())],input=('\n'.join(' '.join(map(str,row)) for row in cases)+'\n').encode()).decode().splitlines();assert len(output)==len(cases)
fixtures=[];engaged=restored=changes=0
for index,(row,line) in enumerate(zip(cases,output)):
    available,inhibited,crashed,ejected,landed,stages,configuration,saved_configuration,mode,saved_mode,enabled,saved_enabled,brake,saved_brake,after,saved,control,display,pending,throttle,saved_throttle,target,left,right,fuel=row
    craft=1 if stages==0 else 0
    for field,value,fmt in ((0x8867,available,'<B'),(0xabe9,inhibited,'<B'),(0x12c04,crashed,'<H'),(0x86ce,ejected,'<B'),(0x8d3a,landed,'<H'),(0x11b2a,craft,'<H'),(0x8cd8+craft,stages,'<B'),(0x14962,configuration,'<H'),(0x1327a,saved_configuration,'<H'),(0x14960,mode,'<H'),(0x1327c,saved_mode,'<H'),(0x14958,enabled,'<H'),(0x1327e,saved_enabled,'<H'),(0x7d77,brake,'<B'),(0x13278,saved_brake,'<H'),(0x1496d,after,'<B'),(0x13269,saved,'<B'),(0x10bed,control,'<B'),(0x6c38,display,'<B'),(0x1347b,255 if pending else 1,'<B'),(0x133f8,throttle,'<I'),(0x13270,saved_throttle,'<Q'),(0x14890,target,'<Q'),(0x14880,left,'<Q'),(0x14888,right,'<Q'),(0x14858,fuel,'<Q')):im.write(field,fmt,value)
    im.write(0xe76c,'<H',23);events.clear();im.call(0x85a7c,limit=100000)
    change=0 if inhibited or crashed or ejected or landed or (mode!=4 and not available) else 2 if mode==4 else 1
    reheat=[]
    if change==1:
        assert events[0][:2]==('play',0x3e) and events[1][0:2]==('radio',im.data+0x1990),events
        assert len(events)==2
    elif change==2:
        cursor=after;expected_events=[]
        while cursor!=saved:
            if cursor<saved:
                if cursor==0:expected_events.append(('model',23,9))
                expected_events.append(('sound',0x4b,None));reheat.append(1 if cursor==0 else 2);cursor+=1
            else:
                expected_events.append(('sound',8,None));cursor-=1;reheat.append(4 if cursor==0 else 3)
                if cursor==0:expected_events.append(('model',23,10))
        assert len(events)==len(expected_events),(index,events,expected_events)
        assert all(actual[:2]==expected[:2] and (expected[2] is None or actual[2]==expected[2]) for actual,expected in zip(events,expected_events)),(index,events,expected_events)
    else:assert not events
    expected=[im.read(field,fmt)[0] for field,fmt in ((0x14962,'<H'),(0x1327a,'<H'),(0x1327c,'<H'),(0x1327e,'<H'),(0x13278,'<H'),(0x13270,'<Q'),(0x13269,'<B'))]+[int(im.read(0x1347b,'<B')[0]==255)]+[im.read(field,fmt)[0] for field,fmt in ((0x14958,'<H'),(0x14960,'<H'),(0x7d77,'<B'),(0x133f8,'<I'),(0x14890,'<Q'),(0x1496d,'<B'),(0x10bed,'<B'),(0x6c38,'<B'))]+[change,len(reheat),*reheat]
    actual=list(map(int,line.split()));assert actual==expected,(index,[(i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y])
    engaged+=change==1;restored+=change==2;changes+=len(reheat)
    if index%67==0:fixtures.append(' '.join(map(str,row+expected)))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
assert engaged>1000 and restored>500 and changes>100
# Empty fuel makes the native restoration loop retry an unavailable increase
# indefinitely. Bound the original and require the translated diagnostic.
invalid=[1,0,0,0,0,4,1,1,4,0,1,0,2,2,0,1,0,0,0,fbits(.5),bits(.6),bits(.7),bits(1),bits(1),bits(0)]
failed=subprocess.run([str((a.build/'aerodynamic_recovery_probe').resolve())],input=(' '.join(map(str,invalid))+'\\n').encode(),capture_output=True)
assert failed.returncode==1 and b'cannot restore unavailable recovery afterburner state' in failed.stderr,failed
im.write(0xabe9,'<B',0);im.write(0x12c04,'<H',0);im.write(0x86ce,'<B',0);im.write(0x8d3a,'<H',0);im.write(0x14960,'<H',4);im.write(0x1496d,'<B',0);im.write(0x13269,'<B',1);im.write(0x14858,'<d',0);im.write(0x11b2a,'<H',0);im.write(0x8cd8,'<B',4)
try:im.call(0x85a7c,limit=4096)
except RuntimeError as error:assert 'did not return within 4096' in str(error)
else:raise AssertionError('unavailable native reheat restoration unexpectedly terminated')
print(f'{len(cases)} original recovery toggles agree: {engaged} engagements, {restored} restorations and {changes} ordered reheat changes; only output delivery intercepted')
