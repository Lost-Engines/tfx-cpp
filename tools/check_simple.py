#!/usr/bin/env python3
"""Compare complete persistent Simple flight callbacks with original 2.05.

Native player/engine initialisers and the complete ordinary 0x8f56c callback
execute. Timer, mouse/joystick acquisition, HUD/control startup and output delivery are explicit
boundaries. Supplied ground observations and control changes are not inferred.
Automatic recovery, ILS and fatal-player mission handling are separate consumers.
"""
import argparse
from pathlib import Path
import struct
import subprocess
from native_reference import NativeReference,r

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--build',type=Path,default=Path('build'))
parser.add_argument('--record',type=Path)
a=parser.parse_args();data=a.research/'installs/cd_1994_09/TFX'
names=[]
names += ['position_'+axis for axis in 'xyz']+['integer_'+axis for axis in 'xyz']
names += [basis+str(i) for basis in ('body','visible') for i in range(9)]
names += ['remainder_'+axis for axis in 'xyz']
names += ['mach','throttle','minimum_mach','maximum_mach','target_mach','metres_per_second','altitude','movement','unrounded_mach','fixed_speed']
names += ['landed','low_speed_ground','recovering','gear_down','brake_chute','chute_cutaway','arrestor_hook','arrested','left_engine','right_engine','collision','gear_condition','afterburner','fuel_readout','normalisation_counter','fuel','fuel_flow']
names += ['pitch','heading','roll','pitch_rate','heading_rate','roll_rate','negative_pitch_limit','positive_pitch_limit','roll_limit','turn_response','turn_rate','turn_speed','g_load','bank_correction','stall_pitch','landing_pitch','landing_roll','previous_landed','indicated_speed','low_speed_reference','geometric_altitude','gear_descent_speed','reported_speed']

def words(im):
    result=[im.read(p,'<I')[0] for p in (0x1341c,0x13428,0x13434)]
    result += [im.read(p,'<i')[0]&0xffffffff for p in (0x13424,0x13430,0x1343c)]
    result += [v&0xffffffff for p in (0x1345e,0x1344c) for v in im.read(p,'<9h')]
    result += list(im.read(0x13480,'<3I'))
    result += [im.read(p,'<I')[0] for p in (0x86f4,0x133f8,0x133bc,0x133b8,0x133cc,0x133e8,0x133d8,0x133c0)]
    result += [im.read(0x14778,'<Q')[0],im.read(0x13444,'<i')[0]&0xffffffff]
    result += [int(im.read(p,'<H')[0]!=0) for p in (0x8d3a,0x8d38,0x13474)]
    result += [int(im.read(0x146d8,'<d')[0]!=0)]
    result += [int(im.read(p,'<H')[0]!=0) for p in (0x14964,0x14966,0x8d12,0x8d14)]
    result += [int(im.read(p,'<d')[0]!=0) for p in (0x14880,0x14888)]
    result += [im.read(0x12c04,'<h')[0]&0xffffffff,im.read(0x7d7a,'<B')[0],im.read(0x1496d,'<B')[0],im.read(0x6c3c,'<h')[0]&0xffffffff,im.read(0x86fa,'<H')[0]]
    result += [im.read(p,'<Q')[0] for p in (0x14858,0x14308)]
    result += list(im.read(0x86c8,'<3H'))
    result += [im.read(p,'<I')[0] for p in (0x86dc,0x86e0,0x86e4,0x133d0,0x133d4,0x133a4,0x133a0,0x133c8,0x1339c,0x133f4)]
    result += [im.read(p,'<h')[0]&0xffffffff for p in (0x878e,0x8790,0x8792,0x8794)]
    result += [int(im.read(0x86b4,'<H')[0]!=0)]
    result += [im.read(p,'<Q')[0] for p in (0x14418,0x14290)]
    result += [im.read(p,'<I')[0] for p in (0x8788,0x133ec,0x13440)]
    assert len(result)==len(names),(len(result),len(names))
    return result

cases=[]
for craft in (1,2,3):
    for source in (0,1):
        for variant in range(4):
            position=[293888,[-800,-9500,-500,-20][variant],236544]
            if variant==2:position=[409000,-500,409000]
            angles=[0,[32767,24576,8192,0][variant],8192 if variant==1 else 0]
            header=[craft,256,*position,*angles,.65,source,0,0,0,variant==3,1200 if variant==2 else -1]
            controls=[]
            for frame in range(256):
                phase=frame%64
                controls.append([[2,4,10,18][frame%4],-128 if phase<16 else 128 if phase<32 else 0,64 if phase<16 else -64 if phase<32 else 0,int(phase<16),int(phase<8),int(32<=phase<48),int(16<=phase<24),1 if frame%4==0 else 2 if frame%4==2 else 0,int(frame<180),int(frame>=220),1 if frame==32 else 0 if frame==64 else -1,3 if frame==0 or frame==128 else 1 if frame==96 else -1])
            cases.append((header,controls))
for craft in (1,2,3):
    for height in (0,-20):
        for engines in (0,3):
            header=[craft,768,125952,0,48128,0,0,0,0,0,1,1,height,0,-1]
            controls=[[4,0,0,0,0,int(bool(engines) and frame in (180,240,300)),0,0,1,0,-1,engines if frame==0 else -1] for frame in range(768)]
            cases.append((header,controls))
payload='\n'.join(' '.join(str(int(v)) if isinstance(v,bool) else str(v) for v in row) for header,controls in cases for row in (header,*controls))+'\n'
output=subprocess.check_output([str((a.build/'simple_probe').resolve())],input=payload.encode()).decode().splitlines();assert len(output)==sum(len(c) for h,c in cases)
cursor=0;fixtures=[]
for case,(header,controls) in enumerate(cases):
    craft,frames,x,y,z,pitch,heading,roll,speed,source,landed,present,height,rudder,entry=header
    im=NativeReference(data/'TFX.DAT');im.cpu.mem_map(0x300000,4096)
    im.intercept(0x744e4,'No host DOS mouse driver; original player setup executes',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
    for address,reason in ((0x74614,'Mouse range reset has no physics effect'),(0x8c43c,'Supply elapsed ticks; native timer has separate comparisons'),(0x74508,'Supply mouse/button samples explicitly'),(0xc4ac0,'Supply calibrated joystick axes explicitly; native Simple response executes'),(0xb52d4,'Record boundary for model-entry delivery; it does not change this flight-state capture'),(0x7dde4,'Warning presentation is outside the numerical callback comparison'),(0xa4dfc,'Sample playback is outside numerical flight state'),(0xa4edc,'Tone output is outside numerical flight state'),(0xa6068,'No optional external control device is connected')):
        im.intercept(address,reason,lambda image:image.return_from())
    for p,v in zip((0x13424,0x13430,0x1343c),(x,y,z)):im.write(p,'<i',v)
    im.write(0x86c8,'<3H',pitch,heading,roll);im.write(0x86f4,'<f',speed);im.write(0x11b2a,'<H',craft-1);im.write(0x1347a,'<B',2);im.write(0x11b3c,'<B',landed)
    if landed:
        im.intercept(0xb0d80,'Supply start-cell terrain lookup; actual ground placement executes',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,0),image.return_from()))
        im.intercept(0xb7a3c,'Supply checked runway/carrier start type without executing the separate terrain classifier',lambda image:(image.cpu.reg_write(r.UC_X86_REG_EAX,50 if height==0 else 0),image.return_from()))
    im.call(0x8c184,limit=2000000);im.call(0x8c318)
    im.write(0x13478,'<B',source);im.write(0x8867,'<B',0);im.write(0xabea,'<B',present);im.write(0xabf2,'<h',height);im.write(0x8e22,'<B',1);im.write(0x1b23c,'<I',0x300000);im.cpu.mem_write(0x300038,bytes([rudder]))
    if entry>=0:im.write(0x13444,'<i',entry)
    im.write(0x7d7a,'<B',1 if landed else 2) # Separately verified native HUD startup 0x7df30/0x7e047.
    if landed:
        placing=[True]
        def placement_complete(image):
            if not placing[0]:return
            placing[0]=False
            frame=image.cpu.reg_read(r.UC_X86_REG_EBP)
            previous,saved_edx,saved_ebx,destination=struct.unpack('<4I',image.cpu.mem_read(frame,16))
            for register,value in ((r.UC_X86_REG_EBP,previous),(r.UC_X86_REG_EDX,saved_edx),(r.UC_X86_REG_EBX,saved_ebx),(r.UC_X86_REG_ESP,frame+16),(r.UC_X86_REG_EIP,destination)):image.cpu.reg_write(register,value)
        im.intercept(0x8f686,'Complete original initial ground placement before supplied engine/control changes; later full callbacks execute',placement_complete)
        im.call(0x8f56c,limit=2000000)
    previous_buttons=0;digest=14695981039346656037;fixtures.append(' '.join(str(int(v)) if isinstance(v,bool) else str(v) for v in header))
    for frame,row in enumerate(controls):
        ticks,joyx,joyy,up,left,down,right,buttons,accelerate,decelerate,gear,engines=row
        im.write(0x13476,'<H',ticks);im.write(0xac60,'<2h',joyx,joyy);im.write(0x5968,'<H',buttons);im.write(0x596a,'<H',previous_buttons)
        for p,v in zip((0x13256,0x13258,0x1325c,0x1325e,0x1325a,0x13260),(up,left,down,right,accelerate,decelerate)):im.write(p,'<H',v)
        if gear>=0:im.write(0x146d8,'<d',float(gear));im.write(0x7d7a,'<B',1 if gear else 2)
        if engines>=0:
            im.write(0x14880,'<d',float(bool(engines&1)));im.write(0x14888,'<d',float(bool(engines&2)))
        # Supply the engine display state at the checked HUD/control boundary,
        # as in the independent Arcade callback comparison.
        for engine,visual in ((0x14880,0x7d72),(0x14888,0x7d75)):im.write(visual,'<B',1 if im.read(engine,'<d')[0] else 2)
        im.call(0x8f56c,limit=2000000);previous_buttons=buttons
        expected=words(im);actual=list(map(int,output[cursor].split()));cursor+=1
        assert actual==expected,(case,craft,source,frame,[(name,x,y) for name,x,y in zip(names,actual,expected) if x!=y],len(actual),len(expected))
        for value in expected:
            for byte in struct.pack('<Q',value):digest=((digest^byte)*1099511628211)&0xffffffffffffffff
        fixtures.append(' '.join(map(str,row)))
    fixtures.append(str(digest))
if a.record:a.record.write_text('\n'.join(fixtures)+'\n')
print(f'Complete Simple callback agrees across {len(cases)} persistent initialised trajectories and {cursor} original float-bit/pose/control/gear/fuel updates')
