"""Untimed v8 receipts: exact published-prefix seals and minimum tail release."""
import re
from pathlib import Path
def inspect(text):
 prepared=[];active={};begins=seals=ends=releases=public=entries=0
 for line in re.findall(r'GRAPH_FRONTIER_[A-Z_]+ [^\r\n]*',text):
  typ=line.split()[0];v=dict(re.findall(r'(\w+)=(\S+)',line));key=(v.get('graph'),v.get('serial'))
  if typ=='GRAPH_FRONTIER_TAIL_RELEASE':
   assert int(v['scope']) in (1,2);prepared.append(v['signal'])
  elif typ=='GRAPH_FRONTIER_ENTRY':
   prior=int(v['prior_tails']);waits=int(v['waits']);assert (prior==0 and waits in (0,1)) or (prior>0 and waits in (prior-1,prior));entries+=1
  elif typ=='GRAPH_FRONTIER_BEGIN':
   n=int(v['segments']);assert len(prepared)>=n and key not in active
   tokens=prepared[-n:];assert len(set(tokens))==n;prepared=[];active[key]=dict(tokens=tokens,published=[],sealed={},ended=False);begins+=1
  elif typ=='GRAPH_FRONTIER_SEGMENT':active[key]['published'].append(v['physical'])
  elif typ=='GRAPH_FRONTIER_SEAL':
   a=active[key];assert v['physical'] not in a['sealed'];a['sealed'][v['physical']]=v['signal'];seals+=1
  elif typ=='GRAPH_FRONTIER_END':
   a=active[key];n=int(v['submitted']);assert n==len(a['published']) and n>0
   assert a['sealed']==dict(zip(a['published'],a['tokens'][:n])),(key,a)
   a['ended']=True;ends+=1
  elif typ=='GRAPH_FRONTIER_PUBLIC':assert int(v['tails'])>0;public+=1
  elif typ=='GRAPH_FRONTIER_RELEASE':
   a=active.pop(key);assert a['ended'] and v['recycled']=='1';releases+=1
 assert not active and begins==ends==releases and (begins==0 or public>0)
 return dict(launches=begins,sealed_tails=seals,public_bridges=public,first_queue_entries=entries)
if __name__=='__main__':
 import sys,json
 print(json.dumps({str(p):inspect(p.read_text()) for p in map(Path,sys.argv[1:])}))
