"""GDB-only virtual GLFW input/timer boundary for complete flight comparisons.

Only external GLFW return values are supplied. No game routine, outcome,
position, weapon, random value or instruction is altered. Linux x86-64 ABI.
"""
import json
import os
import struct
import gdb
from flight_inputs import FlightInputs,KEYS


def install(current_frame):
 inputs=FlightInputs(json.loads(os.environ['TFX_FLIGHT_INPUTS']))
 timer_hz=1193182/21845
 ticks_per_frame=int(os.environ.get('TFX_TICKS_PER_FRAME','4'))
 started=False
 phase={'input_pending':False,'in_frame':False}
 arming=None
 ui_ticks=0
 cursor=[0,0]
 cursor_frame=None
 class Keys(gdb.Breakpoint):
  def stop(self):
   key=int(gdb.parse_and_eval('$rsi'))
   held=set() if arming is not None else {KEYS[name][1]for name in inputs.at(current_frame()+1)['held']}
   gdb.execute('return (int) '+str(int(key in held)),to_string=True)
   return False
 class Timer(gdb.Breakpoint):
  def stop(self):
   nonlocal started,ui_ticks
   # A tiny increasing fraction avoids host double rounding losing a tick;
   # it never accumulates to a whole tick within the bounded capture.
   phase['input_pending']=started and not phase['in_frame']
   if arming is not None:
    ui_ticks+=4;arming['polls']+=1
   # Modal polls advance wall time within the current simulation frame.
   # Returning from them must leave the next flight sample one interval ahead.
   frame=current_frame()+int(not phase['in_frame'])
   value=(frame*(ticks_per_frame+.000001)+ui_ticks)/timer_hz if started else 0
   started=True
   gdb.execute('return (double) '+format(value,'.17g'),to_string=True)
   return False
 class Focus(gdb.Breakpoint):
  def stop(self):
   if int(gdb.parse_and_eval('$rsi'))==0x20001:
    gdb.execute('return (int) 1',to_string=True)
   return False
 class Mouse(gdb.Breakpoint):
  def stop(self):
   button=int(gdb.parse_and_eval('$rsi'))
   mask=int(arming['polls']%32 in range(8,16)) if arming is not None else inputs.at(current_frame()+1).get('buttons',0)
   gdb.execute('return (int) '+str(int(button in (0,1) and bool(mask&(1<<button)))),to_string=True)
   return False
 class Cursor(gdb.Breakpoint):
  def stop(self):
   nonlocal cursor_frame
   frame=current_frame()+1
   if arming is not None:
    # The comparison owns a scale-2, 640x480 private window. These are the
    # same logical DEFAULT/DONE positions supplied to the DOS mouse boundary.
    position=[(197 if arming['default'] else 101)*2,199*2.4]
   else:
    position=cursor
   if arming is None and phase['input_pending'] and cursor_frame!=frame:
    for axis,value in enumerate(inputs.at(frame).get('mouse',[0,0])):cursor[axis]+=value
    cursor_frame=frame
   inferior=gdb.selected_inferior()
   for register,value in zip(('$rsi','$rdx'),position):
    address=int(gdb.parse_and_eval(register))
    if address:inferior.write_memory(address,struct.pack('<d',value))
   gdb.execute('return',to_string=True)
   return False
 if 'TFX_DEFAULT_REARMING' in os.environ:
  class ArmingReturn(gdb.FinishBreakpoint):
   def stop(self):
    nonlocal arming
    assert arming['default'],'declared DEFAULT input never reached the arming controller'
    arming=None
    phase['input_pending']=False
    print('CPP_DEFAULT_REARMING_COMPLETE')
    return False
  class ArmingEntry(gdb.Breakpoint):
   def stop(self):
    nonlocal arming
    assert arming is None,'nested arming dialog'
    arming={'polls':0,'default':False}
    ArmingReturn(internal=True)
    return False
  class DefaultFit(gdb.Breakpoint):
   def stop(self):
    if arming is not None:arming['default']=True
    return False
  ArmingEntry('tfx::platform::arm_mission',internal=True)
  DefaultFit('tfx::weapons::armament::fit_default',internal=True)
 Keys('glfwGetKey',internal=True)
 Timer('glfwGetTime',internal=True)
 Focus('glfwGetWindowAttrib',internal=True)
 Mouse('glfwGetMouseButton',internal=True)
 Cursor('glfwGetCursorPos',internal=True)
 print(f'Virtual GLFW boundary: declared keyboard/mouse frames, focused private window, {ticks_per_frame}-tick timer')

 return phase
