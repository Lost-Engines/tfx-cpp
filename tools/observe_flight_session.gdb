# Read-only observation of the actual headless game, called from a private cwd.
set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
python
import hashlib
import json
from pathlib import Path
renderer_pointer=None
rendered_frames=0
flight_frame=0
import os
import sys
virtual_devices=None
if 'TFX_FLIGHT_INPUTS' in os.environ:
 sys.path.insert(0,os.environ['TFX_TOOLS_DIRECTORY'])
 from virtual_flight_inputs import install
 virtual_devices=install(lambda:flight_frame)
def current_renderer():
 global renderer_pointer
 if renderer_pointer is None:
  frame=gdb.newest_frame()
  while frame:
   try:
    value=frame.read_var('renderer')
    if value.type.code in (gdb.TYPE_CODE_REF,gdb.TYPE_CODE_RVALUE_REF):value=value.referenced_value()
    renderer_pointer=value.address
    break
   except (ValueError,gdb.error):frame=frame.older()
  if renderer_pointer is None:raise RuntimeError('No actual flight renderer in observed call stack')
 return renderer_pointer.dereference()
end
set $player = 0
set $air = 0
set $seeker = 0
set $radar = 0
set $projectiles = 0
set $armament = 0
set $scene = 0
break tfx::world::scene::draw
commands
silent
set $scene = this
continue
end
break tfx::weapons::runtime::advance
commands
silent
set $projectiles = this
continue
end
break tfx::weapons::armament::select
commands
silent
set $armament = this
continue
end
break tfx::sensors::advance_air_lock
commands
silent
set $radar = &radar
set $seeker = &state
continue
end
break tfx::actors::air_runtime::advance
commands
silent
set $air = this
continue
end
break tfx::flight::player_flight::advance
commands
silent
set $player = this
python
flight_frame+=1
if virtual_devices:virtual_devices['input_pending']=False
end
printf "CPP_PRE %d %d %d %u %u %u %d\n", this->basic.flight.integer_position.x, this->basic.flight.integer_position.y, this->basic.flight.integer_position.z, this->basic.flight.angles.x, this->basic.flight.angles.y, this->basic.flight.angles.z, this->basic.flight.fixed_speed
continue
end
break tfx::missions::progress::finish_frame
commands
silent
printf "CPP_POST %d %d %d %u %u %u %d\n", $player->basic.flight.integer_position.x, $player->basic.flight.integer_position.y, $player->basic.flight.integer_position.z, $player->basic.flight.angles.x, $player->basic.flight.angles.y, $player->basic.flight.angles.z, $player->basic.flight.fixed_speed
python
import json
air=gdb.parse_and_eval('$air').dereference()
actors=[]
for index in range(100):
 slot=air['actors']['_M_elems'][index]
 if not bool(slot['_M_payload']['_M_engaged']):continue
 actor=slot['_M_payload']['_M_payload']['_M_value']
 flight=actor['flight'];pose=flight['pose']
 values=[index]
 for field in ('position','angles'):
  for axis in ('x','y','z'):values.append(int(pose[field][axis]))
 values.append(int(pose['speed']))
 for axis in ('x','y','z'):values.append(int(flight['angular_rate'][axis]))
 values.extend(int(x) for x in (flight['acceleration'],flight['input_ticks'],actor['wait_seconds'],actor['actions'],pose['flags'],pose['leader'],pose['formation'],actor['scan_cursor'],actor['player_shots']))
 actors.append(values)
print('CPP_WORLD '+json.dumps({'random':[int(air['random']['low']),int(air['random']['high'])],'actors':actors}))
player=gdb.parse_and_eval('$player').dereference()
body=player['physical']['view']['orientation']
print('CPP_BODY '+json.dumps([int(body[axis][component]) for component in ('x','y','z') for axis in ('right','down','forward')]))
radar=gdb.parse_and_eval('$radar').dereference()
seeker=gdb.parse_and_eval('$seeker').dereference()
def identity(value):
 return int(value['_M_payload']['_M_payload']['_M_value']) if bool(value['_M_payload']['_M_engaged']) else -1
values=[int(radar['cursor']),identity(radar['selected']),*[identity(radar['slots']['_M_elems'][i]) for i in range(20)],int(radar['hostile_nearby']),int(radar['nearby_hostile_count']),identity(seeker['guidance']),identity(seeker['tracking'])]
values += [int(seeker[name][axis]) for name in ('reticle','projected') for axis in ('x','y')]
values += [int(seeker[name]) for name in ('lock_ticks','acquisition_ticks','too_close')]
print('CPP_SENSORS '+json.dumps(values))

import struct
armament=gdb.parse_and_eval('$armament').dereference()
values=[int(armament[name]) for name in ('selected','guns','last_released','cannon_role')]
values += [int(armament['pylons']['_M_elems'][i][name])for i in range(11)for name in ('weapon','count')]
values += [struct.unpack('<Q',struct.pack('<d',float(player['physical']['powerplant']['fuel'])))[0]]
print('CPP_ARMAMENT '+json.dumps(values))
projectiles=gdb.parse_and_eval('$projectiles').dereference()
printer=gdb.default_visualizer(projectiles['active'])
if printer is None:raise RuntimeError('GNU std::map printer required for read-only projectile observation')
children=list(printer.children());bodies=[]
for i in range(0,len(children),2):
 shot=children[i+1][1].dereference();body=shot['state']
 values=[int(shot['id']),int(body['weapon']),int(body['next_stage']),int(body['motion']),int(body['ticks'])]
 values += [int(body[name][axis])for name in ('position','previous','angles')for axis in ('x','y','z')]
 values += [int(body[name])for name in ('speed','fall_speed','acceleration','range')]
 values += [int(shot[name])for name in ('spent','mount')]
 bodies.append(values)
print('CPP_PROJECTILES '+json.dumps(bodies))
scene=gdb.parse_and_eval('$scene').dereference()
printer=gdb.default_visualizer(scene['warnings'])
if printer is None:raise RuntimeError('GNU std::set printer required for renderer diagnostics')
notes=[value['_M_dataplus']['_M_p'].string()for _,value in printer.children()]
if notes:print('CPP_WARNINGS '+json.dumps(notes))

renderer=current_renderer()
image=renderer['output']['pixels']['_M_elems']
raw=bytes(gdb.selected_inferior().read_memory(int(image.address),64000))
rendered_frames+=1
Path(f'cpp-frame-{rendered_frames}.indices').write_bytes(raw)
print('CPP_RENDER '+json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'pattern_seed':int(renderer['procedural_seed'])}))
end
continue
end
python
class AnimationReturn(gdb.FinishBreakpoint):
 def __init__(self):
  super().__init__(internal=True)
  self.owner=gdb.parse_and_eval('this')
 def stop(self):
  scene=self.owner.dereference()
  value=int(scene['clock']['accumulated'])
  print('CPP_ANIMATION '+json.dumps([int(scene['animation_pending']),(value+32768)%65536-32768]))
  return False
class AnimationAdvance(gdb.Breakpoint):
 def stop(self):
  AnimationReturn()
  return False
AnimationAdvance('tfx::world::scene::advance',internal=True)
end
break tfx::sensors::air_lock::begin_mission
commands
silent
set $seeker = this
python
origin=gdb.parse_and_eval('projection_origin')
print('CPP_PREFLIGHT '+json.dumps([int(origin[axis]) for axis in ('x','y')]))
end
continue
end
break tfx::cockpit::radio_ticker::show
commands
silent
python
message=gdb.parse_and_eval('message')
raw=bytes(gdb.selected_inferior().read_memory(int(message['_M_str']),int(message['_M_len'])))
print('CPP_RADIO '+json.dumps({'frame':flight_frame+int(bool(virtual_devices and virtual_devices['input_pending'])),'message':raw.decode('latin1'),'persistent':bool(gdb.parse_and_eval('repeat'))}))
end
continue
end
break tfx::render::framebuffer::screenshot
commands
silent
dump binary memory cpp.indices this->pixels._M_elems this->pixels._M_elems+64000
continue
end
break tfx::render::original_camera
commands
silent
python
pose=gdb.parse_and_eval('position_q16')
camera_position=[int(pose[axis]) for axis in ('x','y','z')]
end
continue
end
break tfx::render::paint_horizon
commands
silent
python
context=gdb.parse_and_eval('context')
fields=['pitch','roll','camera_y','ground_phase','origin_y']
print('CPP_CAMERA_HORIZON '+json.dumps({'camera':camera_position,'horizon':[int(context[field]) for field in fields]+[int(context['maximum']['y'])]}))
end
continue
end
break tfx::world::trail_pool::spawn
commands
silent
python
point=gdb.parse_and_eval('position_q8')
print('CPP_TRAIL '+json.dumps([flight_frame,int(point['x']),int(point['y']),int(point['z'])]))
end
continue
end
run
