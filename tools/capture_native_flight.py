#!/usr/bin/env python3
"""Capture a bounded complete original TFX 2.05 launch and neutral flight.

Executes real renderer/EMM/configuration/environment/mission/arming/AI/flight
initialization and the original frame loop. The host supplies silent DOS I/O,
private memory, keyboard/mouse transport, fixed timer samples and planar VGA.
Inherited presentation variables are explicit inputs from the independent
research parser. No game instruction or original installation is modified.
Requires Unicorn and the independent did-unpack module in the research tree.
"""
from pathlib import Path
import argparse,struct,sys,json
from native_reference import NativeReference,r
from native_vga import VgaCapture
from unicorn import UC_HOOK_CODE,UC_HOOK_INSN,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ

class SessionReference(NativeReference):
 def _interrupt(self,cpu,interrupt,unused):
  operation=cpu.reg_read(r.UC_X86_REG_EAX)&65535
  if interrupt==0x31 and operation in (0x202,0x203):
   if operation==0x202:
    cpu.reg_write(r.UC_X86_REG_ECX,0);cpu.reg_write(r.UC_X86_REG_EDX,0)
   cpu.reg_write(r.UC_X86_REG_EFLAGS,cpu.reg_read(r.UC_X86_REG_EFLAGS)&~1)
   return
  super()._interrupt(cpu,interrupt,unused)

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
args=parser.parse_args()
if not 1 <= args.frames <= 256:parser.error('--frames must be between 1 and 256')
root=args.research.resolve();directory=root/'installs/cd_1994_09/TFX'
args.output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'did-unpack'))
from did_unpack import Archive
im=SessionReference(directory/'TFX.DAT',data_base=0x100000);video=SessionVideo(im,aperture=0xa0000)
im.cpu.mem_map(0x400000,0x4000000);heap=[0x410000]
archive=Archive.read(directory/'DID.DAT');entries={x.identifier:x for x in archive.entries};loads=[]
def string(address):
 if not address:return '<null>'
 return bytes(im.cpu.mem_read(address,256)).split(bytes(1))[0].decode('cp437')
def read(name):
 name=name.replace('\\','/').lstrip('/').lower()
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
im.intercept(0xc71b4,'Supply an empty resource root.',lambda current:(current.cpu.mem_write(current.cpu.reg_read(r.UC_X86_REG_EAX),bytes(1)),current.return_from()))
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
 mouse_polls[0]+=1;mouse_buttons[0]=0 if entered[0] else int(mouse_polls[0]%32 in range(8,16))
 for offset,value in ((4,197 if defaults_applied[0] else 101),(8,199),(12,mouse_buttons[0])):
  pointer=struct.unpack('<I',current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))[0];current.cpu.mem_write(pointer,struct.pack('<H',value))
 current.return_from()
im.intercept(0xc72ff,'Supply explicit pointer input on the authored DEFAULT then DONE buttons.',mouse)
def held_mouse(current):
 if mouse_polls[0]>128 and not entered[0]:raise RuntimeError('Unconsumed mouse script after 128 polls')
 mouse_polls[0]+=1;mouse_buttons[0]=0 if entered[0] else int(mouse_polls[0]%32 in range(8,16));current.cpu.reg_write(r.UC_X86_REG_EAX,mouse_buttons[0]);current.return_from()
im.intercept(0xc733e,'Supply an explicit button press/release sequence while the original modal controller polls.',held_mouse)
def relative_mouse(current):
 for offset in (4,8):
  pointer=struct.unpack('<I',current.cpu.mem_read(current.cpu.reg_read(r.UC_X86_REG_ESP)+offset,4))[0];current.cpu.mem_write(pointer,bytes(2))
 current.return_from()
im.intercept(0xc7326,'Supply zero relative virtual-mouse movement.',relative_mouse)
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

def frame_boundary(current):
 snapshots.append({
  'frame':frames[0],
  'position':[current.read(at,'<i')[0] for at in (0x13424,0x13430,0x1343c)],
  'angles':current.read(0x86c8,'<3H'),
  'speed':current.read(0x13444,'<i')[0],
  'elapsed':current.read(0x13476,'<H')[0],
  'cockpit_offset':[current.read(at,'<h')[0] for at in (0x10be8,0x10be6)],
  'view':current.read(0x87b8,'<h')[0],
  'cockpit_callback':hex(current.read(0xe70c,'<I')[0]+0x70aa4-0x10000),
  'environment_flags':current.read(0xe774,'<H')[0],
  'arena_free':current.read(0xad14,'<I')[0],
  'aiming_flags':[current.read(at,'<B')[0] for at in (0x7140,0x7148)],
  'selected':current.read(0x93b0,'<h')[0],
  'stores':[current.read(0x13374+i*2,'<2B') for i in range(11)],
  'ground_phase':current.read(0xad7c,'<i')[0],
  'pattern_seed':struct.unpack('<H',current.cpu.mem_read(current.native(0xe3a3f),2))[0],
  'timer':clock[0],
  'random':struct.unpack('<2H',current.cpu.mem_read(current.native(0xc9894),4)),
  'actors':actors_snapshot(current),
 })
 if frames[0]==args.frames:
  current.cpu.emu_stop();return
 frames[0]+=1;clock[0]+=4
im.intercept(0x72045,'Supply one four-tick external interval at each original frame boundary and stop after the requested complete frames.',frame_boundary)
radio_events=[]
def observe_radio(cpu,address,size,unused):
 radio_events.append({'frame':frames[0],'message':string(cpu.reg_read(r.UC_X86_REG_EAX)),'persistent':address==im.native(0x81254)})
for file in (0x81198,0x81254):im.cpu.hook_add(UC_HOOK_CODE,observe_radio,begin=im.native(file),end=im.native(file))
terrain_passes=[]
active_terrain=[None]
def terrain_begin(cpu,address,size,unused):
 if not entered[0]:return
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
  'camera':position,
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
 im.call(0x72588,eax=2,edx=0x400200,limit=100000000+args.frames*2000000)
except RuntimeError:
 # A bounded capture deliberately stops at the next real frame boundary;
 # it does not pretend that launch_game returned through a mission result.
 if len(snapshots)!=args.frames+1 or im.cpu.reg_read(r.UC_X86_REG_EIP)!=im.native(0x72045):raise
else:raise RuntimeError('Original mission returned before completing the requested capture')
assert parser_base<=im.read(0x1acfc,'<I')[0]<parser_base+0x100000,'presentation arena exhausted'
record={
 'mission':args.mission,'presentation_numbers':presentation_numbers,'flight_model':args.flight_model,'ticks_per_frame':4,'snapshots':snapshots,'horizons':horizons,'terrain_passes':terrain_passes,
 'radio_events':radio_events,'grid':string(im.data+0x11974).lower()[:8],'environment':string(im.data+0x11960).lower(),
 'dependencies':{hex(address):reason for address,reason in im.dependencies.items()},
 'host_services':['DPMI exception-vector transport','VGA planar memory and ports','fixed startup calendar','inherited presentation declarations'],
}
(args.output/'session.json').write_text(json.dumps(record,indent=2)+'\n')
print(f'Captured original mission {args.mission}: {args.frames} complete frames, {len(loads)} resource requests; {args.output}')
