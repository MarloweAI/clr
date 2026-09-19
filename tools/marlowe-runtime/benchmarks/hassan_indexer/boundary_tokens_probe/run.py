#!/usr/bin/env python3
import argparse,csv,hashlib,json,math,os,statistics,struct,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def hashes(d):return {str(p.relative_to(d)):sha(p) for p in sorted(d.rglob('*')) if p.is_file()}
def env_for(spec):
 e={k:v for k,v in os.environ.items() if not k.startswith(('HSA_','GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HASSAN_','FLYDSL_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG','HIP_VISIBLE_DEVICES','ROC_GLOBAL_CU_MASK')}
 e.update(spec['controls'],LD_LIBRARY_PATH=spec['lib']+':/opt/rocm/lib',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so');return e

def packet_audit(d,g,units):
 captured=(d/'captured.bin').read_bytes();templates=(d/'templates.bin').read_bytes();top=json.loads((d/'topology.json').read_text());nodes={x['index']:x for x in top['nodes']};assert len(nodes)==2*g and len(captured)==len(templates)==128*g
 assert templates==b''.join(captured[i*64:(i+1)*64] for i in top['ordered'])
 prior=set()
 for layer,indices in enumerate(top['layers']):
  assert len(indices)==2 and [nodes[i]['label'] for i in indices]==['q','k']
  assert all(nodes[i]['layer']==layer and set(nodes[i]['dependencies'])==prior for i in indices);prior=set(indices)
 graphs=units//g;counts={};all_signals=set();allocation_sizes={}
 finals=[{k:int(v) for k,v in row.items()} for row in csv.DictReader((d/'finals.csv').open())]
 assert [x['index'] for x in finals]==list(range(graphs)) and len({x['handle'] for x in finals})==graphs
 for mode in [0,1,2]:
  signals=[{k:int(v) for k,v in row.items()} for row in csv.DictReader((d/f'signals-m{mode}.csv').open())]
  assert [row['index'] for row in signals]==list(range(2*units+graphs))
  handles={row['handle'] for row in signals};assert len(handles)==2*units+graphs and not handles&all_signals;all_signals|=handles
  for row in signals:
   assert row['pointer']==row['handle']+8 and row['handle']%64==0 and row['handle']%4096<=3968
   assert row['global_flags']&2 and row['host_base']==row['agent_base']!=0
   assert row['owner_type']==(1 if mode==2 else 0)
   if mode:assert row['handle']==row['agent_base'] and row['handle']%4096==0 and row['allocation_size']==4096
  allocation_sizes[mode]=[row['allocation_size'] for row in signals]
  for lane in [0,1]:
   raw=(d/f'packets-m{mode}-q{lane}.bin').read_bytes();assert len(raw)%64==0;packets=[raw[i:i+64] for i in range(0,len(raw),64)];pos=0
   def barrier(packet,header,dep,completion):
    expected=bytearray(64);struct.pack_into('<H',expected,0,header);struct.pack_into('<Q',expected,8,dep);struct.pack_into('<Q',expected,56,completion);assert packet==expected
   for graph in range(graphs):
    entry=signals[2*units+graph]['handle']
    if lane==0:barrier(packets[pos],3+256+(2<<9)+(2<<11),0,entry)
    else:barrier(packets[pos],3+256+(2<<9),entry,0)
    pos+=1
    for pair in range(g):
     i=graph*g+pair
     if pair:barrier(packets[pos],3+256,signals[2*(i-1)+(1-lane)]['handle'],0);pos+=1
     want=bytearray(templates[64*(2*pair+lane):64*(2*pair+lane+1)]);struct.pack_into('<Q',want,56,signals[2*i+lane]['handle']);assert packets[pos]==want;pos+=1
    if lane==0:
     barrier(packets[pos],3+256+(2<<9)+(2<<11),signals[2*((graph+1)*g-1)+1]['handle'],finals[graph]['handle']);pos+=1
   assert pos==len(packets)==2*units+(graphs if lane==0 else 0);counts[f'm{mode}q{lane}']=len(packets)
 assert not {x['handle'] for x in finals}&all_signals
 assert allocation_sizes[1]==allocation_sizes[2],allocation_sizes
 return counts

def audit(out):
 m=json.loads((out/'manifest.json').read_text());source=json.loads((R/'source.json').read_text());spec=json.loads((R/'protocol.json').read_text());assert m['complete'] and m['source']==source
 for f,h in source.items():assert sha(R/f)==h
 assert hashes(out/'build')==m['build_artifacts'];build=json.loads((out/'build/build.json').read_text());assert build['source']==source and build['libraries']==spec['libraries']
 assert [r['group'] for r in m['runs']]==spec['groups'];summaries={};check_count=0;row_count=0;data=None
 for rec in m['runs']:
  d=out/rec['name'];assert rec['returncode']==0 and hashes(d)==rec['artifacts'] and sha(out/(rec['name']+'.log'))==rec['log_sha256'];assert (d/'COMPLETE').read_text()=='PASS\n';g=rec['group'];units=rec['units'];counts=packet_audit(d,g,units)
  ident=json.loads((d/'identity.json').read_text());assert ident['group']==g and ident['units']==units and ident['pilot']==rec['pilot'] and ident['controls']==spec['controls'] and ident['external_sources']==spec['external_sources']
  assert {k:v['sha256'] for k,v in ident['libraries'].items()}==spec['libraries'] and ident['helpers']==build['helpers']
  if data is None:data=ident['data_sha256']
  assert ident['data_sha256']==data==spec['data_sha256']
  for filename in ['maps-before-import.txt','maps-after-capture.txt','maps-after.txt']:
   text=(d/filename).read_text()
   for stem,receipt in ident['libraries'].items():assert {x.split()[-1] for x in text.splitlines() if stem+'.so' in x}=={receipt['path']}
  checks=json.loads((d/'correctness.json').read_text());phases=['initial','changed-m0','restored-m0','changed-m1','restored-m1','changed-m2','restored-m2']+[f'r{r}-{cell}' for r,order in enumerate(ident['orders']) for cell in order]
  assert len(checks)==len(phases)*2*g and {(c['phase'],c['index']) for c in checks}=={(p,i) for p in phases for i in range(2*g)}
  assert all(c['finite'] and c['nrms']<=(.0067 if c['label']=='q' else .012) and c['nmax']<=(.20 if c['label']=='q' else .15) for c in checks);check_count+=len(checks)
  rows=json.loads((d/'timings.json').read_text());assert [(r['round'],r['cell'],r['trial']) for r in rows]==[(r,c,t) for r,order in enumerate(ident['orders']) for c in order for t in range(1 if rec['pilot'] else 8)];row_count+=len(rows)
  profile={(t['round'],t['cell'],t['trial']):t['times'] for t in json.loads((d/'dispatch-times.json').read_text())};assert len(profile)==(3 if rec['pilot'] else 96)
  med={};rounds={};gaps={};min_dependent_gap=None;wraps=0
  last_indices=None
  for row in rows:
   assert row['group']==g and row['units']==units
   cell=row['cell'];r=row['round'];rounds.setdefault(cell,{}).setdefault(r,[]).append(row)
   if cell=='hip':assert all(math.isfinite(row[f]) and row[f]>0 for f in ['gpu_us','host_us','submit_us']);continue
   assert row['completed_signals']==2*units+units//g and row['queue0']!=row['queue1'] and row['system_hz']>0
   assert all(math.isfinite(row[f]) and row[f]>0 for f in ['prepare_us','publish_us','total_us','latency_us'])
   assert abs(row['total_us']-row['prepare_us']-row['publish_us']-row['latency_us'])<1e-6
   mode=int(cell[1]);profiling=int(cell[3])
   for lane in [0,1]:
    first,last=row[f'first{lane}'],row[f'last{lane}'];assert last-first+1==counts[f'm{mode}q{lane}'];wraps+=int(first%4096+last-first+1>4096)
    if last_indices is not None:assert first>last_indices[lane]
   last_indices=[row['last0'],row['last1']]
   if not profiling:assert row['dispatch_envelope_us']==0;continue
   times=profile[(r,cell,row['trial'])];assert len(times)==4*units
   pairs=[(times[2*i],times[2*i+1]) for i in range(2*units)];assert all(start>0 and end>=start for start,end in pairs)
   assert abs(row['dispatch_envelope_us']-(max(x[1] for x in pairs)-min(x[0] for x in pairs))*1e6/row['system_hz'])<1e-6
   first_resume=[];both_resume=[]
   for i in range(1,units):
    ready=max(pairs[2*(i-1)][1],pairs[2*(i-1)+1][1]);a,b=pairs[2*i][0],pairs[2*i+1][0]
    first_resume.append((min(a,b)-ready)*1e6/row['system_hz']);both_resume.append((max(a,b)-ready)*1e6/row['system_hz'])
   lowest=min(first_resume);min_dependent_gap=lowest if min_dependent_gap is None else min(min_dependent_gap,lowest)
   gaps.setdefault(cell,[]).append(dict(first_resume_us=statistics.median(first_resume),both_resume_us=statistics.median(both_resume),host_minus_envelope_us=row['latency_us']-row['dispatch_envelope_us']))
  for cell,rr in rounds.items():
   fields=['gpu_us','host_us','submit_us'] if cell=='hip' else ['latency_us','dispatch_envelope_us','prepare_us','publish_us','total_us']
   rounds[cell]={r:{f:statistics.median(x[f] for x in rows)/units for f in fields} for r,rows in rr.items()}
   med[cell]={f:statistics.median(x[f] for x in rounds[cell].values()) for f in fields}
  if not rec['pilot']:assert wraps>0
  # Negative dependency intervals reject timestamp interpretation, not numerical timing data.
  summaries[str(g)]=dict(us_per_pair=med,round_medians=rounds,packet_counts=counts,observed_wraps=wraps,profile_clock_gate_pass=min_dependent_gap>=0,min_dependency_gap_us=min_dependent_gap,profile_gaps={c:{f:statistics.median(x[f] for x in values) for f in values[0]} for c,values in gaps.items()})
 result=dict(passed=True,job=m['job'],timing_rows=row_count,correctness_rows=check_count,groups=summaries,manifest_sha256=sha(out/'manifest.json'),qualified=False)
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==json.loads(json.dumps(result))
 else:write(out/'summary.json',result)
 print(json.dumps(result),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);spec=json.loads((R/'protocol.json').read_text());source=json.loads((R/'source.json').read_text())
 for f,h in source.items():assert sha(R/f)==h
 m=dict(job=os.environ['SLURM_JOB_ID'],complete=False,source=source,runs=[]);save=lambda:write(out/'manifest.json',m);save()
 subprocess.run([sys.executable,str(R/'build.py'),str(out/'build')],check=True);m['build_artifacts']=hashes(out/'build');save()
 for g in spec['groups']:
  pilot=False;units=spec['units'];name=f'g{g}';rec=dict(name=name,group=g,units=units,pilot=pilot,started=time.time());m['runs'].append(rec);save()
  with (out/(name+'.log')).open('x') as f:proc=subprocess.run([sys.executable,str(R/'benchmark.py'),'--group',str(g),'--out',str(out/name),'--build',str(out/'build'),'--units',str(units)]+(['--pilot'] if pilot else []),env=env_for(spec),stdout=f,stderr=subprocess.STDOUT)
  rec.update(returncode=proc.returncode,elapsed_s=time.time()-rec['started']);save();assert proc.returncode==0,(name,proc.returncode)
  rec.update(artifacts=hashes(out/name),log_sha256=sha(out/(name+'.log')));save();print('PASS',name,flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
