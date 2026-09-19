#!/usr/bin/env python3
"""Unchanged historical executables and references; new runtime comparison only."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json,math,os,shutil,statistics,subprocess,sys
from child import audit_receipt
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
def controls(s,mode,family):return s['modes'][mode]['controls']|{'GPU_MAX_HW_QUEUES':str(s['families'][family]['cap'])}
def inspect(s,out,rec,live=False):
 c=s['families'][rec['family']];p=s['modes'][rec['mode']];log=(out/(rec['name']+'.log')).read_text();rows=list(csv.DictReader((out/(rec['name']+'.csv')).open()))
 assert rec['returncode']==0 and rec['controls']==controls(s,rec['mode'],rec['family']);audit_receipt(log,rec['controls'])
 assert not any(x.startswith(('GRAPH_FRONTIER_','GRAPH_QUEUE_','GRAPH_LOCAL_','NATIVE_COST ','NATIVE_EVENT_PACKET ')) for x in log.splitlines())
 assert Counter(tuple(row[k] for k in c['keys']) for row in rows)==Counter(tuple(v) for v in c['coverage'])
 assert all(row['correct']=='1' and float(row[c['metric']])>0 for row in rows)
 assert all(math.isfinite(float(row[k])) for row in rows for k in c['fields'])
 hashes=p['libraries']|({'librocblas':c['rocblas_sha256']} if c['exe']=='llm' else {});mapped={}
 if c['exe']=='llm':assert 'CUs=256' in log and 'mode='+rec['mode'] in log
 for stem,h in hashes.items():
  paths={line.split()[-1] for line in log.splitlines() if line.startswith('LIBRARY ') and stem in line};assert len(paths)==1;path=paths.pop()
  if live:assert sha(path)==h
  mapped[stem]=dict(path=path,sha256=h)
 observed=dict(rows=len(rows),mapped=mapped,csv_sha256=sha(out/(rec['name']+'.csv')),log_sha256=sha(out/(rec['name']+'.log')))
 if 'observed' in rec:assert rec['observed']==observed
 return observed,rows

def audit(out,live=False):
 s=json.loads((W/'spec.json').read_text());m=json.loads((out/'manifest.json').read_text());assert m['complete'] and m['node']=='marlowe-mi355x-2' and m['spec_sha256']==sha(W/'spec.json')
 for f,h in s['sources'].items():assert sha(W/f)==h
 assert files(out/'bins')==s['binaries'];assert files(out/'references')==s['references']
 wanted=[(r,mode,family) for r,order in enumerate(s['orders']) for mode in order for family in s['families']];assert [(v['round'],v['mode'],v['family']) for v in m['runs']]==wanted
 values=defaultdict(lambda:defaultdict(dict));n=0
 for rec in m['runs']:
  _,rows=inspect(s,out,rec,live);n+=len(rows);c=s['families'][rec['family']];groups=defaultdict(list)
  for row in rows:groups[tuple(row[k] for k in c['keys'][:-1])].append(row)
  for cell,rr in groups.items():values[(rec['family'],*cell)][rec['mode']][rec['round']]={f:statistics.median(float(row[f]) for row in rr) for f in c['fields']}
 cells=[]
 for key,modes in sorted(values.items()):
  c=s['families'][key[0]];assert set(modes)==set(s['modes']) and all(set(v)==set(range(4)) for v in modes.values());med={mode:{f:statistics.median(v[f] for v in rounds.values()) for f in c['fields']} for mode,rounds in modes.items()};f=c['metric']
  contrasts={b:dict(percent=100*(med['distributed'][f]/med[b][f]-1),round_percent=[100*(modes['distributed'][r][f]/modes[b][r][f]-1) for r in range(4)]) for b in ['stock','central','previous']}
  cells.append(dict(family=key[0],cell=list(key[1:]),metric=f,medians=med,contrasts=contrasts))
 result=dict(passed=True,job=m['job'],qualified=False,processes=len(wanted),timing_rows=n,manifest_sha256=sha(out/'manifest.json'),cells=cells)
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==result
 else:write(out/'summary.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='cells'}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 s=json.loads((W/'spec.json').read_text());prior=Path(s['prior_root'])
 for f,h in s['sources'].items():assert sha(W/f)==h
 for name,h in s['binaries'].items():assert sha(prior/name)==h
 for policy in s['modes'].values():
  for stem,h in policy['libraries'].items():assert sha(Path(policy['lib'])/(stem+'.so'))==h
 out.mkdir(exist_ok=False);(out/'bins').mkdir();shutil.copytree(prior/'references',out/'references');assert files(out/'references')==s['references']
 for name in s['binaries']:shutil.copy2(prior/name,out/'bins'/name)
 m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,spec_sha256=sha(W/'spec.json'),runs=[]);save=lambda:write(out/'manifest.json',m);save()
 for r,order in enumerate(s['orders']):
  for mode in order:
   for family,c in s['families'].items():
    policy=s['modes'][mode];name=f'r{r}-{mode}-{family}';ctrl=controls(s,mode,family);env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HSA_','LLM_','HASSAN_','FLYDSL_')) and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_DEBUG','HIP_VISIBLE_DEVICES')};env.update(ctrl,LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LD_LIBRARY_PATH=policy['lib']+':/opt/rocm/lib',LLM_RUNTIME_MODE=mode,LLM_TRIALS='8',LLM_REFERENCE_DIR=str(out/'references'),LLM_GROUP_DEPTH='1',LLM_GROUP_HEADS='32',LLM_GROUP_SPLITS='1',LLM_GROUP_PLAN_US='0',LLM_GROUP_MAIN_BACKUP='0')
    args=[c['argument']] if c['exe']=='llm' else ['3',str(out/'references')] if c['exe']=='queued_chains' else ['24'];argv=[sys.executable,str(W/'child.py'),str(out/'bins'/c['exe']),*args];print('BENCH',name,flush=True)
    with (out/(name+'.csv')).open('w') as f,(out/(name+'.log')).open('w') as log:q=subprocess.run(argv,env=env,stdout=f,stderr=log)
    rec=dict(name=name,round=r,mode=mode,family=family,controls=ctrl,returncode=q.returncode);m['runs'].append(rec);save();rec['observed'],_=inspect(s,out,rec,True);save();print('PASS',name,rec['observed']['rows'],flush=True)
 m['complete']=True;save();audit(out,True);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
