#!/usr/bin/env python3
import argparse,copy,csv,hashlib,json,math,os,re,statistics,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def hashes(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def env_for(mode,extra={}):
 e={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HSA_','HASSAN_','FLYDSL_')) and k not in ['LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG','HIP_VISIBLE_DEVICES']}
 e.update(mode['controls']);e.update(LD_LIBRARY_PATH=mode['lib']+':/opt/rocm/lib',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so');e.update(extra);return e

def records(text,name):return [dict(re.findall(r'(\w+)=(\S+)',s)) for s in re.findall(re.escape(name)+r' [^\r\n]*',text)]

def enabled(spec,mode):return spec['modes'][mode]['controls']['GPU_GRAPH_DIAGNOSTIC_LOCAL_SIGNALS']=='1'
def fixture_plan():
 return [('minimal-off',1,'lane',False),('minimal-off',4,'lane',False)]+[(mode,cap,kind,fault) for mode in ['minimal-n1','minimal-n0'] for cap,kind,fault in [(1,'lane',False),(4,'lane',False),(4,'lane',True),(4,'burst',False)]]
def proof_plan(spec):return [(mode,c) for mode in spec['modes'] if mode!='stock' for c in spec['cases']]
def topology_audit(text,controls,cfg):
 selected=records(text,'GRAPH_QUEUE_SELECTED');spares=records(text,'GRAPH_SPARE_POLICY')
 assert selected
 if cfg['operation']=='events':assert spares
 else:assert len({v['physical'] for v in selected})==1
 for v in spares:
  assert v['spare_requested']==controls['GPU_GRAPH_DIAGNOSTIC_SPARE'] and v['qualified_policy']==controls['GPU_GRAPH_DIAGNOSTIC_QUALIFIED_SPARE']
 if cfg['operation']=='events':assert len({v['physical'] for v in selected})==2
 if controls['GPU_GRAPH_DIAGNOSTIC_LOCAL_SIGNALS']=='1' and cfg['operation']=='events' and cfg['group']>1:
  arenas=records(text,'GRAPH_LOCAL_ARENA');assert arenas and all(v['local']=='1' and v['count']==str(2*cfg['group']) for v in arenas)
 return dict(physical_queues=len({v['physical'] for v in selected}),spare_receipts=len(spares))

def trace_audit(text,expect=False,burst=False,fault=False):
 active={};peak=0;begins=0;done=0;retired=[];pending={};packets=0;batches=0;waits=0
 # Fixture output uses several fprintf calls per line; callback receipts may
 # start inside that line. Every runtime receipt is one newline-terminated printf.
 for line in re.findall(r'GRAPH_LOCAL_[A-Z_]+ [^\r\n]*',text):
  name=line.split()[0];v=dict(re.findall(r'(\w+)=(\S+)',line))
  if name=='GRAPH_LOCAL_BEGIN':
   key=(v['graph'],v['serial']);assert key not in active
   assert v['generation'] not in [x['generation'] for x in active.values()]
   active[key]=v;begins+=1;peak=max(peak,len(active))
  elif name=='GRAPH_LOCAL_COMPLETE':
   key=(v['graph'],v['serial']);assert key in active and active[key]['generation']==v['generation'];assert v['status']=='0' and v['recycled']=='1';del active[key];done+=1
  elif name=='GRAPH_LOCAL_RESET':
   h=int(v['header']);assert v['status']=='1' and h&255==2 and (h>>8)&1==1 and (h>>9)&3==2 and (h>>11)&3==2
  elif name=='GRAPH_LOCAL_PACKET':
   key=(v['command'],v['physical']);i=int(v['packet']);n=int(v['total'])
   if i==0:assert key not in pending;pending[key]=[]
   assert key in pending and i==len(pending[key]);assert v['barrier']=='1' and int(v['acquire'])>=1 and int(v['release'])>=1
   assert (int(v['signal'])!=0)==(i+1==n);pending[key].append(v);packets+=1
  elif name=='GRAPH_LOCAL_BATCH':
   key=(v['command'],v['physical']);p=pending.pop(key);assert len(p)==int(v['packets']) and p[-1]['signal']==v['tail'] and v['status']=='1';batches+=1;waits+=int(v['waits'])
  elif name=='GRAPH_LOCAL_RETIRE':
   assert int(v['submitted'])>0 or int(v['status'])!=0
   if not fault:assert v['status']=='0'
   retired.append(v)
 assert not active and not pending and begins==done==len(retired)
 if expect:assert begins>0 and batches>0
 if burst:assert begins==64 and peak>=2
 if fault:assert len(retired)==1 and retired[0]['submitted']=='3' and retired[0]['status']!='0' and int(retired[0]['side_waits'])>0
 return dict(launches=begins,peak_inflight=peak,packets=packets,batches=batches,waits=waits)

def audit(out):
 m=json.loads((out/'manifest.json').read_text());spec=json.loads((out/'spec.json').read_text());h=json.loads((W/'harness.json').read_text());assert m['complete'] and m['harness']==h and m['spec_sha256']==sha(out/'spec.json')
 for f,v in h.items():assert sha(W/f)==v,f
 build=json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text());assert m['build']==build
 protocol=json.loads((W/'protocol.json').read_text());assert spec['cases']==protocol['cases'] and spec['orders']==protocol['orders'] and spec['sources']==h
 for mode,policy in spec['modes'].items():
  assert policy['controls']==protocol['modes'][mode]['controls']
  if mode=='stock':assert policy==protocol['modes'][mode]
  else:assert policy['libraries']=={f.removesuffix('.so'):v for f,v in build['libraries'].items()} and policy['lib'].endswith('/hassan-graph-local-tokens-20260919/lib-'+m['revision'])
 for kind,key in [('source-manifest','source_manifest_sha256'),('full','full_patch_sha256'),('candidate','candidate_patch_sha256')]:
  suffix='.json' if kind=='source-manifest' else '.patch';assert sha(W/(kind+'-'+m['revision']+suffix))==build[key]
 assert hashes(out/'fixtures-bin')==m['fixture_build']
 for rec in m['fixtures']:
  d=out/rec['name'];assert rec['returncode']==0 and hashes(d)==rec['artifacts']
  text=(d/'stderr.log').read_text();trace=trace_audit(text,enabled(spec,rec['mode']) and rec['cap']==4,rec['kind']=='burst',rec['fault']);assert trace==rec['trace']
  if rec['kind']=='burst':assert json.loads((d/'stdout.log').read_text())==dict(passed=True,launches=64,updates=448,checked_values=448,destroyed_before_sync=True)
  else:
   rows=list(csv.DictReader((d/'stdout.log').open()));assert len(rows)==(1 if rec['fault'] else 6) and all(v['correct']=='1' and v['expected_error']==v['observed_error'] for v in rows)
  for stem,v in rec['mapped'].items():assert v['sha256']==build['libraries'][stem+'.so']
 expected_fixtures=fixture_plan()
 assert [(x['mode'],x['cap'],x['kind'],x['fault']) for x in m['fixtures']]==expected_fixtures
 proofwanted=proof_plan(spec)
 assert [(r['mode'],r['case']) for r in m['proofs']]==proofwanted
 timingwanted=[] if m['phase']=='preflight' else [(i,mode,c) for i,order in enumerate(spec['orders']) for mode in order for c in spec['cases']]
 assert [(r['round'],r['mode'],r['case']) for r in m['runs']]==timingwanted
 data=None;ccount=0;tcount=0;vals={}
 for proof,recs in [(True,m['proofs']),(False,m['runs'])]:
  for rec in recs:
   d=out/rec['name'];assert rec['returncode']==0 and hashes(d)==rec['artifacts'] and sha(out/(rec['name']+'.log'))==rec['log_sha256'] and (d/'COMPLETE').read_text()=='PASS\n'
   ident=json.loads((d/'identity.json').read_text());cfg=spec['cases'][rec['case']];policy=spec['modes'][rec['mode']];controls=policy['controls']|({'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1'} if proof else {})
   assert ident['config']==cfg and ident['proof']==proof and ident['round']==rec['round'] and ident['mode']==rec['mode'] and ident['case']==rec['case'] and ident['controls']==controls
   assert {k:v['sha256'] for k,v in ident['libraries'].items()}==policy['libraries'] and ident['external_sources']==spec['external_sources']
   if data is None:data=ident['data_sha256']
   assert ident['data_sha256']==data
   for f in ['maps-before.txt','maps-after.txt']:
    text=(d/f).read_text()
    for stem,receipt in ident['libraries'].items():assert {line.split()[-1] for line in text.splitlines() if stem+'.so' in line}=={receipt['path']}
   dot=(d/'graph.dot').read_text();assert dot.count('KERNEL\n')==2*cfg['group'] and 'FillFunctor' not in dot
   cc=json.loads((d/'correctness.json').read_text());assert {(c['phase'],c['index']) for c in cc}=={(p,i) for p in ['initial','changed','final'] for i in range(2*cfg['group'])};ccount+=len(cc)
   assert all(c['finite'] and c['nrms']<=(.0067 if c['label']=='q' else .012) and c['nmax']<=(.20 if c['label']=='q' else .15) for c in cc)
   rows=json.loads((d/'timings.json').read_text());assert len(rows)==(1 if proof else 8) and [v['trial'] for v in rows]==list(range(len(rows)))
   for v in rows:assert v['units']==(cfg['group'] if proof else 200) and v['graph_launches']*cfg['group']==v['units'] and all(math.isfinite(v[f]) and v[f]>0 for f in ['gpu_us','host_us','submit_us'])
   if proof:
    topology_audit((out/(rec['name']+'.log')).read_text(),controls,cfg)
    expected=enabled(spec,rec['mode']) and cfg['operation']=='events' and cfg['group']>1;tr=trace_audit((out/(rec['name']+'.log')).read_text(),expected)
    if expected:assert tr['launches']==4 and tr['packets']==8*cfg['group'] and tr['waits']==8*(cfg['group']-1)
    else:assert tr['launches']==0
   else:
    tcount+=len(rows);vals.setdefault(rec['mode'],{}).setdefault(rec['case'],{})[rec['round']]={f:statistics.median(v[f] for v in rows) for f in ['gpu_us','host_us','submit_us']}
 med={mode:{case:{f:statistics.median(v[f] for v in rounds.values()) for f in ['gpu_us','host_us','submit_us']} for case,rounds in cases.items()} for mode,cases in vals.items()}
 result=dict(passed=True,job=m['job'],phase=m['phase'],revision=m['revision'],fixture_processes=len(m['fixtures']),proof_processes=len(m['proofs']),timing_processes=len(m['runs']),timing_rows=tcount,correctness_rows=ccount,medians=med,round_medians=vals,manifest_sha256=sha(out/'manifest.json'),qualified=False)
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==json.loads(json.dumps(result))
 else:write(out/'summary.json',result)
 print(json.dumps(result),flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--revision',default='v3');ap.add_argument('--phase',choices=['preflight','performance'],default='preflight');ap.add_argument('--audit',action='store_true');a=ap.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 h=json.loads((W/'harness.json').read_text())
 for f,v in h.items():assert sha(W/f)==v
 build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W.parent/'hassan-graph-local-tokens-20260919'/('lib-'+a.revision)
 for f,v in build['libraries'].items():assert sha(lib/f)==v
 out.mkdir(exist_ok=False);spec=json.loads((W/'protocol.json').read_text());spec['sources']=h
 for mode,p in spec['modes'].items():
  if p['lib']=='BUILD':p['lib']=str(lib);p['libraries']={f.removesuffix('.so'):v for f,v in build['libraries'].items()}
 write(out/'spec.json',spec)
 m=dict(complete=False,job=os.environ.get('SLURM_JOB_ID'),revision=a.revision,phase=a.phase,build=build,harness=h,spec_sha256=sha(out/'spec.json'),fixtures=[],proofs=[],runs=[])
 def save():write(out/'manifest.json',m)
 fb=out/'fixtures-bin';fb.mkdir()
 for name,source in [('lane','graph_lane_lifetime.cpp'),('burst','graph_signal_generations.cpp')]:
  subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','--offload-arch=gfx950',str(W/source),'-o',str(fb/name)],check=True)
 m['fixture_build']=hashes(fb);save()
 fs=fixture_plan()
 for mode,cap,kind,fault in fs:
  name=f'fixture-{mode}-q{cap}-{kind}-f{int(fault)}';d=out/name;d.mkdir();extra={'GPU_MAX_HW_QUEUES':str(cap),'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1','LD_DEBUG':'libs','GPU_GRAPH_DIAGNOSTIC_LANE_FAIL_AFTER':str(3 if fault else 0)}
  cmd=[str(fb/kind)]+([str(int(fault))] if kind=='lane' else [])
  print('FIXTURE',name,flush=True)
  with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:p=subprocess.run(cmd,env=env_for(spec['modes'][mode],extra),stdout=stdout,stderr=stderr)
  text=(d/'stderr.log').read_text();rec=dict(name=name,mode=mode,cap=cap,kind=kind,fault=fault,returncode=p.returncode,artifacts=hashes(d));m['fixtures'].append(rec);save();assert p.returncode==0,(name,p.returncode)
  mapped={}
  for stem,expected in spec['modes'][mode]['libraries'].items():
   paths={line.split('calling init:',1)[1].strip() for line in text.splitlines() if 'calling init:' in line and stem+'.so' in line};assert len(paths)==1;path=paths.pop();assert sha(path)==expected;mapped[stem]=dict(path=path,sha256=expected)
  rec['mapped']=mapped;rec['trace']=trace_audit(text,enabled(spec,mode) and cap==4,kind=='burst',fault);save()
 for proof in [True,False]:
  if not proof and a.phase=='preflight':break
  wanted=[(-1,mode,c) for mode,c in proof_plan(spec)] if proof else [(i,mode,c) for i,order in enumerate(spec['orders']) for mode in order for c in spec['cases']]
  for round_id,mode,case in wanted:
   name=('proof' if proof else f'r{round_id}')+'-'+mode+'-'+case;sp=out/'spec.json';extra={}
   if proof:
    ps=copy.deepcopy(spec);ps['modes'][mode]['controls']['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']='1';sp=out/(name+'-spec.json');write(sp,ps);extra={'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1'}
   cmd=[sys.executable,str(W/'benchmark.py'),'--case',case,'--round',str(round_id),'--out',str(out/name),'--spec',str(sp),'--mode',mode]+(['--proof'] if proof else [])
   print('BENCH',name,flush=True)
   with (out/(name+'.log')).open('w') as log:p=subprocess.run(cmd,env=env_for(spec['modes'][mode],extra),stdout=log,stderr=subprocess.STDOUT)
   rec=dict(name=name,mode=mode,case=case,round=round_id,returncode=p.returncode,log_sha256=sha(out/(name+'.log')),artifacts=hashes(out/name));m['proofs' if proof else 'runs'].append(rec);save();assert p.returncode==0,(name,p.returncode)
   if proof:
    cfg=spec['cases'][case];topology_audit((out/(name+'.log')).read_text(),spec['modes'][mode]['controls'],cfg);expected=enabled(spec,mode) and cfg['operation']=='events' and cfg['group']>1
    tr=trace_audit((out/(name+'.log')).read_text(),expected)
    if expected:assert tr['launches']==4 and tr['packets']==8*cfg['group'] and tr['waits']==8*(cfg['group']-1)
    else:assert tr['launches']==0
    print('PROOF',name,tr,flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
