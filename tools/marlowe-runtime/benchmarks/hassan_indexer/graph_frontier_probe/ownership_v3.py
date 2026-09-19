#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
from preflight import trace,cleanenv
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'] and files(out/'bins')==m['binaries']
 for f,h in m['sources'].items():assert sha(W/f)==h
 assert m['build']==json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text())
 assert [(v['early'],v['mode']) for v in m['runs']]==[(e,k) for e in [0,1] for k in ['stock','off','on']]
 for v in m['runs']:
  d=out/v['name'];assert files(d)==v['files']
  assert {k:r['sha256'] for k,r in v['mapped'].items()}==v['expected_libraries']
  if v['returncode']==0:
   assert trace((d/'stderr.log').read_text())==v['trace'];result=json.loads((d/'stdout.log').read_text());assert result['passed'] and result['checked_values']==4 and result['destroyed_before_sync']
   if v['mode']=='on':assert v['trace']['launches']==2 and v['trace']['chained']==1 and v['trace']['peak']==2 and result['function_update_ms']<100
  else:
   assert v['early']==1 and v['mode']!='on', (v['name'],v['returncode'])
 print(json.dumps({'passed':True,'job':m['job'],'revision':m['revision'],'runs':[{k:v[k] for k in ['mode','early','returncode','trace','result']} for v in m['runs']]}),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--revision',default='v2');p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);bins=out/'bins';bins.mkdir();lib=W/('lib-'+a.revision);build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text())
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 for i,add in enumerate([1,17]):subprocess.run(['/opt/rocm/bin/hipcc','--genco','-O2','--offload-arch=gfx950','-DADDEND='+str(add),str(W/'ownership_module.cpp'),'-o',str(bins/f'module{i}.hsaco')],check=True)
 subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','--offload-arch=gfx950',str(W/'graph_frontier_ownership_v3.cpp'),'-o',str(bins/'ownership')],check=True)
 fs=['ownership_v3.py','ownership_module.cpp','graph_frontier_ownership_v3.cpp','preflight.py','protocol.json'];m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources={f:sha(W/f) for f in fs},binaries=files(bins),runs=[])
 def save():write(out/'manifest.json',m)
 save()
 for early in [0,1]:
  for mode in ['stock','off','on']:
   name=f'e{early}-{mode}';d=out/name;d.mkdir();policy=json.loads((W/'protocol.json').read_text())['modes']['stock' if mode=='stock' else 'local'];controls=policy['controls'];controls.update(GPU_GRAPH_DIAGNOSTIC_FRONTIER=str(int(mode=='on')),GPU_GRAPH_DIAGNOSTIC_LOCAL_SIGNALS='0');env=cleanenv(controls,policy['lib'] if mode=='stock' else lib)
   expected={k+'.so':v for k,v in policy['libraries'].items()} if mode=='stock' else build['libraries']
   with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:r=subprocess.run([str(bins/'ownership'),str(bins/'module0.hsaco'),str(bins/'module1.hsaco'),str(early)],env=env,stdout=stdout,stderr=stderr)
   v=dict(name=name,mode=mode,early=early,returncode=r.returncode,files=files(d),controls=controls,expected_libraries=expected,trace=None,result=None);m['runs'].append(v);save()
   text=(d/'stderr.log').read_text();v['mapped']={}
   for stem,h in expected.items():
    paths={line.split('calling init:',1)[1].strip() for line in text.splitlines() if 'calling init:' in line and stem in line};assert len(paths)==1;path=paths.pop();assert sha(path)==h;v['mapped'][stem]=dict(path=path,sha256=h)
   if r.returncode==0:v['trace']=trace(text);v['result']=json.loads((d/'stdout.log').read_text())
   save();print('OWNERSHIP',name,r.returncode,v['trace'],v['result'],flush=True)
   assert r.returncode==0 or (early==1 and mode!='on'),(name,r.returncode)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
