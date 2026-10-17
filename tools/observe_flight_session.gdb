# Read-only observation of the actual headless game, called from a private cwd.
set pagination off
set confirm off
set startup-with-shell off
set print thread-events off
python
import json
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
