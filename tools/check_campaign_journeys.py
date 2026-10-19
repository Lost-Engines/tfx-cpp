#!/usr/bin/env python3
"""Compare persistent campaign journeys and repeated native save/load boundaries.

Flight results and menu choices are explicit host inputs, not claimed natural
sorties. Original control and serialization handlers execute continuously;
media/planners are observed boundaries. The C++ production parser and pilot
store must agree at every yield, including exact save bytes and resumed stacks.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import tempfile
from native_campaign import NativeCampaign

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--research',type=Path,default=Path('../tfx-reverse'))
p.add_argument('--build',type=Path,default=Path('build'))
p.add_argument('--report',type=Path)
a=p.parse_args()
program=next(x for x in json.loads((a.research/'analysis/presentations/programs.json').read_text()) if x['name']=='tfx')
functions=program['functions'];named={f['name']:i for i,f in enumerate(functions)}
native=NativeCampaign(a.research/'installs/cd_1994_09/TFX',program)
numeric=[v['name'] for v in program['variables'] if not v['string_value']]
scenarios=[(name,name,[]) for name in ('fws','soapcol','soaplib','soapsom','soapyug2','soapsea','todefa','todf22','todf17','arcade')]
scenarios += [(f'{name}-retry-ejection',name,[(0,0,0,1),(3,1,0,1),(3,1,0,1)]) for name in ('fws','soapcol','todefa','todf22','todf17')]
scenarios += [(f'soapcol-outcome-{outcome}','soapcol',[(outcome,0,status,safe)]) for outcome,status,safe in ((1,4,0),(2,1,0),(3,3,0),(99,0,0))]
scenarios += [(f'{name}-repeated-ejection',name,[(3,0,2,1),(3,0,2,1)]) for name in ('soapcol','todefa','todf22','todf17')]
scenarios += [('arcade-three-losses','arcade',[(1,0,4,0)]*3),('tour-score-wrap','todefa',[])]
commands=[];expected=[];labels=[];reports=[]
def emit(command):commands.append(command)
def set_value(name,value):
 value &= 0xffffffff;native.set(name,value);emit(f'V {name} {value}')
def observe(label):
 action=native.run();emit('N');expected.append(' '.join(map(str,native.row(action))));labels.append(label)
 return action

def save(slot,log,mode,label):
 raw=native.save(mode);emit(f'S {slot} {int(log)} {mode}')
 expected.append('S '+str(len(raw))+' '+' '.join(map(str,raw)));labels.append(label)
 return raw

for scenario,entry,returns in scenarios:
 initial=dict(rank=0 if entry=='fws' else 1,lives=3,miss_val=1,sqd_val=3,soap_val=1)
 if scenario=='tour-score-wrap':initial['score']=0xfffffff0
 native.reset((named[entry],0),initial)
 emit('R '+' '.join(map(str,[named[entry],0,*[initial.get(name,0) for name in numeric]])))
 launches=[];visited=Counter();log=None;saves=0
 for step in range(12000):
  action=observe(f'{scenario} step {step}')
  if action is None:break
  fi,ni,kind=action;node=functions[fi]['nodes'][ni];resource=node.get('resource','')
  visited[functions[fi]['name']]+=1
  # Persist, disturb and restore at every host boundary. Both versions execute
  # their actual save readers; no expected snapshot is copied into the C++ side.
  slot=1+step%9;raw=save(slot,False,2,f'{scenario} checkpoint {step}');saves+=1
  set_value('score',native.values()['score']^0xa5a55a5a)
  native.complete();emit('C')
  native.restore(raw);emit(f'L {slot} 0')
  assert observe(f'{scenario} restored {step}')==action
  if kind==8:
   if launches:break
   assert entry=='arcade' and resource=='arcade',(scenario,action,resource)
   set_value('miss_val',1)
  elif kind==5 and resource=='%mission':
   values=native.values();launches.append(values['mission'])
   outcome,success,status,safe=returns[len(launches)-1] if len(launches)<=len(returns) else (0,1,0,1)
   for key,value in dict(outcome=outcome,miss_val=success,status=status,safe=safe,score=values['score']+137,a2akills=values['a2akills']+1,a2gkills=values['a2gkills']+1,num_miss=values['num_miss']+1,num_hours=values['num_hours']+3).items():set_value(key,value)
  elif kind==5 and resource=='slog':log=save(0,True,0,f'{scenario} native log')
  elif kind==5 and resource=='rlog':
   assert log is not None,(scenario,'restore without saved log')
   native.restore(log);emit('L 0 1')
  elif kind==5 and resource=='spos':save(0,False,2,f'{scenario} authored save');saves+=1
  elif kind==5 and resource=='enrol':break
  elif kind==7:break
  else:assert kind in (0,1,2,5,9,11,12,13),(scenario,'unexpected host boundary',action)
  native.complete();emit('C')
 else:raise AssertionError((scenario,'journey exceeded its bound',launches,native.values()))
 assert launches,(scenario,'no flight boundary reached')
 if not returns and entry!='arcade':
  authored=[]
  for node in functions[named[entry]]['nodes']:
   if node['type']==10:
    raw=bytes.fromhex(node['payload_hex']);ordinal=int.from_bytes(raw[:4],'little')
    if ordinal<len(program['variables']) and program['variables'][ordinal]['name']=='mission':authored.append(int.from_bytes(raw[5:9],'little'))
  assert launches==authored,(scenario,launches,authored)
 reports.append({'scenario':scenario,'missions':launches,'host_yields':sum(visited.values()),'save_roundtrips':saves,'final_values':native.values(),'visited_functions':sorted(visited)})

with tempfile.TemporaryDirectory(prefix='tfx-campaign-journeys-') as temporary:
 result=subprocess.run([str((a.build/'campaign_journey_probe').resolve()),str((a.research/'installs/cd_1994_09/TFX').resolve()),temporary],input='\n'.join(commands)+'\n',capture_output=True,text=True,timeout=120)
 assert result.returncode==0,(result.returncode,result.stderr)
 actual=result.stdout.splitlines()
 assert len(actual)==len(expected),(len(actual),len(expected),result.stderr)
 for index,(got,wanted) in enumerate(zip(actual,expected)):
  assert got==wanted,(labels[index],got,wanted)
required={'death1','mia','eject_ok','bust_ejc','busted1','promote','un-defeat'}
visited={name for journey in reports for name in journey['visited_functions']}
assert required<=visited,('missing persistent campaign branch',required-visited)
report={'scope':__doc__,'journeys':reports,'comparisons':len(expected),'matched':True}
if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
print(f"{len(reports)} persistent campaign journeys agree: {sum(len(x['missions']) for x in reports)} supplied flight returns, {sum(x['save_roundtrips'] for x in reports)} native byte-exact save/reload checkpoints and {len(expected)} state/stack/save comparisons")
