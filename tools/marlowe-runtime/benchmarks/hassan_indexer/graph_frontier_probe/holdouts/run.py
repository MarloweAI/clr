#!/usr/bin/env python3
"""Frozen expert/grouped-KV holdouts; diagnostic structural observations are untimed."""
import argparse, csv, hashlib, json, math, os, re, shutil, statistics, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path
from child import audit_receipt
ROOT=Path(__file__).resolve().parent
PREVIOUS=ROOT.parent.parent/'stream-wait-calibration-20260918'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def env_for(s,mode,refs,family,proof=False):
 p=s['modes'][mode];cfg=s['families'][family]
 env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','LLM_','HSA_','HASSAN_','FLYDSL_')) and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_DEBUG','HIP_VISIBLE_DEVICES')}
 c=p['controls']|({'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1'} if proof else {})
 env.update(c,LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LD_LIBRARY_PATH=p['lib']+':/opt/rocm/lib',
  LLM_RUNTIME_MODE=mode,LLM_TRIALS='4' if proof else '8',LLM_REFERENCE_DIR=str(refs),LLM_GROUP_DEPTH='1',LLM_GROUP_HEADS='32',LLM_GROUP_SPLITS=cfg['splits'],LLM_GROUP_PLAN_US='0',LLM_GROUP_MAIN_BACKUP='0')
 return env,c

def inspect(s,out,rec,live=False):
 family,mode=rec['family'],rec['mode'];cfg=s['families'][family];stem=out/rec['name']
 log=stem.with_suffix('.log').read_text();rows=list(csv.DictReader(stem.with_suffix('.csv').open()))
 c=s['modes'][mode]['controls']|({'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1'} if rec['proof'] else {})
 assert rec['returncode']==0 and rec['controls']==c
 audit_receipt(log,c)
 expected=[x for x in cfg['coverage'] if not rec['proof'] or int(x[-1])<4]
 assert Counter(tuple(x[k] for k in cfg['keys']) for x in rows)==Counter(tuple(x) for x in expected)
 assert all(x['correct']=='1' for x in rows)
 assert all(math.isfinite(float(x[f])) and float(x[f])>0 for x in rows for f in cfg['positive_fields'])
 assert 'CUs=256' in log and 'mode='+mode in log
 hashes=s['modes'][mode]['libraries']|{'librocblas':cfg['rocblas_sha256']};mapped={}
 for stemname,h in hashes.items():
  paths={l.split()[-1] for l in log.splitlines() if l.startswith('LIBRARY ') and stemname in l}
  assert len(paths)==1;path=paths.pop()
  if live:assert sha(path)==h,(path,h)
  mapped[stemname]={'path':path,'sha256':h}
 result=dict(rows=len(rows),csv_sha256=sha(stem.with_suffix('.csv')),log_sha256=sha(stem.with_suffix('.log')),mapped=mapped)
 if rec['proof']:
  active={};compact=[];begins=ends=releases=0
  for line in re.findall(r'GRAPH_FRONTIER_[A-Z_]+ [^\r\n]*',log):
   typ=line.split()[0];v=dict(re.findall(r'(\w+)=(\S+)',line));key=(v.get('graph'),v.get('serial'))
   if typ=='GRAPH_FRONTIER_BEGIN':
    assert key not in active and v['generation'] not in [x['begin']['generation'] for x in active.values()]
    active[key]=dict(begin=v,segments=[],ended=False);begins+=1
   elif typ=='GRAPH_FRONTIER_SEGMENT':
    assert key in active and not active[key]['ended'];active[key]['segments'].append(v)
   elif typ=='GRAPH_FRONTIER_END':
    assert key in active and v['status']=='0';a=active[key];assert not a['ended'];a['ended']=True;ends+=1
    ids={x['segment'] for x in a['segments']};lanes={x['physical'] for x in a['segments']}
    assert len(ids)==len(a['segments'])==int(a['begin']['segments'])==int(v['submitted']) and len(lanes)==int(a['begin']['lanes']) and len(lanes)>=2
   elif typ=='GRAPH_FRONTIER_RELEASE':
    assert key in active and v['recycled']=='1';a=active.pop(key);assert a['ended'] and a['begin']['generation']==v['generation'];releases+=1
    compact.append(dict(graph=key[0],serial=int(key[1]),segments=len(a['segments']),physical=len({x['physical'] for x in a['segments']})))
  assert not active and begins==ends==releases
  eligible=family=='experts' and mode in ['local','v1']
  assert (begins>0)==eligible,(family,mode,begins)
  if eligible:assert begins==48,('six multi-stream expert graphs times eight proof launches',begins)
  result['structure']=dict(frontier_launches=begins,graphs=compact,fallback_receipts=len(re.findall(r'GRAPH_LOCAL_FALLBACK ',log)))
 else:
  assert not any(l.startswith(('GRAPH_QUEUE_','GRAPH_LOGICAL_COALESCE ','GRAPH_SHARED_RETIRE ','GRAPH_LANE_','GRAPH_FRONTIER_','GRAPH_LOCAL_','NATIVE_POLICY_','NATIVE_EVENT_PACKET ')) for l in log.splitlines())
 if 'csv_sha256' in rec:assert all(rec[k]==v for k,v in result.items())
 return result,rows

def audit(specpath,out,live=False):
 s=json.loads(specpath.read_text());m=json.loads((out/'manifest.json').read_text())
 assert m['spec_sha256']==sha(specpath) and m['complete'] and m['node']=='marlowe-mi355x-2'
 for f,h in s['sources'].items():assert sha(ROOT/f)==h,f
 assert sha(out/'llm')==s['binary_sha256']
 assert {p.name:sha(p) for p in (out/'references').iterdir()}==s['references']
 wantproof=[(True,-1,mode,family) for mode in s['proof_modes'] for family in ['experts','grouped_s22']]
 wanttime=[(False,r,mode,family) for r,order in enumerate(s['orders']) for mode in order for family in s['families']]
 assert [(r['proof'],r['round'],r['mode'],r['family']) for r in m['runs']]==wantproof+wanttime
 values=defaultdict(lambda:defaultdict(dict));nrows=0
 for rec in m['runs']:
  verified,rows=inspect(s,out,rec,live)
  if rec['proof']:continue
  nrows+=len(rows);cfg=s['families'][rec['family']];group=defaultdict(list)
  for row in rows:group[tuple(row[k] for k in cfg['keys'][:-1])].append(row)
  for cell,rr in group.items():values[(rec['family'],*cell)][rec['mode']][rec['round']]={f:statistics.median(float(x[f]) for x in rr) for f in cfg['fields']}
 comparisons=s['comparisons'];cells=[]
 for key,modes in sorted(values.items()):
  assert set(modes)==set(s['modes']) and all(set(v)==set(range(4)) for v in modes.values())
  fields=s['families'][key[0]]['fields'];med={mode:{f:statistics.median(v[f] for v in rounds.values()) for f in fields} for mode,rounds in modes.items()}
  contrasts={a+'/'+b:{f:dict(delta_us=med[a][f]-med[b][f],percent=100*(med[a][f]/med[b][f]-1),round_percent=[100*(modes[a][r][f]/modes[b][r][f]-1) for r in range(4)]) for f in fields} for a,b in comparisons}
  cells.append(dict(family=key[0],cell=list(key[1:]),median_us=med,contrasts=contrasts))
 assert len(cells)==76
 result=dict(audit_passed=True,qualified_for_production=False,processes=len(wanttime),timing_rows=nrows,proof_processes=len(wantproof),spec_sha256=sha(specpath),cells=cells)
 if live:write(out/'summary.json',result)
 else:assert result==json.loads((out/'summary.json').read_text())
 print(json.dumps({k:v for k,v in result.items() if k!='cells'}),flush=True)
 for x in cells:
  if x['cell'][-1]=='graph' and x['cell'][-2]=='total':print(json.dumps(x),flush=True)
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--spec',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--audit',action='store_true');a=ap.parse_args()
 if a.audit:audit(a.spec,a.out);return
 s=json.loads(a.spec.read_text());out=a.out;out.mkdir(exist_ok=False)
 for f,h in s['sources'].items():assert sha(ROOT/f)==h
 for f,h in s['inputs'].items():assert sha(PREVIOUS/f)==h,(f,'input hash')
 shutil.copy2(PREVIOUS/s['binary'],out/'llm');shutil.copytree(PREVIOUS/s['reference_dir'],out/'references')
 for p in s['modes'].values():
  for stem,h in p['libraries'].items():assert sha(Path(p['lib'])/(stem+'.so'))==h
 m=dict(job=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,spec_sha256=sha(a.spec),complete=False,runs=[]);save=lambda:write(out/'manifest.json',m);save()
 steps=[(True,-1,mode,family) for mode in s['proof_modes'] for family in ['experts','grouped_s22']]+[(False,r,mode,family) for r,order in enumerate(s['orders']) for mode in order for family in s['families']]
 for proof,r,mode,family in steps:
  name=('proof' if proof else 'r'+str(r))+'-'+mode+'-'+family
  env,c=env_for(s,mode,out/'references',family,proof);argv=['/opt/venv/bin/python',str(ROOT/'child.py'),str(out/'llm'),s['families'][family]['argument']]
  rec=dict(proof=proof,round=r,mode=mode,family=family,name=name,controls=c,started=time.time(),argv=argv);m['runs'].append(rec);save()
  with (out/(name+'.csv')).open('x') as f,(out/(name+'.log')).open('x') as log:p=subprocess.run(argv,env=env,stdout=f,stderr=log)
  rec.update(returncode=p.returncode,elapsed_s=time.time()-rec['started']);save()
  verified,_=inspect(s,out,rec,True);rec.update(verified);save();print(name,'PASS',rec['rows'],flush=True)
 m['complete']=True;save();audit(a.spec,out,True);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
