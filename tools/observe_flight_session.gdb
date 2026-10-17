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
renderer=current_renderer()
image=renderer['output']['pixels']['_M_elems']
raw=bytes(gdb.selected_inferior().read_memory(int(image.address),64000))
rendered_frames+=1
Path(f'cpp-frame-{rendered_frames}.indices').write_bytes(raw)
print('CPP_RENDER '+json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'pattern_seed':int(renderer['procedural_seed'])}))
end
continue
end
break tfx::cockpit::radio_ticker::show
commands
silent
python
message=gdb.parse_and_eval('message')
raw=bytes(gdb.selected_inferior().read_memory(int(message['_M_str']),int(message['_M_len'])))
print('CPP_RADIO '+json.dumps({'frame':rendered_frames+1,'message':raw.decode('latin1'),'persistent':bool(gdb.parse_and_eval('repeat'))}))
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
run
