import argparse,hashlib,json,math,os,statistics,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
write=lambda p,v:Path(p).write_text(json.dumps(v,indent=2)+'\n')
hashes=lambda d:{str(p.relative_to(d)):sha(p) for p in d.rglob('*') if p.is_file()}
def audit(out):
 spec=json.loads((R/'spec.json').read_text());h=json.loads((R/'harness.json').read_text());m=json.loads((out/'manifest.json').read_text());assert m['complete'] and m['harness']==h and all(sha(R/f)==v for f,v in h.items())
 assert sha(out/'launcher.so')==m['helper_sha256'];data=None;med={};rows_total=checks_total=0
 assert [(x['round'],x['case']) for x in m['runs']]==[(r,c) for r,o in enumerate(spec['orders']) for c in o]
 assert {x['case'] for x in m['proofs']}==set(spec['cases'])
 for proof,runs in [(False,m['runs']),(True,m['proofs'])]:
  for rec in runs:
   d=out/rec['name'];assert rec['returncode']==0 and hashes(d)==rec['artifacts'] and sha(out/(rec['name']+'.log'))==rec['log_sha256'] and (d/'COMPLETE').read_text()=='PASS\n';i=json.loads((d/'identity.json').read_text());cfg=spec['cases'][rec['case']];controls=spec['controls']|{'GPU_STREAMOPS_CP_WAIT':str(cfg['cp'])}
   if proof:controls.update(AMD_LOG_LEVEL='4',AMD_LOG_MASK='256')
   assert i['config']==cfg and i['case']==rec['case'] and i['round']==rec['round'] and i['proof']==proof and i['controls']==controls and i['helper_sha256']==m['helper_sha256'] and i['external_sources']==spec['external_sources']
   assert {k:v['sha256'] for k,v in i['libraries'].items()}==spec['libraries']
   if data is None:data=i['data_sha256']
   assert i['data_sha256']==data and i['streams'][0]!=i['streams'][1]
   dots=list(d.glob('graph-*.dot'));assert len(dots)==(1 if cfg['mode']==0 else 2)
   text='\n'.join(x.read_text() for x in dots);assert 'FillFunctor' not in text and text.count('KERNEL\n')==2*cfg['group'] and text.count('(64,4,1),(128,1,1)')==text.count('(2,12,1),(128,1,1)')==cfg['group']
   cc=json.loads((d/'correctness.json').read_text());assert len(cc)==6*cfg['group'] and {(x['phase'],x['index']) for x in cc}=={(p,j) for p in ['changed','initial','final'] for j in range(2*cfg['group'])}
   assert all(x['finite'] and x['nrms']<=(.0067 if x['label']=='q' else .012) and x['nmax']<=(.20 if x['label']=='q' else .15) for x in cc);checks_total+=len(cc)
   rows=json.loads((d/'timings.json').read_text());assert len(rows)==(1 if proof else 8) and {x['trial'] for x in rows}==set(range(len(rows)))
   for row in rows:assert row['units']==(cfg['group'] if proof else 200) and row['launches']*cfg['group']==row['units'] and all(math.isfinite(row[f]) and row[f]>0 for f in ['gpu_us','submit_us','host_us'])
   count=2+(2 if proof else 9)*rows[0]['launches'];assert i['generations'][0]==(count if cfg['mode'] in (2,3) else 0) and i['generations'][1:]==([count,count] if cfg['mode']==3 else [0,0])
   if proof:
    log=(out/(rec['name']+'.log')).read_text();expected=2*count if cfg['mode']==3 and cfg['cp']==0 else 0;assert log.count('Waiting for value:')==expected,(rec['name'],log.count('Waiting for value:'),expected)
   else:
    rows_total+=len(rows);med.setdefault(rec['case'],{})[rec['round']]={f:statistics.median(x[f] for x in rows) for f in ['gpu_us','submit_us','host_us']}
 result=dict(passed=True,job=m['job'],timing_processes=len(m['runs']),timing_rows=rows_total,proof_processes=len(m['proofs']),correctness_rows=checks_total,medians={c:{f:statistics.median(x[f] for x in rounds.values()) for f in ['gpu_us','submit_us','host_us']} for c,rounds in med.items()},round_medians=med,manifest_sha256=sha(out/'manifest.json'))
 if (out/'summary.json').exists():assert json.loads(json.dumps(result))==json.loads((out/'summary.json').read_text())
 else:write(out/'summary.json',result)
 print(json.dumps(result),flush=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();out=a.out
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);spec=json.loads((R/'spec.json').read_text());h=json.loads((R/'harness.json').read_text());assert all(sha(R/f)==v for f,v in h.items())
 subprocess.run(['/opt/rocm/bin/hipcc','-O2','-std=c++17','-shared','-fPIC',str(R/'launcher.cpp'),'-o',str(R/'launcher.so')],check=True)
 (out/'launcher.so').write_bytes((R/'launcher.so').read_bytes());m=dict(job=os.environ['SLURM_JOB_ID'],complete=False,harness=h,helper_sha256=sha(R/'launcher.so'),runs=[],proofs=[]);save=lambda:write(out/'manifest.json',m);save()
 def run(c,r,proof):
  name=f'proof-{c}' if proof else f'r{r}-{c}';rec=dict(name=name,case=c,round=r,started=time.time());(m['proofs'] if proof else m['runs']).append(rec);save();print('START',name,flush=True)
  e={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','HASSAN_','FLYDSL_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG','HIP_VISIBLE_DEVICES')};e.update(spec['controls'],GPU_STREAMOPS_CP_WAIT=str(spec['cases'][c]['cp']),LD_LIBRARY_PATH='/opt/rocm/lib',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so')
  if proof:e.update(AMD_LOG_LEVEL='4',AMD_LOG_MASK='256')
  with (out/(name+'.log')).open('x') as f:p=subprocess.run([sys.executable,str(R/'benchmark.py'),'--case',c,'--round',str(r),'--out',str(out/name)]+(['--proof'] if proof else []),env=e,stdout=f,stderr=subprocess.STDOUT)
  rec.update(returncode=p.returncode,elapsed_s=time.time()-rec['started']);save();assert p.returncode==0,name
  rec.update(artifacts=hashes(out/name),log_sha256=sha(out/(name+'.log')));save();print('PASS',name,flush=True)
 for c in spec['cases']:run(c,0,True)
 for r,order in enumerate(spec['orders']):
  for c in order:run(c,r,False)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
