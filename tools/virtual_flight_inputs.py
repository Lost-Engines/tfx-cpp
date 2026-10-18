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
 configuration=None
 modal_resuming=False
 ui_ticks=0
 cursor=[0,0]
 cursor_frame=None
 class Keys(gdb.Breakpoint):
  def stop(self):
   key=int(gdb.parse_and_eval('$rsi'))
   held=set() if arming is not None or configuration is not None else {KEYS[name][1]for name in inputs.at(current_frame()+1)['held']}
   gdb.execute('return (int) '+str(int(key in held)),to_string=True)
   return False
 class Timer(gdb.Breakpoint):
  def stop(self):
   nonlocal started,ui_ticks,modal_resuming
   # A tiny increasing fraction avoids host double rounding losing a tick;
   # it never accumulates to a whole tick within the bounded capture.
   phase['input_pending']=started and not phase['in_frame']
   if arming is not None:
    ui_ticks+=4
    if arming['ready']:arming['polls']+=1
   # Modal polls advance wall time within the current simulation frame.
   # Returning from them must leave the next flight sample one interval ahead.
   frame=current_frame()+int(not phase['in_frame'])
   value=(frame*(ticks_per_frame+.000001)+ui_ticks)/timer_hz if started else 0
   if modal_resuming:
    # The first read resets the host loop's wall-clock baseline after the
    # modal return. Its next poll supplies a fresh ordinary flight interval.
    ui_ticks+=ticks_per_frame;modal_resuming=False
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
   if configuration is not None:mask=int(configuration['polls']%32 in range(8,16))
   elif arming is not None:
    step=min((max(1,arming['polls'])-1)//32,len(arming['clicks'])-1)
    buttons=arming['clicks'][step][2]if arming['clicks']else 1
    period=31 if arming['clicks']and arming['polls']>32*(len(arming['clicks'])-1)else 32
    mask=buttons*int(arming['ready']and arming['polls']%period in range(8,16))
   else:mask=inputs.at(current_frame()+1).get('buttons',0)
   gdb.execute('return (int) '+str(int(button in (0,1) and bool(mask&(1<<button)))),to_string=True)
   return False
 class Cursor(gdb.Breakpoint):
  def stop(self):
   nonlocal cursor_frame
   frame=current_frame()+1
   if configuration is not None:
    step=(max(1,configuration['polls'])-1)//32
    assert step<len(configuration['clicks']),'C++ configuration exhausted its declared mouse input'
    x,y=configuration['clicks'][step];position=[x*2,y*2]
   elif arming is not None:
    # The comparison owns a scale-2, 640x400 private window. These are the
    # same logical DEFAULT/DONE positions supplied to the DOS mouse boundary.
    if arming['clicks']:
     step=min((max(1,arming['polls'])-1)//32,len(arming['clicks'])-1)
     assert arming['polls']<=32*(len(arming['clicks'])+4),'C++ arming exhausted its pointer actions'
     position=[value*2 for value in arming['clicks'][step][:2]]
    else:position=[(197 if arming['default'] else 101)*2,199*2]
   else:
    position=cursor
   if arming is None and configuration is None and phase['input_pending'] and cursor_frame!=frame:
    for axis,value in enumerate(inputs.at(frame).get('mouse',[0,0])):cursor[axis]+=value
    cursor_frame=frame
   inferior=gdb.selected_inferior()
   for register,value in zip(('$rsi','$rdx'),position):
    address=int(gdb.parse_and_eval(register))
    if address:inferior.write_memory(address,struct.pack('<d',value))
   gdb.execute('return',to_string=True)
   return False
 if any('configuration'in row for row in inputs.rows(65535)):
  class ConfigurationReturn(gdb.FinishBreakpoint):
   def stop(self):
    nonlocal configuration,modal_resuming
    assert configuration['polls']>=32*(len(configuration['clicks'])-1)+8,'C++ configuration returned before its final declared click'
    print('CPP_CONFIGURATION_EVENT '+json.dumps({'frame':current_frame()+1,'clicks':configuration['clicks']}))
    configuration=None
    modal_resuming=True
    return False
  class ConfigurationEntry(gdb.Breakpoint):
   def stop(self):
    nonlocal configuration
    assert configuration is None,'nested C++ configuration screen'
    clicks=inputs.at(current_frame()+1).get('configuration',[])
    assert clicks,'configuration entry needs declared modal pointer input'
    configuration={'polls':0,'clicks':clicks}
    ConfigurationReturn(internal=True)
    return False
  class ConfigurationPoll(gdb.Breakpoint):
   def stop(self):
    if configuration is not None:
     configuration['polls']+=1
     assert configuration['polls']<=32*len(configuration['clicks']),'unconsumed configuration input'
    return False
  ConfigurationEntry('tfx::platform::configure_flight',internal=True)
  ConfigurationPoll('glfwPollEvents',internal=True)
 if 'TFX_DEFAULT_REARMING' in os.environ or any('arming'in row for row in inputs.rows(65535)):
  class ArmingReturn(gdb.FinishBreakpoint):
   def stop(self):
    nonlocal arming,modal_resuming
    if arming['clicks']:
     modal_resuming=True
     assert arming['polls']>=32*(len(arming['clicks'])-1)+8,'C++ arming returned before its final declared click'
     print('CPP_ARMING_EVENT '+json.dumps({'frame':current_frame()+1,'clicks':arming['clicks']}))
    else:assert arming['default'],'declared DEFAULT input never reached the arming controller'
    arming=None
    phase['input_pending']=False
    print('CPP_DEFAULT_REARMING_COMPLETE')
    return False
  class ArmingEntry(gdb.Breakpoint):
   def stop(self):
    nonlocal arming
    assert arming is None,'nested arming dialog'
    clicks=inputs.at(current_frame()+1).get('arming',[])
    arming={'polls':0,'default':False,'clicks':clicks,'ready':not clicks}
    ArmingReturn(internal=True)
    return False
  class DefaultFit(gdb.Breakpoint):
   def stop(self):
    if arming is not None:arming['default']=True
    return False
  class ArmingReady(gdb.Breakpoint):
   def stop(self):
    # The native opening fade consumes no mouse polls. Match that boundary:
    # C++ presents its 40 fade frames before accepting any pointer action.
    if arming is not None and arming['clicks']:arming['ready']=True
    return False
  ArmingReady('tfx::presentation::arming_preview::start',internal=True)
  ArmingEntry('tfx::platform::arm_mission',internal=True)
  DefaultFit('tfx::weapons::armament::fit_default',internal=True)
 Keys('glfwGetKey',internal=True)
 Timer('glfwGetTime',internal=True)
 Focus('glfwGetWindowAttrib',internal=True)
 Mouse('glfwGetMouseButton',internal=True)
 Cursor('glfwGetCursorPos',internal=True)
 print(f'Virtual GLFW boundary: declared keyboard/mouse frames, focused private window, {ticks_per_frame}-tick timer')

 return phase
