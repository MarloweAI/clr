#!/usr/bin/env python3
"""Untimed matched central/distributed packet intervals, original Hassan kernels."""
from pathlib import Path
import argparse,copy,hashlib,json,math,os,statistics,subprocess,sys
from preflight import cleanenv
from timestamps_analysis_v2 import analyze
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
CASES=[(mode,case) for mode in ['central','distributed'] for case in ['events-g1','events-g50']]
def inspect(out,v,spec,build):
 d=out/v['name'];assert v['returncode']==0 and files(d)==v['files'] and sha(out/(v['name']+'.log'))==v['log_sha256'] and (d/'COMPLETE').read_text()=='PASS\n'
 ident=json.loads((d/'identity.json').read_text());cfg=spec['cases'][v['case']];p=spec['modes'][v['mode']];group=cfg['group']
 assert ident['controls']==p['controls'] and ident['config']==cfg and ident['mode']==v['mode'] and ident['external_sources']==spec['external_sources']
 assert {k+'.so':x['sha256'] for k,x in ident['libraries'].items()}==build['libraries']
 for f in ['maps-before.txt','maps-after.txt']:
  text=(d/f).read_text()
  for stem,x in ident['libraries'].items():assert {line.split()[-1] for line in text.splitlines() if stem+'.so' in line}=={x['path']}
 checks=json.loads((d/'correctness.json').read_text());assert {(x['phase'],x['index']) for x in checks}=={(p,i) for p in ['initial','changed','final'] for i in range(2*group)}
 assert all(x['finite'] and math.isfinite(x['nrms']) and x['nrms']<=(.0067 if x['label']=='q' else .012) and x['nmax']<=(.20 if x['label']=='q' else .15) for x in checks)
 log=(out/(v['name']+'.log')).read_text();assert 'GRAPH_FRONTIER_BEGIN ' not in log
 summary,raw=analyze(log,(d/'graph.dot').read_text(),group)
 start=3+200//group;timed=[x for x in raw if x['serial']>=start];first=[x for x in timed if x['pair']==0];later=[x for x in timed if x['pair']>0]
 perlaunch={serial:[x for x in timed if x['serial']==serial] for serial in sorted({x['serial'] for x in timed})};gaps=[]
 for serial,rr in perlaunch.items():
  if serial>start and (serial-start)%(200//group)!=0:
   prev=perlaunch[serial-1];gap=(rr[0]['start']-prev[-1]['end'])*1e6/rr[0]['frequency'];assert gap>=0;gaps.append(gap)
 summary.update(first_pair_skew_us=statistics.median(x['start_skew_us'] for x in first),first_pair_span_us=statistics.median(x['span_us'] for x in first),later_pair_skew_us=statistics.median(x['start_skew_us'] for x in later) if later else None,cross_launch_gap_us=statistics.median(gaps),correctness_checks=len(checks))
 return summary,raw,ident['data_sha256']
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'];spec=json.loads((out/'spec.json').read_text());assert sha(out/'spec.json')==m['spec_sha256']
 for f,h in m['sources'].items():assert sha(W/f)==h,f
 assert spec['sources']==m['sources'] and m['build']==json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text())
 assert [(v['mode'],v['case']) for v in m['runs']]==CASES
 data=None
 for v in m['runs']:
  summary,raw,d=inspect(out,v,spec,m['build']);assert summary==v['summary'] and json.loads((out/(v['name']+'-packets.json')).read_text())==raw
  if data is None:data=d
  assert data==d
 result=dict(passed=True,job=m['job'],revision=m['revision'],timing_eligible=False,qualified=False,manifest_sha256=sha(out/'manifest.json'),cases={v['name']:v['summary'] for v in m['runs']})
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==result
 else:write(out/'summary.json',result)
 print(json.dumps(result),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--revision',default='v10');p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W/('lib-'+a.revision)
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 spec=json.loads((W/'protocol-boundary.json').read_text());sources=json.loads((W/'harness-boundary.json').read_text())
 for f in ['timestamps_boundary.py','timestamps_analysis_v2.py','timestamps.py']:sources[f]=sha(W/f)
 spec['sources']=sources
 for mode in ['central','distributed']:
  policy=spec['modes'][mode];policy['lib']=str(lib);policy['libraries']={k.removesuffix('.so'):h for k,h in build['libraries'].items()};policy['controls'].update(GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS='1',GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE='0')
 write(out/'spec.json',spec);m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources=sources,spec_sha256=sha(out/'spec.json'),runs=[]);save=lambda:write(out/'manifest.json',m);save()
 for mode,case in CASES:
  name=mode+'-'+case;policy=spec['modes'][mode];env=cleanenv(policy['controls'],lib);env.pop('LD_DEBUG',None);env['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']='0';print('DISPATCH',name,flush=True)
  with (out/(name+'.log')).open('w') as log:r=subprocess.run([sys.executable,str(W/'benchmark.py'),'--case',case,'--round','0','--out',str(out/name),'--spec',str(out/'spec.json'),'--mode',mode],env=env,stdout=log,stderr=subprocess.STDOUT)
  v=dict(name=name,mode=mode,case=case,returncode=r.returncode,files=files(out/name),log_sha256=sha(out/(name+'.log')));m['runs'].append(v);save()
  summary,raw,_=inspect(out,v,spec,build);v['summary']=summary;write(out/(name+'-packets.json'),raw);save();print('OBSERVED',summary,flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
