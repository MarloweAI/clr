#!/usr/bin/env python3
"""Existing attention-dispatch and original waiter loops, unmodified kernels/cases."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,hashlib,json,math,os,statistics,subprocess,sys
from child import audit_receipt
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
KEYS=('heads','tokens','launches','form','schedule','trial')
FIELDS=('total_us','host_us','submit_us','a_span_us','b_span_us','handoff_us','overlap_us','b_end_minus_a_us')
def dispatch_cells(n):
 return Counter(tuple(map(str,(h,t,k,f,s,r))) for h,t in ((256,256),(256,1024),(64,8192)) for k in (1,4,16,256) if h!=64 or k==1 for f in ('eager','graph') for s in ('serial','parallel','wide') if s!='wide' or k==1 for r in range(n))
def inspect(out,rec,s,live=False):
 p=s['modes'][rec['mode']];log=(out/(rec['name']+'.log')).read_text();rows=list(csv.DictReader((out/(rec['name']+'.csv')).open()))
 assert rec['returncode']==0 and rec['controls']==p['controls'];audit_receipt(log,rec['controls'])
 assert not any(x.startswith(('GRAPH_FRONTIER_','GRAPH_QUEUE_','GRAPH_LOCAL_','NATIVE_COST ','NATIVE_EVENT_PACKET ')) for x in log.splitlines())
 mapped={}
 for stem,h in p['libraries'].items():
  paths={line.split()[-1] for line in log.splitlines() if line.startswith('LIBRARY ') and stem in line};assert len(paths)==1;path=paths.pop()
  if live:assert sha(path)==h
  mapped[stem]=dict(path=path,sha256=h)
 if rec['bench']=='dispatch':
  assert Counter(tuple(row[k] for k in KEYS) for row in rows)==dispatch_cells(s['repeats'])
  assert all(row['correct']=='1' and float(row['max_abs_error'])<=2e-5 for row in rows)
  assert all(math.isfinite(float(row[k])) for row in rows for k in FIELDS)
  assert all(float(row[k])>0 for row in rows for k in ('total_us','host_us','submit_us','a_span_us','b_span_us'))
  assert all(float(row['handoff_us'])>=-1 and float(row['overlap_us'])>=0 for row in rows)
  receipt=f"CONTROLS wait={p['controls']['GPU_NATIVE_EVENT_WAIT']} relaxed=(null) minimum=(null) trace=0 queue_cap=4";assert receipt in log
 else:
  assert Counter((r['block'],r['case']) for r in rows)==Counter({(str(b),c):8 for b in range(5) for c in ('alone','pending_wait','ready_wait')})
  assert all(r['correct']=='1' and math.isfinite(float(r['gpu_us'])) and float(r['gpu_us'])>0 for r in rows)
  assert all(r['pending']=='1' for r in rows if r['case']=='pending_wait')
 observed=dict(rows=len(rows),mapped=mapped,csv_sha256=sha(out/(rec['name']+'.csv')),log_sha256=sha(out/(rec['name']+'.log')))
 if 'observed' in rec:assert rec['observed']==observed
 return observed,rows

def audit(out,live=False):
 s=json.loads((W/'spec.json').read_text());m=json.loads((out/'manifest.json').read_text());assert m['complete'] and m['node']=='marlowe-mi355x-2' and m['spec_sha256']==sha(W/'spec.json')
 for f,h in s['sources'].items():assert sha(W/f)==h
 assert files(out/'bins')==m['binaries'] and files(out/'references')==m['references']
 wanted=[(r,mode,bench) for r,order in enumerate(s['orders']) for mode in order for bench in ('dispatch','waiter')]
 assert [(v['round'],v['mode'],v['bench']) for v in m['runs']]==wanted
 values=defaultdict(lambda:defaultdict(dict));n=0
 for rec in m['runs']:
  observed,rows=inspect(out,rec,s,live);n+=len(rows);keys=KEYS[:-1] if rec['bench']=='dispatch' else ('case',);field='total_us' if rec['bench']=='dispatch' else 'gpu_us';groups=defaultdict(list)
  for row in rows:groups[tuple(row[k] for k in keys)].append(float(row[field]))
  for cell,v in groups.items():values[(rec['bench'],*cell)][rec['mode']][rec['round']]=statistics.median(v)
 cells=[]
 for key,modes in sorted(values.items()):
  assert set(modes)==set(s['modes']) and all(set(v)==set(range(len(s['orders']))) for v in modes.values())
  med={mode:statistics.median(v.values()) for mode,v in modes.items()}
  contrasts={b:dict(percent=100*(med['local']/med[b]-1),round_percent=[100*(modes['local'][r]/modes[b][r]-1) for r in range(len(s['orders']))]) for b in ('stock','off','previous')}
  cells.append(dict(bench=key[0],cell=list(key[1:]),gpu_us=med,contrasts=contrasts,round_medians=modes))
 result=dict(passed=True,job=m['job'],qualified=False,processes=len(wanted),timing_rows=n,manifest_sha256=sha(out/'manifest.json'),cells=cells)
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==json.loads(json.dumps(result))
 else:write(out/'summary.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='cells'}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 s=json.loads((W/'spec.json').read_text())
 for f,h in s['sources'].items():assert sha(W/f)==h
 for policy in s['modes'].values():
  for stem,h in policy['libraries'].items():assert sha(Path(policy['lib'])/(stem+'.so'))==h
 out.mkdir(exist_ok=False);(out/'references').mkdir();(out/'bins').mkdir()
 for bench,src in [('dispatch','attention_dispatch.cpp'),('waiter','minimal_wait.cpp')]:subprocess.run(['/opt/rocm/bin/hipcc','-O3','-std=c++17','--offload-arch=gfx950',str(W/src),'-o',str(out/'bins'/bench)],check=True)
 m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,spec_sha256=sha(W/'spec.json'),binaries=files(out/'bins'),runs=[]);save=lambda:write(out/'manifest.json',m);save()
 for r,order in enumerate(s['orders']):
  for mode in order:
   for bench in ('dispatch','waiter'):
    policy=s['modes'][mode];name=f'r{r}-{mode}-{bench}';ctrl=policy['controls'];env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HSA_','LLM_','HASSAN_','FLYDSL_')) and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_DEBUG','HIP_VISIBLE_DEVICES')};env.update(ctrl,LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LD_LIBRARY_PATH=policy['lib']+':/opt/rocm/lib')
    argv=[sys.executable,str(W/'child.py'),str(out/'bins'/bench)]+([str(s['repeats']),str(out/'references')] if bench=='dispatch' else [])
    print('BENCH',name,flush=True)
    with (out/(name+'.csv')).open('w') as f,(out/(name+'.log')).open('w') as log:q=subprocess.run(argv,env=env,stdout=f,stderr=log)
    rec=dict(name=name,round=r,mode=mode,bench=bench,controls=ctrl,returncode=q.returncode);m['runs'].append(rec);save();rec['observed'],_=inspect(out,rec,s,True);save();print('PASS',name,rec['observed']['rows'],flush=True)
 m.update(complete=True,references=files(out/'references'));save();audit(out,True);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
