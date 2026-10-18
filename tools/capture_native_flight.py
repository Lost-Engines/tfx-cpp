#!/usr/bin/env python3
"""Capture a bounded complete original TFX 2.05 launch and flight.

Executes real renderer/EMM/configuration/environment/mission/arming/AI/flight
initialization and the original frame loop. The host supplies silent DOS I/O,
private memory, keyboard/mouse transport, fixed timer samples and planar VGA.
Inherited presentation variables are explicit inputs from the independent
research parser. No game instruction or original installation is modified.
Requires Unicorn and the independent did-unpack module in the research tree.
"""
from pathlib import Path
import argparse,struct,sys,json,hashlib
from native_reference import r
from native_dpmi import DpmiReference
from flight_inputs import FlightInputs,KEYS
from native_vga import VgaCapture
from unicorn import UC_HOOK_CODE,UC_HOOK_INSN,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ

class SessionVideo(VgaCapture):
 def __init__(self,image,aperture=0xa0000):
  self.vram=[bytearray(65536) for _ in range(4)]
  self.image=image;self.aperture=aperture;image.cpu.mem_map(aperture,65536);self.reset()
  image.cpu.hook_add(UC_HOOK_INSN,self._out,None,1,0,r.UC_X86_INS_OUT)
  image.cpu.hook_add(UC_HOOK_MEM_READ,self._read,begin=aperture,end=aperture+65535)
  image.cpu.hook_add(UC_HOOK_MEM_WRITE,self._write,begin=aperture,end=aperture+65535)
 def get(self,field):return struct.unpack('<H',self.image.cpu.mem_read(self.image.native(0x70aa4+field),2))[0]
 def reset(self,colour=0):
  for plane in self.vram:plane[:]=bytes([colour])*65536
  self.index=self.mask=self.gc_index=self.read_plane=self.rotate=self.logic=self.write_mode=0;self.bit_mask=255;self.latches=[bytes(16) for _ in range(4)]
 def pixels(self):
  start=(self.get(0x55907)<<4)-self.aperture
  assert 0<=start<=65536-16000,hex(start)
  return self._deplane([plane[start:start+16000] for plane in self.vram])
 def _read(self,cpu,access,address,size,value,unused):
  if address<self.aperture or address+size>self.aperture+65536:return
  offset=address-self.aperture
  self.latches=[bytes(plane[offset:offset+size]) for plane in self.vram]
  cpu.mem_write(address,self.latches[self.read_plane])
 def _write(self,cpu,access,address,size,value,unused):
  if address<self.aperture or address+size>self.aperture+65536:return
  raw=(value&((1<<(size*8))-1)).to_bytes(size,'little')
  for index,byte in enumerate(raw):
   at=address+index-self.aperture
   for plane in range(4):
    if not(self.mask&(1<<plane)):continue
    latched=self.latches[plane][index] if index<len(self.latches[plane]) else 0
    if self.write_mode==1:result=latched
    else:
     assert self.write_mode==0,self.write_mode
     colour=((byte>>self.rotate)|(byte<<(8-self.rotate)))&255
     if self.logic==8:colour&=latched
     elif self.logic==16:colour|=latched
     elif self.logic==24:colour^=latched
     result=(colour&self.bit_mask)|(latched&~self.bit_mask&255)
    self.vram[plane][at]=result

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--mission',type=int,default=501)
parser.add_argument('--flight-model',choices=('arcade','simple','military-spec','realistic'),default='arcade')
parser.add_argument('--frames',type=int,default=4)
parser.add_argument('--ticks-per-frame',type=int,default=4,help='declared external timer interval; native frame clamps still execute')
parser.add_argument('--until-result',action='store_true',help='capture through a natural mission result, with --frames as the upper bound')
parser.add_argument('--inputs',type=Path,help='declared per-frame keyboard events/held keys as JSON')
args=parser.parse_args()
inputs=FlightInputs.read(args.inputs)if args.inputs else FlightInputs([])
if not 1 <= args.frames <= 1024:parser.error('--frames must be between 1 and 1024')
if not 4 <= args.ticks_per_frame <= 65535:parser.error('--ticks-per-frame must be between 4 and 65535; each supplied interval must complete the native timer polls')
root=args.research.resolve();directory=root/'installs/cd_1994_09/TFX'
args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'did-unpack'))
from did_unpack import Archive
im=DpmiReference(directory/'TFX.DAT',data_base=0x100000);video=SessionVideo(im,aperture=0xa0000)
from native_recording import MemoryFiles
memory_files=MemoryFiles(im)
# Native 0x75940 clears its shot pointer with zero, then reads flat address
# 0x4b. DOS permits that low-memory read; the cleared owner is unused before
# the next source selection overwrites it. Preserve the original helper.
im.cpu.mem_map(0,4096)
im.cpu.mem_map(0x400000,0x4000000);heap=[0x410000]
archive=Archive.read(directory/'DID.DAT');entries={x.identifier:x for x in archive.entries};loads=[]
def string(address):
 if not address:return '<null>'
 return bytes(im.cpu.mem_read(address,256)).split(bytes(1))[0].decode('cp437')
def read(name):
 name=name.replace('\\','/').lstrip('/').lower().removeprefix('tfx/')
 if name=='tfx.cfg':
  model={'arcade':0,'simple':1,'realistic':2,'military-spec':3}[args.flight_model]
  return f'CONTROL=0\r\nMODEL={model}\r\nSOUNDFX=0\r\nMUSIC=0\r\nREALISM=0,0,1,1,0,0,0\r\n'.encode()
 identifier=archive.hash_name(name)
 if identifier not in entries:raise RuntimeError('missing asset '+name)
 return archive.unpack(entries[identifier])
def allocate(current):
 size=current.cpu.reg_read(r.UC_X86_REG_EAX);address=heap[0];assert size<0x2000000,(hex(size),hex(address));heap[0]+=(size+15)&~15;assert heap[0]<0x4300000
 current.cpu.reg_write(r.UC_X86_REG_EAX,address);current.return_from()
# The inherited presentation allocator owns a byte-addressed arena. Let its
# original allocation routine run, rather than replacing internal bookkeeping.
parser_base=heap[0];heap[0]+=0x100000;im.write(0x1acfc,'<I',parser_base)
for address in (0xd3820,):im.intercept(address,'Capture-owned bounded zeroed allocations at the host memory boundary.',allocate)
for address in (0xd36ef,):im.intercept(address,'Retain host allocations until the bounded native session ends.',lambda current:current.return_from())
def length(current):
 name=string(current.cpu.reg_read(r.UC_X86_REG_EAX))
 try:value=read(name)
 except RuntimeError:value=b''
 loads.append(('length',name,len(value)));current.cpu.reg_write(r.UC_X86_REG_EAX,len(value));current.return_from()
def file(current):
 name=string(current.cpu.reg_read(r.UC_X86_REG_EAX));value=read(name);destination=current.cpu.reg_read(r.UC_X86_REG_EDX);current.cpu.mem_write(destination,value);loads.append(('read',name,len(value)));
 current.cpu.reg_write(r.UC_X86_REG_EAX,len(value));current.return_from()
for address in (0xc8bec,0xc9c24):im.intercept(address,'Supply resource/file lengths from the original archive or explicit silent configuration.',length)
for address in (0xc8cf0,0xc9d4c):im.intercept(address,'Supply decoded original bytes at the archive/filesystem boundary.',file)
def join(current):
 name=''.join(string(current.cpu.reg_read(reg)) for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX));current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX),name.encode('cp437')+bytes(1));current.return_from()
im.intercept(0x7b494,'Supply the DOS pathname join for archive resources.',join)
im.intercept(0xc72c0,'Supply an available neutral virtual DOS mouse, required even for keyboard sessions.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,1),current.return_from()))
im.intercept(0x744e4,'Supply no DOS mouse driver for the explicit keyboard session.',lambda current:(current.cpu.reg_write(r.UC_X86_REG_EAX,0),current.return_from()))
# A nonempty DID root also enables the original loader's SPR subdirectory.
# The hosted filesystem strips this explicit virtual root before archive lookup.
im.intercept(0xc71b4,'Supply the explicit virtual DOS resource root TFX.',lambda current:(current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX),b'TFX\0'),current.return_from()))
im.intercept(0xc92f7,'Supply a fixed startup calendar.',lambda current:(current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX),bytes(16)),current.return_from()))
def fatal(current):
 stack=current.cpu.reg_read(r.UC_X86_REG_ESP);pointer=struct.unpack('<I',current.cpu.mem_read(stack+4,4))[0];raise RuntimeError('native fatal '+string(pointer))
im.intercept(0xb0eb0,'Fail explicitly at native fatal diagnostics.',fatal)
# Start with external hardware boundaries only. Expand only when execution
# identifies a real dependency; do not silently skip game simulation routines.
for address in (0xa5ce0,0xa6424,0xa6458,0xa629c):im.intercept(address,'Exclude external DOS audio loading and startup console/analogue calibration; the supplied configuration selects silent keyboard flight.',lambda current:current.return_from())
im.intercept(0xb3f2c,'DOS real-mode interrupt transport is hosted, without installing vectors.',lambda current:current.return_from())
im.intercept(0xa4ddc,'The explicit silent configuration has no external DOS audio device to initialize.',lambda current:current.return_from())
def keyboard(current):
 current.write(0x1b234,'<I',0x403000);current.write(0x1b238,'<I',0x403100);current.write(0x1b23c,'<I',0x403200);current.return_from()
im.intercept(0xb41e4,'Supply private keyboard transport arrays instead of installing the DOS IRQ handler; native translation initialization executes.',keyboard)
im.intercept(0xb43b4,'No host keyboard events are pending during startup.',lambda current:current.return_from())
entered=[False];frames=[0];snapshots=[]
mouse_polls=[0];mouse_buttons=[0];defaults_applied=[False]
im.intercept(0x8978c,'Observe the original DEFAULT button action; its complete native body executes.',lambda current:defaults_applied.__setitem__(0,True))
def mouse(current):
 if mouse_polls[0]>128 and not entered[0]:raise RuntimeError('Unconsumed mouse script after 128 polls')
 mouse_polls[0]+=1;mouse_buttons[0]=inputs.at(frames[0]).get('buttons',0) if entered[0] else int(mouse_polls[0]%32 in range(8,16))
 for offset,value in ((4,197 if defaults_applied[0] else 101),(8,199),(12,mouse_buttons[0])):
  pointer=struct.unpack('<I',current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))[0];current.cpu.mem_write(pointer,struct.pack('<H',value))
 current.return_from()
im.intercept(0xc72ff,'Supply explicit pointer input on the authored DEFAULT then DONE buttons.',mouse)
def held_mouse(current):
 if mouse_polls[0]>128 and not entered[0]:raise RuntimeError('Unconsumed mouse script after 128 polls')
 mouse_polls[0]+=1;mouse_buttons[0]=inputs.at(frames[0]).get('buttons',0) if entered[0] else int(mouse_polls[0]%32 in range(8,16));current.cpu.reg_write(r.UC_X86_REG_EAX,mouse_buttons[0]);current.return_from()
im.intercept(0xc733e,'Supply an explicit button press/release sequence while the original modal controller polls.',held_mouse)
mouse_motion_frame=[None]
def relative_mouse(current):
 motion=[0,0]
 if entered[0] and mouse_motion_frame[0]!=frames[0]:
  motion=inputs.at(frames[0]).get('mouse',motion);mouse_motion_frame[0]=frames[0]
 for offset,value in zip((4,8),motion):
  pointer=struct.unpack('<I',current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))[0];current.cpu.mem_write(pointer,struct.pack('<h',value))
 current.return_from()
im.intercept(0xc7326,'Supply declared relative virtual-mouse movement, consumed once per input frame.',relative_mouse)
retrace_reads=[0]
def input_port(cpu,port,size,unused):
 if port==0x3da:
  retrace_reads[0]+=1;return 8 if retrace_reads[0]&1 else 0
 if port==0x3cf:
  values={3:video.rotate|video.logic,4:video.read_plane,5:video.write_mode,8:video.bit_mask}
  if video.gc_index in values:return values[video.gc_index]
 raise RuntimeError("undeclared hardware input port/register " + hex(port) + '/' + hex(video.gc_index))
im.cpu.hook_add(UC_HOOK_INSN,input_port,None,1,0,r.UC_X86_INS_IN)
clock=[0]
def timer(current):
 if not entered[0]:clock[0]+=4
 current.write(0x16f2c,'<I',clock[0]);current.return_from()
im.intercept(0xa6134,'Supply an explicit monotonically advancing launcher timer.',timer)
# Original startup installs Watcom floating formatting and its x87 environment.
im.call(0xde851);im.call(0xde547);im.call(0xde81e)
# The presentation graph normally owns these inherited campaign declarations.
# Match the C++ direct --mission runner: Arcade scoring/permission eligibility
# is independent of the selected numerical flight model.
program=next(p for p in json.loads((root/'analysis/presentations/programs.json').read_text()) if p['name']=='tfx')
presentation_numbers={'mission':args.mission,'arcade':1}
im.write(0x1afee,'<H',len(program['variables']))
for index,variable in enumerate(program['variables']):
 name=variable['name'];im.write(0x1ad44+index,'<B',variable['string_value']);im.cpu.mem_write(im.data+0x1ad62+index*21,name.encode()+bytes(21-len(name)))
 value=presentation_numbers.get(name,0)
 if variable['string_value']:
  value=0x402000+index*64;im.cpu.mem_write(value,b'NATIVE TEST\0')
 im.write(0x1a400+index*4,'<I',value)
im.cpu.mem_write(0x400000,b'tfx\0');im.cpu.mem_write(0x400100,str(args.mission).encode()+bytes(1));im.cpu.mem_write(0x400200,struct.pack('<2I',0x400000,0x400100));im.write(0x1b238,'<I',0x400300);im.write(0x1b23c,'<I',0x400400)
def begin(current):
 for page in range(1,5):
  assert ('read',f'TFX\\SPR\\global_{page}.TM',49152) in loads,('global texture page was not loaded',page)
 entered[0]=True;mouse_buttons[0]=0
im.intercept(0x72018,'Observe native flight entry and end the explicitly supplied arming input; the original session body executes.',begin)
def actors_snapshot(current):
 result=[]
 for pool,base in enumerate((0x11034,0x10f6c)):
  for index in range(50):
   pointer=current.read(base+index*4,'<I')[0]
   if not pointer:continue
   raw=bytes(current.cpu.mem_read(pointer,68))
   result.append([pool*50+index,*struct.unpack_from('<3i3Hi3hihhI',raw),struct.unpack_from('<H',raw,66)[0],*raw[40:42],*raw[64:66]])
 return result

def sensor_snapshot(current):
 # The original reuses the air-guidance scratch pointer for a designated
 # ground point during weapon release. This array enumerates aircraft only;
 # actual projectile guidance coordinates are observed separately below.
 identities={0:-1,current.data+0x135a0:-1}
 for pool,base in enumerate((0x11034,0x10f6c)):
  for index in range(50):
   pointer=current.read(base+index*4,'<I')[0]
   if pointer:identities[pointer]=pool*50+index
 identity=lambda pointer:identities[pointer]
 slots=current.read(current.read(0x76c8,'<I')[0]-current.data,'<20I')
 return [current.read(0x76d0,'<h')[0],identity(current.read(0x11108,'<I')[0]),*[identity(p) for p in slots],int(current.read(0x763e,'<H')[0]!=0),current.read(0x7774,'<h')[0],identity(current.read(0x135c8,'<I')[0]),identity(current.read(0x135d0,'<I')[0]),*current.read(0x135c0,'<2i'),*current.read(0x135cc,'<2h'),*current.read(0x135d4,'<2h'),int(current.read(0x8860,'<B')[0]!=0)]

hud_alert_events=[]
def observe_hud_alert(current):
 if not entered[0]:return
 pointer=current.cpu.reg_read(r.UC_X86_REG_EAX)-current.data
 assert pointer in (0x6fbe,0x6f12),hex(pointer)
 hud_alert_events.append({'frame':frames[0],'kind':int(pointer==0x6f12)})
im.intercept(0x7dde4,'Observe vector HUD alert requests; the original warning state and painter execute unchanged.',observe_hud_alert)
trail_events=[]
def observe_trail(current):
    stack=current.cpu.reg_read(r.UC_X86_REG_ESP)
    z,y,x=struct.unpack('<3i',current.cpu.mem_read(stack+4,12))
    trail_events.append([frames[0],x,y,z])
im.intercept(0x7b6cc,'Observe original smoke sample transport; its producer, allocation and animation execute unchanged.',observe_trail)
projectile_ids={}
next_projectile_id=[0]
def identify_projectile(cpu,address,size,unused):
 next_projectile_id[0]+=1
 projectile_ids[cpu.reg_read(r.UC_X86_REG_EAX)]=next_projectile_id[0]
# Assign identities only when the live pool allocator has linked a record.
# The shared constructor also builds temporary HUD prediction projectiles.
im.cpu.hook_add(UC_HOOK_CODE,identify_projectile,begin=im.native(0xa2d79),end=im.native(0xa2d79))
projectile_guidance=[]
def observe_projectile_guidance(cpu,address,size,unused):
 pointer=cpu.reg_read(r.UC_X86_REG_EAX)
 if not entered[0] or pointer not in projectile_ids:return
 # Only the real motion dispatch belongs to this boundary. HUD predictions
 # reuse projectile records and can call the same functions with copied state.
 caller=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP),4))[0]
 if caller!=im.native(0xa32a6):return
 body=bytes(cpu.mem_read(pointer,80));target=struct.unpack_from('<I',body,48)[0]
 projectile_guidance.append({'frame':frames[0],'weapon':body[6],'position':list(struct.unpack_from('<3i',body,8)),'target':list(struct.unpack('<3i',cpu.mem_read(target,12)))})
from check_projectiles import CALLBACKS
for address in CALLBACKS[1:]:im.cpu.hook_add(UC_HOOK_CODE,observe_projectile_guidance,begin=im.native(address),end=im.native(address))
def projectile_snapshot(current):
 from check_projectiles import KINDS
 head=current.read(0x16e80,'<I')[0];tail=current.read(0x16e7c,'<I')[0]
 if not head:return []
 pointer=struct.unpack('<I',current.cpu.mem_read(head+52,4))[0]
 result=[]
 while pointer!=tail:
  if len(result)>=98:raise RuntimeError('native projectile list exceeds its declared pool')
  body=bytes(current.cpu.mem_read(pointer,80));callback=struct.unpack_from('<I',body,60)[0]
  function=callback-0x10000+0x70aa4 if callback else 0
  result.append([projectile_ids[pointer],body[6],struct.unpack_from('<H',body,4)[0],KINDS[function],struct.unpack_from('<h',body,64)[0],*struct.unpack_from('<6i3Hihh',body,8),struct.unpack_from('<i',body,67)[0],body[66],body[79]])
  pointer=struct.unpack_from('<I',body,52)[0]
 return sorted(result)

bound_models={}
def observe_model_bind(cpu,address,size,unused):
 bound_models[cpu.reg_read(r.UC_X86_REG_EAX)]=cpu.reg_read(r.UC_X86_REG_EDX)&65535
im.cpu.hook_add(UC_HOOK_CODE,observe_model_bind,begin=im.native(0xb4d3c),end=im.native(0xb4d3c))

def player_parts_snapshot(current,bindings=False):
 handle=current.read(0xe76c,'<H')[0]
 table=current.read(0x21800,'<I')[0]
 instance=struct.unpack('<I',current.cpu.mem_read(table+(handle-1)*4,4))[0]
 definition=struct.unpack('<H',current.cpu.mem_read(instance,2))[0]&511
 source=current.read(0x1b250+definition*4,'<I')[0]
 count=current.cpu.mem_read(source+1,1)[0]
 return [bound_models.get(instance+16+29*part+9,65535)if bindings else list(current.cpu.mem_read(instance+16+29*part,8))for part in range(count)]

def snapshot(current):
 return {
  'frame':frames[0],
  'mission_progress':{
   'results':[current.read(at,'<i')[0]for at in (0x5c14,0x5c18,0x5c1c,0x5c24,0x5c28,0x5c30,0x5c20,0x5c2c,0x5c34,0x5c38)],
   'credited_targets':current.read(0x11b26,'<h')[0],
   'target_cursor':current.read(0x5d44,'<h')[0],
   'violations':current.read(0xe75c,'<h')[0],
   'exit_ticks':current.read(0x5940,'<h')[0],
   'remaining_timer':current.read(0xe708,'<i')[0],
   'resolved':bool(current.read(0x593e,'<B')[0]),
   'ended':bool(current.read(0x593a,'<h')[0]),
   'critical_loss':bool(current.read(0xe77c,'<B')[0]),
  },
  'position':[current.read(at,'<i')[0] for at in (0x13424,0x13430,0x1343c)],
  'angles':current.read(0x86c8,'<3H'),
  'speed':current.read(0x13444,'<i')[0],
  'speed_factor':current.read(0x86f4,'<I')[0],
  'elapsed':current.read(0x13476,'<H')[0],
  'cockpit_offset':[current.read(at,'<h')[0] for at in (0x10be8,0x10be6)],
  'view':current.read(0x87b8,'<h')[0],
  'cockpit_callback':hex(current.read(0xe70c,'<I')[0]+0x70aa4-0x10000),
  'environment_flags':current.read(0xe774,'<H')[0],
  'arena_free':current.read(0xad14,'<I')[0],
  'aiming_flags':[current.read(at,'<B')[0] for at in (0x7140,0x7148)],
  'cheat_state':[current.read(0x13250,'<H')[0],current.read(0x777e,'<H')[0]],
  'selected':current.read(0x93b0,'<h')[0],
  'stores':[current.read(0x13374+i*2,'<2B') for i in range(11)],
  'ground_phase':current.read(0xad7c,'<i')[0],
  'body_basis':current.read(0x1345e,'<9h'),
  'player_parts':player_parts_snapshot(current),
  'player_models':player_parts_snapshot(current,True),
  'launch_notice':current.read(0x6c41,'<B')[0],
  'control_configuration':[current.read(0x14962,'<H')[0],*[current.read(field,'<Q')[0]for field in (0x14360,0x148b8,0x148b0,0x148a8)]],
  'autopilot_targets':[current.read(field,fmt)[0]for field,fmt in ((0x14958,'<H'),(0x14960,'<H'),(0x1493a,'<H'),(0x14348,'<Q'),(0x8d40,'<Q'))],
  'air_brake':[current.read(0x145a8,'<Q')[0],current.read(0x7d77,'<B')[0]],
  'display_selection':[current.read(field,'<H')[0]for field in (0x713a,0x713c,0x713e,0x7d7c,0x7d7e)],
  'sensors':sensor_snapshot(current),
  'projectiles':projectile_snapshot(current),
  'armament':[current.read(0x93b0,'<h')[0],int(not current.read(0x7140,'<B')[0]),current.read(0x16e98,'<h')[0],current.read(0x809c+20,'<B')[0],*[v for slot in range(11)for v in current.read(0x13374+slot*2,'<2B')],current.read(0x14858,'<Q')[0]],
  'cannon':[current.read(0x16e9a,'<h')[0],current.read(0x16e96,'<H')[0]],
  'radar_pulse':bool(current.read(0x7772,'<B')[0]),
  'animation':[current.read(0xac90,'<B')[0],current.read(0xe74c,'<h')[0]],
  'pattern_seed':struct.unpack('<H',current.cpu.mem_read(current.native(0xe3a3f),2))[0],
  'timer':clock[0],
  'random':struct.unpack('<2H',current.cpu.mem_read(current.native(0xc9894),4)),
  'actors':actors_snapshot(current),
 }

def frame_boundary(current):
 snapshots.append(snapshot(current))
 if frames[0]==args.frames:
  current.cpu.emu_stop();return
 frames[0]+=1;clock[0]+=args.ticks_per_frame
 input=inputs.at(frames[0]);raw=bytearray(128)
 for name in input['held']:raw[KEYS[name][0]]=1
 current.cpu.mem_write(current.read(0x1b23c,'<I')[0],bytes(raw))
 current.cpu.mem_write(current.read(0x1b238,'<I')[0],bytes([KEYS[input['event']][0]if input['event'] else 0]))
im.intercept(0x72045,'Supply the declared external timer interval at each original frame boundary and stop after the requested complete frames.',frame_boundary)
terminal={}
def terminal_boundary(cpu,address,size,unused):
 # This is after the actual frame-tail retirement and before the native
 # result test leaves the flight loop. Keep the final live state intact.
 if args.until_result and not terminal and im.read(0x593a,'<h')[0]:
  snapshots.append(snapshot(im));terminal['frame']=frames[0]
  cpu.emu_stop()
im.cpu.hook_add(UC_HOOK_CODE,terminal_boundary,begin=im.native(0x723d7),end=im.native(0x723d7))
preflight_projection=[]
def observe_seeker_reset(cpu,address,size,unused):
 preflight_projection[:]=struct.unpack('<2h',cpu.mem_read(im.native(0x70aa4+0x47736),4))
im.cpu.hook_add(UC_HOOK_CODE,observe_seeker_reset,begin=im.native(0x930d4),end=im.native(0x930d4))
radio_events=[]
def observe_radio(cpu,address,size,unused):
 # Persistent 0x81254 calls the ordinary builder internally. Count the public
 # request once, matching radio_ticker::show(message,true).
 caller=struct.unpack('<I',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP),4))[0]
 if address==im.native(0x81198) and caller==im.native(0x8125c):return
 radio_events.append({'frame':frames[0],'message':string(cpu.reg_read(r.UC_X86_REG_EAX)),'persistent':address==im.native(0x81254)})
for file in (0x81198,0x81254):im.cpu.hook_add(UC_HOOK_CODE,observe_radio,begin=im.native(file),end=im.native(file))
cockpit_displays=[]
def observe_cockpit_displays(cpu,address,size,unused):
 if entered[0]:cockpit_displays.append({'frame':frames[0],'selection':[im.read(field,'<H')[0]for field in (0x713a,0x713c,0x713e,0x7d7c,0x7d7e)]})
im.cpu.hook_add(UC_HOOK_CODE,observe_cockpit_displays,begin=im.native(0x803e8),end=im.native(0x803e8))
terrain_passes=[]
world_cameras=[]
active_terrain=[None]
def terrain_begin(cpu,address,size,unused):
 if not entered[0]:return
 world_cameras.append(list(struct.unpack('<3i',b''.join(cpu.mem_read(im.native(0x70aa4+at),4)for at in (0x491e1,0x491e7,0x491ed)))))
 record={'frame':frames[0],'height':struct.unpack('<i',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+4,4))[0],'cells':[]}
 terrain_passes.append(record);active_terrain[0]=record
im.cpu.hook_add(UC_HOOK_CODE,terrain_begin,begin=im.native(0xb0ba8),end=im.native(0xb0ba8))
def terrain_end(cpu,address,size,unused):active_terrain[0]=None
for address in (0xb0bd8,0xb0cb6):im.cpu.hook_add(UC_HOOK_CODE,terrain_end,begin=im.native(address),end=im.native(address))
def terrain_cell(cpu,address,size,unused):
 if active_terrain[0] is None:return
 handle=cpu.reg_read(r.UC_X86_REG_EAX)&65535
 table=im.read(0x21800,'<I')[0]
 instance=struct.unpack('<I',cpu.mem_read(table+(handle-1)*4,4))[0]
 definition=struct.unpack('<H',cpu.mem_read(instance,2))[0]&511
 name=string(im.read(0x1b890+definition*4,'<I')[0])
 position=[struct.unpack('<i',struct.pack('<I',cpu.reg_read(reg)&0xffffffff))[0] for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]
 active_terrain[0]['cells'].append([name,*position,(cpu.mem_read(instance+2,1)[0]>>5)&3])
im.cpu.hook_add(UC_HOOK_CODE,terrain_cell,begin=im.native(0xb4fd0),end=im.native(0xb4fd0))
projection=[159,99,319,199]
horizons=[]
def observe_projection(cpu,address,size,unused):
 projection[:]=struct.unpack('<4i',cpu.mem_read(cpu.reg_read(r.UC_X86_REG_ESP)+4,16))
im.cpu.hook_add(UC_HOOK_CODE,observe_projection,begin=im.native(0xb94da),end=im.native(0xb94da))
def observe_horizon(cpu,address,size,unused):
 position=struct.unpack('<3i',b''.join(cpu.mem_read(im.native(0x70aa4+at),4) for at in (0x491e1,0x491e7,0x491ed)))
 horizons.append({
  'camera':position, # Diagnostic installed-cache value; ejection paints its horizon before installing the new camera.
  'horizon':[cpu.reg_read(r.UC_X86_REG_EAX)&65535,cpu.reg_read(r.UC_X86_REG_EDX)&65535,struct.unpack('<h',cpu.mem_read(im.native(0x70aa4+0x47c08),2))[0],im.read(0xad7c,'<h')[0],projection[1],projection[3]],
 })
im.cpu.hook_add(UC_HOOK_CODE,observe_horizon,begin=im.native(0xcaf84),end=im.native(0xcaf84))
def capture_frame(cpu,address,size,unused):
 if entered[0]:
  frame=bytes(video.pixels())
  (args.output/f'frame-{frames[0]}.indices').write_bytes(frame)
im.cpu.hook_add(UC_HOOK_CODE,capture_frame,begin=im.native(0x723bf),end=im.native(0x723bf))


# Execute the original startup components in their ordinary ownership order.
im.call(0xc86b4,limit=2000000)
im.call(0xc756c,limit=2000000)
im.call(0xc7588,limit=2000000)
try:
 # Dense missions can spend over 100 million original instructions in
 # launch/arming alone. This is an execution bound, not a game-clock input.
 im.call(0x72588,eax=2,edx=0x400200,limit=150000000+args.frames*2000000)
except RuntimeError:
 # A bounded capture deliberately stops at the next real frame boundary;
 # it does not pretend that launch_game returned through a mission result.
 bounded=len(snapshots)==args.frames+1 and im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x72045)
 completed=terminal and len(snapshots)==frames[0]+1 and im.cpu.reg_read(r.UC_X86_REG_EIP)==im.native(0x723d7)
 if not (bounded or completed):
  fault={'frame':frames[0],'snapshots':snapshots,'trace':[hex(f)for f in im.trace[-30:]],'registers':{name:im.cpu.reg_read(getattr(r,'UC_X86_REG_'+name))for name in ('EIP','ESP','EAX','EDX','EBX','ECX','ESI','EDI','EBP')},'loads':loads[-15:]}
  (args.output/'failure.json').write_text(json.dumps(fault,indent=2)+'\n')
  raise
else:raise RuntimeError('Original mission returned before completing the requested capture')
if args.until_result and terminal:
 # Continue the same original call and stack through recovery, FINISH and
 # teardown. This supplies no outcome or script variable, and skips no game
 # routine. Any additional external dependency must still be declared.
 (args.output/'result-boundary.json').write_text(json.dumps({'terminal':terminal,'snapshot':snapshots[-1]},indent=2)+'\n')
 im.cpu.emu_start(im.cpu.reg_read(r.UC_X86_REG_EIP),im.RETURN,count=20000000)
 if im.cpu.reg_read(r.UC_X86_REG_EIP)!=im.RETURN:raise RuntimeError('Original result/teardown did not return within its execution bound')
 terminal['returned']=True
 terminal['campaign']={variable['name']:im.read(0x1a400+index*4,'<i')[0]for index,variable in enumerate(program['variables'])if not variable['string_value']}
assert parser_base<=im.read(0x1acfc,'<I')[0]<parser_base+0x100000,'presentation arena exhausted'
recordings=[]
for index,(filename,contents)in enumerate(memory_files.files.items()):
 if not filename.endswith('.rec'):continue
 target=f'recording-{index}.rec';(args.output/target).write_bytes(contents)
 recordings.append({'name':filename,'file':target,'closed':not any(handle[0]==filename for handle in memory_files.handles.values())})
record={
 'reference':{'executable_sha256':hashlib.sha256((directory/'TFX.DAT').read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256((directory/'DID.DAT').read_bytes()).hexdigest()},
 'inputs':inputs.rows(frames[0]),
 'terminal':terminal,
 'recordings':recordings,
 'projectile_guidance':projectile_guidance,
 'processor_exceptions':im.processor_exceptions,
 'cockpit_displays':cockpit_displays,
 'preflight_projection':preflight_projection,
 'trail_events':trail_events,'hud_alert_events':hud_alert_events,'resource_root':'TFX','mission':args.mission,'presentation_numbers':presentation_numbers,'flight_model':args.flight_model,'ticks_per_frame':args.ticks_per_frame,'snapshots':snapshots,'horizons':horizons,'world_cameras':world_cameras,'terrain_passes':terrain_passes,
 'radio_events':radio_events,'grid':string(im.data+0x11974).lower()[:8],'environment':string(im.data+0x11960).lower(),
 'dependencies':{hex(address):reason for address,reason in im.dependencies.items()},
 'host_services':['DPMI exception-vector transport','VGA planar memory and ports','capture-owned in-memory DOS files','fixed startup calendar','zeroed DOS low page for unused cleared-shot owner','inherited presentation declarations'],
}
(args.output/'session.json').write_text(json.dumps(record,indent=2)+'\n')
print(f'Captured original mission {args.mission}: {frames[0]} complete frames, {len(loads)} resource requests; {args.output}')
if args.until_result and not terminal:raise RuntimeError('Original mission did not reach a result within the requested frame bound; bounded capture retained')
