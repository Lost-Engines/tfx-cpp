"""GDB-only virtual GLFW input/timer boundary for complete flight comparisons.

Only external GLFW return values are supplied. No game routine, outcome,
position, weapon, random value or instruction is altered. Linux x86-64 ABI.
"""
import json
import os
import gdb
from flight_inputs import FlightInputs,KEYS


def install(current_frame):
 inputs=FlightInputs(json.loads(os.environ['TFX_FLIGHT_INPUTS']))
 timer_hz=1193182/21845
 started=False
 phase={'input_pending':False}
 class Keys(gdb.Breakpoint):
  def stop(self):
   key=int(gdb.parse_and_eval('$rsi'))
   held={KEYS[name][1]for name in inputs.at(current_frame()+1)['held']}
   gdb.execute('return (int) '+str(int(key in held)),to_string=True)
   return False
 class Timer(gdb.Breakpoint):
  def stop(self):
   nonlocal started
   # A tiny increasing fraction avoids host double rounding losing a tick;
   # it never accumulates to a whole tick within the bounded capture.
   phase['input_pending']=started
   value=(current_frame()+1)*4.000001/timer_hz if started else 0
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
   gdb.execute('return (int) 0',to_string=True)
   return False
 Keys('glfwGetKey',internal=True)
 Timer('glfwGetTime',internal=True)
 Focus('glfwGetWindowAttrib',internal=True)
 Mouse('glfwGetMouseButton',internal=True)
 print('Virtual GLFW boundary: declared keyboard frames, neutral mouse, focused private window, four-tick timer')

 return phase
