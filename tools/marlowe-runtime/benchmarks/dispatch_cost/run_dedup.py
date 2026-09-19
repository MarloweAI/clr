"""Duplicate-native-prewait ablation with source and disabled-path bridges. Sequential processes; no trial trimming."""
import argparse
from collections import Counter, defaultdict
import csv, hashlib, json, math, os
from pathlib import Path
import re, statistics, subprocess, time

KEYS=('heads','tokens','launches','form','schedule','trial')
MODES=('stock','prior_off','off','prior_guarded','guarded','prior_t8','threshold8','dedup8','prior_relaxed','relaxed','dedup_relaxed')
FIELDS=('total_us','host_us','submit_us','a_span_us','b_span_us','handoff_us','overlap_us','b_end_minus_a_us')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cells(repeats):
 return Counter(tuple(map(str,(h,t,k,f,s,r)))
  for h,t in ((256,256),(256,1024),(64,8192)) for k in (1,4,16,256)
  if h!=64 or k==1 for f in ('eager','graph') for s in ('serial','parallel','wide')
  if s!='wide' or k==1 for r in range(repeats))

def audit_process(out,name,libs,repeats,controls):
 log=(out/f'{name}.log').read_text();mapped={}
 for stem,lib in libs.items():
  paths={Path(line.split()[-1]) for line in log.splitlines() if line.startswith('LIBRARY ') and stem in line}
  assert len(paths)==1,(name,stem,paths)
  p=paths.pop();assert sha(p)==sha(lib),(name,p,lib)
  mapped[stem]={'path':str(p),'sha256':sha(p)}
 receipt=f"CONTROLS wait={controls['GPU_NATIVE_EVENT_WAIT']} relaxed={controls['GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST']} minimum={controls['GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES']} trace={controls['GPU_NATIVE_EVENT_TRACE']} queue_cap={controls['GPU_MAX_HW_QUEUES']}"
 assert receipt in log,(name,'control receipt')
 with (out/f'{name}.csv').open() as f:rows=list(csv.DictReader(f))
 assert Counter(tuple(row[k] for k in KEYS) for row in rows)==cells(repeats),(name,'coverage')
 assert all(row['correct']=='1' and float(row['max_abs_error'])<=2e-5 for row in rows),name
 for row in rows:
  assert all(math.isfinite(float(row[k])) for k in FIELDS),name
  assert all(float(row[k])>0 for k in ('total_us','host_us','submit_us','a_span_us','b_span_us')),name
  assert float(row['handoff_us'])>=-1 and float(row['overlap_us'])>=0,name
 return rows,mapped,log

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate-lib',type=Path,required=True);p.add_argument('--released-lib',type=Path,required=True)
 p.add_argument('--rounds',type=int,default=3);p.add_argument('--repeats',type=int,default=8)
 a=p.parse_args();assert os.environ.get('SLURM_JOB_ID') and a.rounds>=3 and a.repeats>=4
 src=Path(__file__).resolve().parent/'attention_dispatch.cpp';out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 refs=out/'references';refs.mkdir()
 paths={m:Path('/opt/rocm/lib') if m=='stock' else a.released_lib if m.startswith('prior_') else a.candidate_lib for m in MODES}
 libs={m:{s:path/(s+'.so') for s in ('libamdhip64','libhsa-runtime64')} for m,path in paths.items()}
 manifest={'job':os.environ['SLURM_JOB_ID'],'node':os.uname().nodename,'source_sha256':sha(src),'runtime_hashes':{m:{s:sha(p) for s,p in ll.items()} for m,ll in libs.items()},'rounds':a.rounds,'repeats':a.repeats,'runs':[],'complete':False}
 def save(): (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 save()
 with (out/'build.log').open('w') as log:
  subprocess.run(['/opt/rocm/bin/hipcc','-O3','-std=c++17','--offload-arch=gfx950',str(src),'-o',str(out/'benchmark')],stdout=log,stderr=subprocess.STDOUT,check=True)
 manifest['binary_sha256']=sha(out/'benchmark');save()
 aggregate=[]
 def execute(name,mode,repeats,trace=False,queue_cap=4):
  controls={'GPU_NATIVE_EVENT_WAIT':str(int(mode not in ('stock','prior_off','off'))),'GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST':str(int(mode.endswith('relaxed'))),
   'GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES':str(8 if mode in ('prior_t8','threshold8','dedup8') else 256),'GPU_NATIVE_EVENT_DIAGNOSTIC_DEDUP':str(int(mode in ('dedup8','dedup_relaxed'))),'GPU_NATIVE_EVENT_TRACE':str(int(trace)),'GPU_MAX_HW_QUEUES':str(queue_cap)}
  env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_NATIVE_EVENT_','GPU_GRAPH_DIAGNOSTIC_')) and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','LD_DEBUG')}
  env.update(controls,LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LD_LIBRARY_PATH=f'{paths[mode]}:/opt/rocm/lib')
  run={'name':name,'mode':mode,'controls':controls,'timing_eligible':not trace,'started':time.time()};manifest['runs'].append(run);save()
  with (out/f'{name}.csv').open('w') as stdout,(out/f'{name}.log').open('w') as stderr:
   r=subprocess.run([str(out/'benchmark'),str(repeats),str(refs)],env=env,stdout=stdout,stderr=stderr)
  run.update(returncode=r.returncode,elapsed_s=time.time()-run['started']);save();assert r.returncode==0,(name,r.returncode)
  rows,mapped,log=audit_process(out,name,libs[mode],repeats,controls)
  run.update(rows=len(rows),mapped=mapped)
  if trace:
   reasons=Counter();emissions=[]
   for line in log.splitlines():
    if not line.startswith('NATIVE_COST '):continue
    record=dict(re.findall(r'(\w+)=([^ ]+)',line));reasons[record['reason']]+=1
    assert record['minimum']==controls['GPU_NATIVE_EVENT_DIAGNOSTIC_MIN_DISPATCHES']
    assert record['relaxed']==controls['GPU_NATIVE_EVENT_DIAGNOSTIC_RELAX_COST']
    assert record['dedup']==controls['GPU_NATIVE_EVENT_DIAGNOSTIC_DEDUP']
    assert int(record['instance'])>0 and record['virtual'].startswith('0x')
    if record['reason']=='emit':
     assert record['producer']!=record['consumer'] and record['producer']!=str(2**64-1)
     assert int(record['generation'])>0;emissions.append(record)
   run.update(admission_reasons=dict(reasons),emitted=len(emissions))
   assert reasons,(name,'no compiled policy receipts')
  save();print(name,'PASS',len(rows),'rows',flush=True)
  return rows
 for rnd in range(a.rounds):
  order=MODES[rnd*2%len(MODES):]+MODES[:rnd*2%len(MODES)]
  for mode in order:
   rows=execute(f'r{rnd}-{mode}',mode,a.repeats)
   groups=defaultdict(list)
   for row in rows:groups[tuple(row[k] for k in KEYS[:-1])].append(row)
   for cell,rr in groups.items():
    aggregate.append({'round':rnd,'mode':mode,'cell':cell,'n':len(rr),'metrics':{f:statistics.median(float(row[f]) for row in rr) for f in FIELDS},'side_ready_fraction':sum(int(row['side_ready_before_main_end']) for row in rr)/len(rr)})
  (out/'summary.json').write_text(json.dumps(aggregate,indent=2)+'\n')
 for mode in ('guarded','threshold8','dedup8','relaxed','dedup_relaxed'):
  execute(f'trace-{mode}',mode,1,trace=True)
 execute('trace-dedup-q1','dedup_relaxed',1,trace=True,queue_cap=1)
 manifest.update(complete=True,reference_sha256={p.name:sha(p) for p in refs.glob('*.bin')})
 save();(out/'COMPLETE').write_text('PASS\n')

if __name__=='__main__':main()
