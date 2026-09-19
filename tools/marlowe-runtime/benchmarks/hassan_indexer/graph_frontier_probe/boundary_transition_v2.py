#!/usr/bin/env python3
"""Functional regression: distributed graph -> ordinary raw single-root graph."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys
from preflight import trace, cleanenv
from boundary_control_child import audit_receipt
from boundary_trace_audit import inspect as boundary_inspect
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def cases():return [(v,d,k,b) for v,d,k in [('v8',0,0),('v8',1,0),('v9',0,0),('v9',1,0),('v9',1,1)] for b in (0,1)]
def inspect(item,d):
 text=(d/'stderr.log').read_text(); audit_receipt(text,item['controls'])
 t=trace(text);assert t['launches']==1 and t['chained']==0,t
 result=json.loads((d/'stdout.log').read_text());assert result['delayed_branch']==item['delayed_branch']
 assert result['expected']==[17,19,146] and result['values'][:2]==[17,19],result
 assert result['passed']==(result['values']==result['expected'])
 assert item['returncode']==(0 if result['passed'] else 3)
 if item['revision']!='v8' or not item['distributed']:assert result['passed'],(item['name'],result)
 b=boundary_inspect(text) if item['distributed'] else None
 if b:assert b['launches']==1 and b['sealed_tails']==2
 return dict(trace=t,boundary=b,result=result)
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'] and files(out/'bins')==m['binaries']
 for f,h in m['sources'].items():assert sha(W/f)==h,f
 assert [(v['revision'],v['distributed'],v['kernel_retire'],v['delayed_branch']) for v in m['runs']]==cases()
 for rev,b in m['builds'].items():assert b==json.loads((W/f'runtime-build-{rev}.json').read_text())
 failed=[]
 for v in m['runs']:
  d=out/v['name'];assert files(d)==v['files'];assert inspect(v,d)==v['observed']
  assert {k:r['sha256'] for k,r in v['mapped'].items()}==m['builds'][v['revision']]['libraries']
  if not v['observed']['result']['passed']:failed.append(v['name'])
 assert failed and all(name.startswith('v8-d1-k0') for name in failed),failed
 print(json.dumps(dict(passed=True,job=m['job'],processes=len(m['runs']),old_bug_reproduced=failed)),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);bins=out/'bins';bins.mkdir()
 builds={rev:json.loads((W/f'runtime-build-{rev}.json').read_text()) for rev in ['v8','v9']}
 for rev,b in builds.items():
  for f,h in b['libraries'].items():assert sha(W/f'lib-{rev}'/f)==h
 subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','--offload-arch=gfx950',str(W/'graph_boundary_to_single_v2.cpp'),'-o',str(bins/'transition')],check=True)
 sources=['boundary_transition_v2.py','boundary_control_child.py','boundary_trace_audit.py','preflight.py','protocol-v8-tests.json','graph_boundary_to_single_v2.cpp']
 m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],builds=builds,sources={f:sha(W/f) for f in sources},binaries=files(bins),runs=[]);save=lambda:write(out/'manifest.json',m);save()
 for rev,distributed,kernel_retire,branch in cases():
  name=f'{rev}-d{distributed}-k{kernel_retire}-delay{branch}';d=out/name;d.mkdir();print('TRANSITION',name,flush=True)
  controls=json.loads((W/'protocol-v8-tests.json').read_text())['modes']['local']['controls'];controls.update(GPU_GRAPH_DIAGNOSTIC_FRONTIER_DISTRIBUTED=str(distributed),GPU_GRAPH_DIAGNOSTIC_KERNEL_RETIRE=str(kernel_retire),GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE='1');env=cleanenv(controls,W/f'lib-{rev}')
  with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:r=subprocess.run([sys.executable,str(W/'boundary_control_child.py'),str(bins/'transition'),str(branch)],env=env,stdout=stdout,stderr=stderr)
  v=dict(name=name,revision=rev,distributed=distributed,kernel_retire=kernel_retire,delayed_branch=branch,controls=controls,returncode=r.returncode,files=files(d));m['runs'].append(v);save();v['mapped']={}
  text=(d/'stderr.log').read_text()
  for stem,h in builds[rev]['libraries'].items():
   paths={line.split('calling init:',1)[1].strip() for line in text.splitlines() if 'calling init:' in line and stem in line};assert len(paths)==1;path=paths.pop();assert sha(path)==h;v['mapped'][stem]=dict(path=path,sha256=h)
  v['observed']=inspect(v,d);save();print('OBSERVED',v['observed'],flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
