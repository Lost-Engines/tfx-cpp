# Read-only observation of the actual headless game, called from a private cwd.
set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
python
import hashlib
import json
import struct
from pathlib import Path
renderer_pointer=None
player_model_pointer=None
player_model_key=None
rendered_frames=0
flight_frame=0
import os
import sys
virtual_devices=None
if 'TFX_FLIGHT_INPUTS' in os.environ:
 sys.path.insert(0,os.environ['TFX_TOOLS_DIRECTORY'])
 from virtual_flight_inputs import install
 virtual_devices=install(lambda:flight_frame)
class RadarInput(gdb.Breakpoint):
 def stop(self):
  if int(gdb.parse_and_eval('mode'))!=0:return False
  state=gdb.parse_and_eval('state')
  span=state['projectiles'];count=int(span['_M_extent']['_M_extent_value']);begin=span['_M_ptr']
  shots=[{'weapon':int(begin[i]['weapon']),'position':[int(begin[i]['position_q8'][axis])for axis in ('x','y','z')],'player_owned':bool(begin[i]['player_owned'])}for i in range(count)]
  print('CPP_RADAR_INPUT '+json.dumps({'frame':flight_frame,'pulse_before':bool(gdb.parse_and_eval('this').dereference()['pulse']),'player':[int(state['player'][axis])for axis in ('x','y','z')],'heading':int(state['heading']),'range':int(gdb.parse_and_eval('range')),'offset':[int(state['offset'][axis])for axis in ('x','y')],'projectiles':shots}))
  return False
if 'TFX_OBSERVE_RADAR_CONTEXT' in os.environ:RadarInput('tfx::cockpit::radar::draw',internal=True)
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
class InitialReturn(gdb.FinishBreakpoint):
 def __init__(self):
  super().__init__(internal=True)
  pointer=gdb.parse_and_eval('this')
  # Materialise the address now: a lazy register-backed value can lose its
  # location when initialise returns, especially in the sanitizer build.
  self.player=gdb.Value(int(pointer)).cast(pointer.type)
 def stop(self):
  player=self.player.dereference()
  bits=lambda value:struct.unpack('<Q',struct.pack('<d',float(value)))[0]
  print('CPP_INITIAL '+json.dumps({'fuel':bits(player['physical']['powerplant']['fuel']),'mass':bits(player['physical']['data']['mass_kg']),'capacity':bits(player['physical']['stores']['fuel_capacity'])}))
  return False
end
break tfx::flight::player_flight::initialise
commands
silent
python InitialReturn()
continue
end
set $navigation_flag = 0
set $cheat = 0
break tfx::platform::fly_mission
commands
silent
set $navigation_flag = &options.cannon_navigation
set $cheat = &options.cheat
continue
end
set $player = 0
set $air = 0
set $seeker = 0
set $radar = 0
set $projectiles = 0
set $armament = 0
set $scene = 0
set $aiming = 0
set $progress = 0
set $cannon = 0
set $hud = 0
set $player_model_handle = -1
break tfx::cockpit::hud::hud
commands
silent
set $hud = this
continue
end
break tfx::weapons::fire_cannon
commands
silent
set $cannon = &state
continue
end
break tfx::missions::progress::begin_frame
commands
silent
set $progress = this
continue
end
break tfx::cockpit::weapon_display::reset_tracking
commands
silent
set $aiming = this
continue
end
break tfx::world::scene::set_player_rendering
commands
silent
set $player_model_handle = handle.value
continue
end
break tfx::world::scene::draw
commands
silent
set $scene = this
python
# This observer launches a direct mission: its first scene draw targets the
# actual flight framebuffer, before any MFD viewport. Capture the borrowed
# renderer argument while it is live instead of depending on an optimised
# caller-local name at the eventual frame-return breakpoint.
if renderer_pointer is None:
 value=gdb.parse_and_eval('renderer')
 if value.type.code in (gdb.TYPE_CODE_REF,gdb.TYPE_CODE_RVALUE_REF):value=value.referenced_value()
 renderer_pointer=value.address
end
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
python
class FrameReturn(gdb.FinishBreakpoint):
 def __init__(self):
  super().__init__(internal=True)
 def stop(self):
  global rendered_frames,player_model_pointer,player_model_key
  gdb.execute('printf "CPP_POST %d %d %d %u %u %u %d\\n", $player->basic.flight.integer_position.x, $player->basic.flight.integer_position.y, $player->basic.flight.integer_position.z, $player->basic.flight.angles.x, $player->basic.flight.angles.y, $player->basic.flight.angles.z, $player->basic.flight.fixed_speed')
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
  progress=gdb.parse_and_eval('$progress').dereference()
  values={field:int(progress[field])for field in ('target_cursor','violations','exit_ticks','remaining_timer')}
  values.update({field:bool(progress[field])for field in ('resolved','ended','critical_loss')})
  values['credited_targets']=int(progress['results']['credited_targets'])
  values['results']=[int(progress['results'][field])for field in ('personal_air_score','enemy_air_score','friendly_air_score','enemy_aircraft_down','friendly_aircraft_down','completed','targets_destroyed','enemy_mobile_down','credited_air_kills','credited_ground_kills')]
  print('CPP_MISSION_PROGRESS '+json.dumps(values))
  cannon=gdb.parse_and_eval('$cannon').dereference()
  print('CPP_CANNON '+json.dumps([int(cannon['ammunition']),int(cannon['barrel'])]))
  print('CPP_RADAR_PULSE '+json.dumps(bool(gdb.parse_and_eval('$hud').dereference()['radar_display']['pulse'])))
  player=gdb.parse_and_eval('$player').dereference()
  body=player['physical']['view']['orientation']
  print('CPP_LAUNCH_NOTICE '+json.dumps(int(gdb.parse_and_eval('$aiming').dereference()['tracking']['launch_frames'])))
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
  physical=player['physical']
  print('CPP_SPEED_FACTOR '+json.dumps(struct.unpack('<I',struct.pack('<f',float(player['basic']['flight']['speed_mach'])))[0]))
  gains=physical['input_gains']
  print('CPP_CONTROL_CONFIGURATION '+json.dumps([int(physical['autopilot']['recovery']['configuration']),*[struct.unpack('<Q',struct.pack('<d',float(gains[field])))[0]for field in ('joystick','pitch','roll','rudder')]]))
  armament=gdb.parse_and_eval('$armament').dereference()
  values=[int(armament[name]) for name in ('selected','guns','last_released','cannon_role')]
  values += [int(armament['pylons']['_M_elems'][i][name])for i in range(11)for name in ('weapon','count')]
  values += [struct.unpack('<Q',struct.pack('<d',float(player['physical']['powerplant']['fuel'])))[0]]
  print('CPP_ARMAMENT '+json.dumps(values))
  print('CPP_AIMING_FLAGS '+json.dumps([int(not bool(armament['guns'])),int(gdb.parse_and_eval('$navigation_flag').dereference())]))
  cheat=gdb.parse_and_eval('$cheat').dereference()['state']
  print('CPP_CHEAT_STATE '+json.dumps([int(cheat['enabled']),int(cheat['matched'])]))
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
  handle=int(gdb.parse_and_eval('$player_model_handle'))
  key=(int(scene.address),handle)
  if key!=player_model_key:
   children=list(gdb.default_visualizer(scene['actors']).children())
   player_model_pointer=next(children[i+1][1].address for i in range(0,len(children),2)if int(children[i][1])==handle)
   player_model_key=key
  model=player_model_pointer.dereference()
  parts=model['state']['parts'];begin=parts['_M_impl']['_M_start'];end=parts['_M_impl']['_M_finish']
  print('CPP_PLAYER_MODELS '+json.dumps([int(begin[i]['model_index'])for i in range(int(end-begin))]))
  print('CPP_PLAYER_PARTS '+json.dumps([[int(begin[i]['parameters']['_M_elems'][p])for p in range(8)]for i in range(int(end-begin))]))
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
  return False
end
break tfx::weapons::runtime::finish_frame
commands
silent
python
FrameReturn()
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
break *'tfx::cockpit::radio_ticker::show(std::basic_string_view<char, std::char_traits<char> >, bool)'
commands
silent
python
message=gdb.parse_and_eval('message')
try:
 address=int(message['_M_str']);length=int(message['_M_len'])
except gdb.error:
 # GCC's sanitizer debug information can omit this mutated parameter.
 # At the exact function entry, GNU x86-64 passes string_view's length
 # and pointer in RSI/RDX. Read them without changing the inferior.
 if gdb.newest_frame().architecture().name()!='i386:x86-64':raise
 length=int(gdb.parse_and_eval('$rsi'));address=int(gdb.parse_and_eval('$rdx'))
raw=bytes(gdb.selected_inferior().read_memory(address,length))
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
