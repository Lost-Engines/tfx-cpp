"""Declared mouse input for the original in-flight configuration screen.

Only DOS mouse returns and relative motion are supplied. The actual dialogs,
hit testing, option callbacks, preference saving and flight return execute.
"""
import struct
from unicorn import UC_HOOK_CODE
from native_dpmi import DpmiReference
from native_reference import r


class FlightReference(DpmiReference):
 def __init__(self,*args,**kwargs):
  self.configuration_mouse=None
  super().__init__(*args,**kwargs)
 def _interrupt(self,cpu,number,unused):
  if number==0x33 and self.configuration_mouse and self.configuration_mouse.active:
   self.configuration_mouse.interrupt(cpu)
  else:super()._interrupt(cpu,number,unused)


class ConfigurationMouse:
 def __init__(self,image,inputs,current_frame):
  self.image=image;self.inputs=inputs;self.current_frame=current_frame
  self.active=False;self.polls=0;self.clicks=[];self.events=[]
  image.configuration_mouse=self
  image.intercept(0x94c8c,'Observe configuration entry to supply declared pointer input through the unchanged original dialogs.',self.enter)
  image.intercept(0xce508,'Clear virtual DOS mouse press counters before configuration input begins.',lambda current:current.return_from())
 def enter(self,image):
  assert not self.active,'nested original configuration screen'
  self.clicks=self.inputs.at(self.current_frame()).get('configuration',[])
  assert self.clicks,'configuration entry needs declared modal pointer input'
  self.active=True;self.polls=0
  address=struct.unpack('<I',image.cpu.mem_read(image.cpu.reg_read(r.UC_X86_REG_ESP),4))[0]
  def leave(cpu,address,size,unused):
   assert self.polls>=32*(len(self.clicks)-1)+8,'original configuration returned before the declared final click'
   self.events.append({'frame':self.current_frame(),'clicks':self.clicks})
   self.active=False;cpu.hook_del(hook)
  hook=image.cpu.hook_add(UC_HOOK_CODE,leave,begin=address,end=address)
 @property
 def position(self):
  step=(max(1,self.polls)-1)//32
  assert step<len(self.clicks),'original configuration exhausted its declared mouse input'
  return self.clicks[step]
 @property
 def buttons(self):return int(self.polls%32 in range(8,16))
 def motion(self):
  return [value-self.image.read(field,'<h')[0]for value,field in zip(self.position,(0x24196,0x24198))]
 def interrupt(self,cpu):
  operation=cpu.reg_read(r.UC_X86_REG_EAX)&65535
  if operation==5 and cpu.reg_read(r.UC_X86_REG_EBX)==0:self.polls+=1
  assert operation in (3,4,5,6),('undeclared configuration mouse function',operation)
  if operation not in (3,5,6):return
  x,y=self.position
  cpu.reg_write(r.UC_X86_REG_ECX,x*2);cpu.reg_write(r.UC_X86_REG_EDX,y)
  count=self.buttons if operation==3 else int(self.polls%32==(8 if operation==5 else 16))
  cpu.reg_write(r.UC_X86_REG_EBX,count)
  if operation!=3:cpu.reg_write(r.UC_X86_REG_EAX,self.buttons)
