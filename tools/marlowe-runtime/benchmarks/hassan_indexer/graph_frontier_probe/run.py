#!/usr/bin/env python3
from pathlib import Path
import argparse,copy,hashlib,json,math,os,statistics,subprocess,sys
from preflight import trace,cleanenv
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete'];spec=json.loads((out/'spec.json').read_text());assert sha(out/'spec.json')==m['spec_sha256']
 for f,h in m['sources'].items():assert sha(W/f)==h
 assert spec['sources']==m['sources'];protocol=json.loads((W/'protocol.json').read_text());assert spec['cases']==protocol['cases'] and spec['orders']==protocol['orders']
 build=json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text());assert build==m['build']
 for mode,p in spec['modes'].items():
  assert p['controls']==protocol['modes'][mode]['controls']
  if mode=='stock':assert p==protocol['modes']['stock']
  else:assert p['libraries']=={k.removesuffix('.so'):h for k,h in build['libraries'].items()} and p['lib'].endswith('/hassan-graph-frontier-20260919/lib-'+m['revision'])
 wanted=[(True,-1,mode,case) for mode in ['off','local'] for case in spec['cases']]
 wanted += [(False,r,mode,case) for r,order in enumerate(spec['orders']) for mode in order for case in spec['cases']]
 assert [(x['proof'],x['round'],x['mode'],x['case']) for x in m['runs']]==wanted
 data=None;values={};count=checks=0
 for item in m['runs']:
  d=out/item['name'];assert item['returncode']==0 and item['files']==files(d) and sha(out/(item['name']+'.log'))==item['log_sha256'];assert (d/'COMPLETE').read_text()=='PASS\n'
  ident=json.loads((d/'identity.json').read_text());cfg=spec['cases'][item['case']];policy=spec['modes'][item['mode']];controls=policy['controls']|({'GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE':'1'} if item['proof'] else {})
  assert ident['config']==cfg and ident['controls']==controls and ident['proof']==item['proof'] and ident['round']==item['round'] and ident['mode']==item['mode'] and ident['case']==item['case']
  assert {k:v['sha256'] for k,v in ident['libraries'].items()}==policy['libraries'] and ident['external_sources']==spec['external_sources']
  if data is None:data=ident['data_sha256']
  assert ident['data_sha256']==data
  for maps in ['maps-before.txt','maps-after.txt']:
   text=(d/maps).read_text()
   for stem,v in ident['libraries'].items():assert {line.split()[-1] for line in text.splitlines() if stem+'.so' in line}=={v['path']}
  dot=(d/'graph.dot').read_text();assert dot.count('KERNEL\n')==2*cfg['group'] and 'FillFunctor' not in dot
  cc=json.loads((d/'correctness.json').read_text());assert {(c['phase'],c['index']) for c in cc}=={(p,i) for p in ['initial','changed','final'] for i in range(2*cfg['group'])};checks+=len(cc)
  assert all(c['finite'] and c['nrms']<=(.0067 if c['label']=='q' else .012) and c['nmax']<=(.20 if c['label']=='q' else .15) for c in cc)
  rows=json.loads((d/'timings.json').read_text());assert len(rows)==(1 if item['proof'] else 8)
  for row in rows:assert row['units']==(cfg['group'] if item['proof'] else 200) and row['graph_launches']*cfg['group']==row['units'] and all(math.isfinite(row[k]) and row[k]>0 for k in ['gpu_us','host_us','submit_us'])
  if item['proof']:
   t=trace((out/(item['name']+'.log')).read_text());assert t==item['trace']
   if item['mode']=='local' and cfg['operation']=='events':assert t['launches']==4
   if item['mode']=='off':assert t['launches']==0
  else:
   count+=len(rows);values.setdefault(item['mode'],{}).setdefault(item['case'],{})[item['round']]={k:statistics.median(row[k] for row in rows) for k in ['gpu_us','host_us','submit_us']}
 medians={mode:{case:{k:statistics.median(v[k] for v in rounds.values()) for k in ['gpu_us','host_us','submit_us']} for case,rounds in cases.items()} for mode,cases in values.items()}
 result=dict(passed=True,job=m['job'],revision=m['revision'],timing_rows=count,correctness_checks=checks,medians=medians,round_medians=values,manifest_sha256=sha(out/'manifest.json'),qualified=False)
 if (out/'summary.json').exists():assert json.loads((out/'summary.json').read_text())==json.loads(json.dumps(result))
 else:write(out/'summary.json',result)
 print(json.dumps(result),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--revision',default='v1');ap.add_argument('--audit',action='store_true');a=ap.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);spec=json.loads((W/'protocol.json').read_text());sources=json.loads((W/'harness.json').read_text());spec['sources']=sources
 for f,h in sources.items():assert sha(W/f)==h
 build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W/('lib-'+a.revision)
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 for mode,p in spec['modes'].items():
  if mode!='stock':p['lib']=str(lib);p['libraries']={k.removesuffix('.so'):v for k,v in build['libraries'].items()}
 write(out/'spec.json',spec);m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources=sources,spec_sha256=sha(out/'spec.json'),runs=[])
 def save():write(out/'manifest.json',m)
 save();wanted=[(True,-1,mode,case) for mode in ['off','local'] for case in spec['cases']]+[(False,r,mode,case) for r,order in enumerate(spec['orders']) for mode in order for case in spec['cases']]
 for proof,r,mode,case in wanted:
  name=('proof' if proof else 'r'+str(r))+'-'+mode+'-'+case;sp=out/'spec.json';policy=copy.deepcopy(spec['modes'][mode]);env=cleanenv(policy['controls'],policy['lib']);env.pop('LD_DEBUG',None);env['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']='1' if proof else '0'
  if proof:
   ps=copy.deepcopy(spec);ps['modes'][mode]['controls']['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']='1';sp=out/(name+'-spec.json');write(sp,ps)
  cmd=[sys.executable,str(W/'benchmark.py'),'--case',case,'--round',str(r),'--out',str(out/name),'--spec',str(sp),'--mode',mode]+(['--proof'] if proof else [])
  print('BENCH',name,flush=True)
  with (out/(name+'.log')).open('w') as log:p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  item=dict(name=name,proof=proof,round=r,mode=mode,case=case,returncode=p.returncode,files=files(out/name),log_sha256=sha(out/(name+'.log')));m['runs'].append(item);save();assert p.returncode==0,(name,p.returncode)
  if proof:
   item['trace']=trace((out/(name+'.log')).read_text());save()
   if mode=='local' and spec['cases'][case]['operation']=='events':assert item['trace']['launches']==4
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
