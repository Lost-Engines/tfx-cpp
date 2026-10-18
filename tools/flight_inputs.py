"""Shared declared external inputs for original/C++ flight captures.

Each row supplies a frame, optional make-code event and that frame's held keys.
Optional mouse motion is a signed [dx,dy] pair; buttons is the DOS left/right
bit mask. The first frame primes desktop cursor capture and must be neutral.
An optional configuration list supplies logical [x,y] mouse clicks inside the
modal screen opened by that frame's grave key; the flight clock stays paused.
An optional arming list supplies [x,y,buttons] actions during cheat Ctrl+D;
zero buttons lets the pointer settle without clicking. Each action has a
release/make/release cycle; the final action repeats up to four times to cover
the original polling/release waits. Missing frames are neutral. A press is held for its frame unless held is given.
These are external device inputs, never changes to game state or outcomes.
"""
import json
from pathlib import Path

DEFAULT_REALISM=(0,0,1,1,0,0,0)

def realism_settings(value):
 values=tuple(int(field)for field in value.split(','))
 if len(values)!=7 or any(not 0<=field<=255 for field in values):
  raise ValueError('expected seven comma-separated unsigned bytes for REALISM')
 return values

# DOS scan code, GLFW key code. The current capture transport uses keyboard input.
KEYS={
 'escape':(1,256),'enter':(28,257),'space':(57,32),'backspace':(14,259),'grave':(41,96),
 'insert':(82,260),'delete':(83,261),
 'up':(72,265),'down':(80,264),'left':(75,263),'right':(77,262),
 'shift':(42,340),'right-shift':(54,344),'control':(29,341),'alt':(56,342),
 't':(20,84),'j':(36,74),'a':(30,65),'c':(46,67),'f':(33,70),
 'g':(34,71),'w':(17,87),'b':(48,66),'h':(35,72),'e':(18,69),
 's':(31,83),'z':(44,90),'x':(45,88),'r':(19,82),'n':(49,78),
 'apostrophe':(40,39),'d':(32,68),'q':(16,81),'p':(25,80),'o':(24,79),
 'i':(23,73),'l':(38,76),'v':(47,86),'equal':(13,61),'minus':(12,45),
 'left-bracket':(26,91),'right-bracket':(27,93),
 'slash':(53,47),'keypad-multiply':(55,332),'keypad-minus':(74,333),'keypad-plus':(78,334),
 'comma':(51,44),'period':(52,46),'iso-extra':(86,161),
 'page-up':(73,266),'page-down':(81,267),'keypad-9':(73,329),'keypad-3':(81,323),
 **{digit:(scan,ord(digit))for scan,digit in enumerate('1234567890',2)},
 'home':(71,268),'end':(79,269),
 'keypad-8':(72,328),'keypad-4':(75,324),'keypad-2':(80,322),'keypad-6':(77,326),
 'keypad-7':(71,327),'keypad-1':(79,321),
 **{f'f{i}':(58+i,289+i)for i in range(1,11)},
}

class FlightInputs:
 def __init__(self,rows):
  self.frames={}
  if not isinstance(rows,list):raise ValueError('flight inputs must be a JSON list')
  for row in rows:
   if not isinstance(row,dict) or set(row)-{'frame','event','held','mouse','buttons','configuration','arming'}:raise ValueError('invalid flight input row')
   frame=row.get('frame')
   if type(frame)is not int or not 1<=frame<=65535 or frame in self.frames:raise ValueError('flight input frames must be distinct integers from 1 to 65535')
   event=row.get('event')
   if event is not None and event not in KEYS:raise ValueError('unknown input event '+str(event))
   held=row.get('held',[event]if event is not None else [])
   if not isinstance(held,list) or any(key not in KEYS for key in held):raise ValueError('unknown held flight key')
   if event is not None and event not in held:raise ValueError('a polled press must be held during its frame')
   self.frames[frame]={'frame':frame,'event':event,'held':sorted(set(held))}
   if 'mouse' in row:
    motion=row['mouse']
    if not isinstance(motion,list) or len(motion)!=2 or any(type(value)is not int or not -32768<=value<=32767 for value in motion):raise ValueError('mouse motion must contain two signed words')
    if frame==1 and any(motion):raise ValueError('mouse motion needs one neutral frame to prime desktop capture')
    self.frames[frame]['mouse']=list(motion)
   if 'buttons' in row:
    buttons=row['buttons']
    if type(buttons)is not int or not 0<=buttons<=3:raise ValueError('mouse buttons must be a left/right bit mask from 0 to 3')
    self.frames[frame]['buttons']=buttons
   if 'arming' in row:
    clicks=row['arming']
    if event!='d' or 'control' not in held or not isinstance(clicks,list) or not 1<=len(clicks)<=64:raise ValueError('arming requires Ctrl+D and 1 to 64 pointer actions')
    if any(not isinstance(point,list) or len(point)!=3 or any(type(value)is not int or not 0<=value<limit for value,limit in zip(point,(320,200,4)))for point in clicks):raise ValueError('arming actions must contain logical X/Y and DOS mouse button bits')
    self.frames[frame]['arming']=[list(point)for point in clicks]
   if 'configuration' in row:

    clicks=row['configuration']
    if event!='grave' or not isinstance(clicks,list) or not 1<=len(clicks)<=32:raise ValueError('configuration requires a grave event and 1 to 32 mouse clicks')
    if any(not isinstance(point,list) or len(point)!=2 or any(type(value)is not int or not 0<=value<limit for value,limit in zip(point,(320,200)))for point in clicks):raise ValueError('configuration clicks must be logical screen coordinates')
    self.frames[frame]['configuration']=[list(point)for point in clicks]
  for frame,row in self.frames.items():
   if row['event'] in self.frames.get(frame-1,{}).get('held',[]):raise ValueError('polled key events need a release before another press')
 @classmethod
 def read(cls,path):return cls(json.loads(Path(path).read_text()))
 def rows(self,frames):return [row for frame,row in sorted(self.frames.items())if frame<=frames]
 def at(self,frame):return self.frames.get(frame,{'frame':frame,'event':None,'held':[]})
