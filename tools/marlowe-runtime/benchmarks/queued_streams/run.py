#!/usr/bin/env python3
"""Check queued attention and fragmented-producer fanout with exact runtime receipts."""
from pathlib import Path
import argparse, subprocess, os, json, hashlib, csv, time
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidate-lib',type=Path,required=True)
p.add_argument('--previous-lib',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--stock-lib',type=Path,default=Path('/opt/rocm/lib'))
p.add_argument('--compiler',default='/opt/rocm/bin/hipcc')
a=p.parse_args();root=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(exist_ok=False)
assert os.environ.get('SLURM_JOB_ID'), 'Run in an allocated single-GPU environment'
stock=a.stock_lib.resolve();previous=a.previous_lib.resolve();candidate=a.candidate_lib.resolve()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
refs=out/'references';refs.mkdir()
for case in ['queued_chains','fanout']:
 subprocess.run([a.compiler,'-O2','-std=c++17','--offload-arch=gfx950',str(root/(case+'.cpp')),'-o',str(out/case)],check=True)
modes=[('stock',stock,0),('off',candidate,0),('on',candidate,1),('previous',previous,1)]
m=dict(job=os.environ['SLURM_JOB_ID'],node=os.uname().nodename,rounds=3,processes=[],
       source_sha256={str(path.relative_to(root.parent)):sha(path) for path in [root/'queued_chains.cpp',root/'fanout.cpp',root.parent/'attention_stream_chains/stream_chains.cpp']},
       binary_sha256={case:sha(out/case) for case in ['queued_chains','fanout']},
       libraries={mode:{'directory':str(lib),'hip_sha256':sha(lib/'libamdhip64.so'),'hsa_sha256':sha(lib/'libhsa-runtime64.so')} for mode,lib,enabled in modes})
def run_case(case,cap,repeats,tag,lib,enabled,trace=False):
 env=dict(os.environ,GPU_MAX_HW_QUEUES=str(cap),GPU_NATIVE_EVENT_WAIT=str(enabled),GPU_NATIVE_EVENT_TRACE=str(int(trace)),LD_LIBRARY_PATH=f'{lib}:{stock}',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so')
 args=[str(out/case),str(repeats)]+([str(refs)] if case=='queued_chains' else [])
 start=time.monotonic()
 with (out/(tag+'.csv')).open('w') as stdout,(out/(tag+'.log')).open('w') as stderr:
  rc=subprocess.run(args,env=env,stdout=stdout,stderr=stderr,timeout=180).returncode
 rows=list(csv.DictReader((out/(tag+'.csv')).open()));expected=68*repeats if case=='queued_chains' else 6*repeats
 assert rc==0 and len(rows)==expected and all(r['correct']=='1' for r in rows),(tag,rc,len(rows))
 log=(out/(tag+'.log')).read_text()
 for name in ['libamdhip64.so','libhsa-runtime64.so']:
  mapped={Path(line.split()[-1]).resolve() for line in log.splitlines() if line.startswith('LIBRARY ') and name in line}
  assert mapped=={(lib/name).resolve()},(tag,name,mapped)
 return dict(tag=tag,rows=len(rows),hip_sha256=sha(lib/'libamdhip64.so'),elapsed=time.monotonic()-start)
for round in range(3):
 for mode,lib,enabled in modes[round%4:]+modes[:round%4]:
  for case,cap,repeats in [('queued_chains',4,3),('fanout',4,24),('fanout',8,24)]:
   record=run_case(case,cap,repeats,f'r{round}-{mode}-{case}-q{cap}',lib,enabled)
   record.update(round=round,mode=mode,case=case,queue_cap=cap);m['processes'].append(record)
   (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(record['tag'],'PASS',record['rows'],flush=True)
m['passed']=True
m['traces']={}
for case in ['queued_chains','fanout']:
 run_case(case,4,3,case+'-trace',candidate,1,True)
 m['traces'][case]={'native_packets':(out/(case+'-trace.log')).read_text().count('NATIVE_EVENT_PACKET')}
(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
subprocess.run(['python3',str(root/'analyze.py'),str(out)],check=True)
