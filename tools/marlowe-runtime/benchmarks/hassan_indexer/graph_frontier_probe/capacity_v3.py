#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
from preflight import trace,cleanenv
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
CASES=[('burst',2),('burst',8),('burst',32),('boundary',8),('boundary',1024),('idle',8),('hostfed',2)]
def inspect(v,d):
 text=(d/'stderr.log').read_text();t=trace(text);assert t['launches']>0 and t['peak']<=v['cap'],(v['name'],t)
 caps=[dict(re.findall(r'(\w+)=(\S+)',s)) for s in re.findall(r'GRAPH_FRONTIER_CAPACITY [^\r\n]*',text)]
 if v['kind'] not in ['idle'] and v['cap']<64:assert caps
 assert all(int(x['size'])==int(x['limit'])==v['cap'] and x['action']=='fallback' for x in caps)
 result=json.loads((d/'stdout.log').read_text());assert result['passed']
 if v['kind']=='hostfed':assert result['checked_values']==16 and result['launches']==8 and result['watchdog_rescued'] is False and result['submit_ms']<1000
 if v['kind']=='idle':
  assert result['checked_values']==2 and result['destroy_ms']<100 and t['launches']==1
  before=text.index('FRONTIER_IDLE phase=before_destroy');end=text.index('FRONTIER_IDLE phase=idle_end');release=text.index('GRAPH_FRONTIER_RELEASE ')
  assert before<release<end,'Idle destruction did not retire without a later HIP operation'
 return dict(trace=t,capacity_fallbacks=len(caps),destroy_notifications=[int(v) for v in re.findall(r'GRAPH_FRONTIER_DESTROY [^\r\n]* notifications=(\d+)',text)],result=result)
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'] and files(out/'bins')==m['binaries']
 for f,h in m['sources'].items():assert sha(W/f)==h
 assert m['build']==json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text())
 assert [(v['kind'],v['cap']) for v in m['runs']]==CASES
 for v in m['runs']:
  d=out/v['name'];assert v['returncode']==0 and files(d)==v['files'];assert inspect(v,d)==v['observed']
  assert {k:r['sha256'] for k,r in v['mapped'].items()}==m['build']['libraries']
 print(json.dumps(dict(passed=True,job=m['job'],revision=m['revision'],runs=[dict(name=v['name'],**v['observed']) for v in m['runs']])),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--revision',default='v7');p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);bins=out/'bins';bins.mkdir();build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W/('lib-'+a.revision)
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 sources=['capacity_v3.py','preflight.py','protocol.json','graph_signal_generations.cpp','graph_frontier_boundaries.cpp','graph_frontier_idle.cpp','graph_frontier_host_fed_v2.cpp']
 for kind,source in [('burst','graph_signal_generations.cpp'),('boundary','graph_frontier_boundaries.cpp'),('idle','graph_frontier_idle.cpp'),('hostfed','graph_frontier_host_fed_v2.cpp')]:subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','-pthread','--offload-arch=gfx950',str(W/source),'-o',str(bins/kind)],check=True)
 m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources={f:sha(W/f) for f in sources},binaries=files(bins),runs=[]);save=lambda:write(out/'manifest.json',m);save()
 for kind,cap in CASES:
  name=f'{kind}-cap{cap}';d=out/name;d.mkdir();print('CAPACITY',name,flush=True)
  controls=json.loads((W/'protocol.json').read_text())['modes']['local']['controls'];controls.update(GPU_GRAPH_DIAGNOSTIC_FRONTIER_MAX_GENERATIONS=str(cap),DEBUG_CLR_MAX_BATCH_SIZE='1000',GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS='0');env=cleanenv(controls,lib)
  with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:r=subprocess.run([str(bins/kind)],env=env,stdout=stdout,stderr=stderr)
  v=dict(name=name,kind=kind,cap=cap,controls=controls,returncode=r.returncode,files=files(d));m['runs'].append(v);save();assert r.returncode==0,(name,r.returncode)
  text=(d/'stderr.log').read_text();v['mapped']={}
  for stem,h in build['libraries'].items():
   paths={line.split('calling init:',1)[1].strip() for line in text.splitlines() if 'calling init:' in line and stem in line};assert len(paths)==1;path=paths.pop();assert sha(path)==h;v['mapped'][stem]=dict(path=path,sha256=h)
  v['observed']=inspect(v,d);save();print('OBSERVED',v['observed'],flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
