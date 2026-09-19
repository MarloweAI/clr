#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def trace(text):
 active={};begins=ends=releases=chains=0;peak=0
 for rec in re.findall(r'GRAPH_FRONTIER_[A-Z_]+ [^\r\n]*',text):
  name=rec.split()[0];v=dict(re.findall(r'(\w+)=(\S+)',rec));key=(v.get('graph'),v.get('serial'))
  if name=='GRAPH_FRONTIER_BEGIN':
   assert key not in active and v['generation'] not in [x['generation'] for x in active.values()]
   active[key]=v;begins+=1;chains+=int(v['chained']);peak=max(peak,len(active))
  elif name=='GRAPH_FRONTIER_END':assert key in active;ends+=1
  elif name=='GRAPH_FRONTIER_RELEASE':
   assert key in active and active[key]['generation']==v['generation'] and v['recycled']=='1';del active[key];releases+=1
 assert not active and begins==ends==releases
 return dict(launches=begins,chained=chains,peak=peak)
def cleanenv(controls,lib):
 e={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HSA_','HASSAN_','FLYDSL_')) and k not in ['LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG','HIP_VISIBLE_DEVICES']}
 e.update(controls);e.update(LD_LIBRARY_PATH=str(lib)+':/opt/rocm/lib',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LD_DEBUG='libs',GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE='1');return e
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'];assert files(out/'bins')==m['binaries']
 for f,h in m['sources'].items():assert sha(W/f)==h,f
 b=json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text());assert b==m['build']
 for item in m['runs']:
  d=out/item['name'];assert files(d)==item['files'] and item['returncode']==0
  t=trace((d/'stderr.log').read_text());assert t==item['trace']
  if item['frontier'] and item['cap']==4:assert t['launches']>0
  else:assert t['launches']==0
  for stem,h in b['libraries'].items():assert item['mapped'][stem]['sha256']==h
 assert len(m['runs'])==9
 print(json.dumps({'passed':True,'job':m['job'],'processes':len(m['runs']),'traces':[x['trace'] for x in m['runs']]}),flush=True)
def main():
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);a.add_argument('--revision',default='v1');a.add_argument('--audit',action='store_true');a=a.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W/('lib-'+a.revision)
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 src=['preflight_boundary_v8.py','protocol-v8-tests.json','graph_lane_lifetime.cpp','graph_signal_generations.cpp','graph_frontier_boundaries.cpp']
 m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources={f:sha(W/f) for f in src},runs=[])
 def save():write(out/'manifest.json',m)
 save();bins=out/'bins';bins.mkdir()
 for name,source in [('lane','graph_lane_lifetime.cpp'),('burst','graph_signal_generations.cpp'),('boundary','graph_frontier_boundaries.cpp')]:subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','-pthread','--offload-arch=gfx950',str(W/source),'-o',str(bins/name)],check=True)
 m['binaries']=files(bins);save();protocol=json.loads((W/'protocol-v8-tests.json').read_text())
 cases=[(0,4,'lane',0,1000),(0,4,'boundary',0,1000),(1,1,'lane',0,1000),(1,4,'lane',0,1000),(1,4,'lane',3,1000),(1,4,'burst',0,1000),(1,4,'boundary',0,1000),(1,4,'boundary',0,8),(1,4,'burst',0,8)]
 for frontier,cap,kind,fault,limit in cases:
  name=f'f{frontier}-q{cap}-{kind}-fault{fault}-batch{limit}';d=out/name;d.mkdir();print('FIXTURE',name,flush=True)
  controls=dict(protocol['modes']['local']['controls']);controls.update(GPU_GRAPH_DIAGNOSTIC_FRONTIER=str(frontier),GPU_GRAPH_DIAGNOSTIC_LOCAL_SIGNALS='0',GPU_MAX_HW_QUEUES=str(cap),GPU_GRAPH_DIAGNOSTIC_LANE_FAIL_AFTER=str(fault),DEBUG_CLR_MAX_BATCH_SIZE=str(limit));env=cleanenv(controls,lib)
  with (d/'stdout.log').open('w') as stdout,(d/'stderr.log').open('w') as stderr:p=subprocess.run([str(bins/kind)]+([str(int(bool(fault)))] if kind=='lane' else []),env=env,stdout=stdout,stderr=stderr)
  item=dict(name=name,frontier=frontier,cap=cap,kind=kind,fault=fault,batch_limit=limit,controls=controls,returncode=p.returncode,files=files(d));m['runs'].append(item);save();assert p.returncode==0,(name,p.returncode)
  text=(d/'stderr.log').read_text();item['trace']=trace(text);item['mapped']={}
  for stem,h in build['libraries'].items():
   paths={line.split('calling init:',1)[1].strip() for line in text.splitlines() if 'calling init:' in line and stem in line};assert len(paths)==1;path=paths.pop();assert sha(path)==h;item['mapped'][stem]=dict(path=path,sha256=h)
  print('TRACE',item['trace'],flush=True);save()
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
