"""One GPU, sequential fresh processes; preserve every result and verify mapped runtimes."""
from pathlib import Path
import csv,hashlib,json,os,subprocess,sys,time
source=Path(__file__).resolve().parent
out=Path(os.environ['ASC_OUT']);out.mkdir(parents=True,exist_ok=False)
package=Path('/workspace/home/sasha/amd-runtime-production/rebuild-41146/dist/marlowe-hip-7.2.4-native-wait-v7-rc4')
assert os.environ.get('SLURM_JOB_ID')
subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=source,stdout=(out/'source-verify.log').open('w'),check=True)
with (out/'build.log').open('w') as log:
 subprocess.run(['/opt/rocm/bin/hipcc','-O3','-std=c++17','--offload-arch=gfx950','stream_chains.cpp','-o',str(out/'benchmark')],cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'binary.sha256').write_text(hashlib.sha256((out/'benchmark').read_bytes()).hexdigest()+'\n')
refs=out/'references';refs.mkdir(exist_ok=True)
expected={'stock':{'libamdhip64':'f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac','libhsa-runtime64':'b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4'},'off':{'libamdhip64':'102086f70978c776e89e4fc0cea16b6e0afea39d24ea9c95b6c7ab1c0e492cdd','libhsa-runtime64':'b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4'}}
expected['on']=expected['off']
manifest={'job':os.environ['SLURM_JOB_ID'],'node':os.uname().nodename,'source':str(source),'repeats':int(os.environ.get('ASC_REPEATS','16')),'quick':int(os.environ.get('ASC_QUICK','0')),'rounds':int(os.environ.get('ASC_ROUNDS','3')),'mode_orders':[],'runs':[]}
(out/'environment.json').write_text(json.dumps({k:v for k,v in os.environ.items() if k.startswith(('ASC_','SLURM_')) or k in ['ROCR_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES']},indent=2)+'\n')
for round in range(manifest['rounds']):
 order=[['stock','off','on'],['off','on','stock'],['on','stock','off']][round%3];manifest['mode_orders'].append(order)
 for mode in order:
  name=f'r{round}-{mode}';env=dict(os.environ,ASC_RUNTIME_MODE=mode,GPU_NATIVE_EVENT_WAIT='1' if mode=='on' else '0');env.pop('LD_PRELOAD',None)
  env['LD_LIBRARY_PATH']='/opt/rocm/lib'
  if mode!='stock':
   env['LD_LIBRARY_PATH']=str(package/'lib')+':/opt/rocm/lib'
   env['LD_PRELOAD']='libamdhip64.so:libhsa-runtime64.so'
  start=time.time()
  with (out/f'{name}.csv').open('w') as stdout,(out/f'{name}.log').open('w') as stderr:
   result=subprocess.run([str(out/'benchmark'),str(manifest['repeats']),str(refs),str(manifest['quick'])],env=env,stdout=stdout,stderr=stderr,timeout=600)
  log=(out/f'{name}.log').read_text();mapped={}
  for stem,digest in expected[mode].items():
   paths={Path(line.split()[-1]) for line in log.splitlines() if line.startswith('LIBRARY ') and stem in line}
   assert len(paths)==1,(name,stem,paths)
   path=paths.pop();actual=hashlib.sha256(path.read_bytes()).hexdigest();assert actual==digest,(name,path,actual)
   mapped[stem]={'path':str(path),'sha256':actual}
  assert result.returncode==0,(name,result.returncode,log[-1000:])
  rows=list(csv.DictReader((out/f'{name}.csv').open()));assert rows and all(row['correct']=='1' for row in rows)
  manifest['runs'].append({'name':name,'round':round,'mode':mode,'returncode':result.returncode,'elapsed_s':time.time()-start,'rows':len(rows),'mapped':mapped})
  (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  print(f'{name} complete: {len(rows)} measured correct outputs',flush=True)
manifest['complete']=True
manifest['reference_sha256']={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in refs.glob('*.bin')}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'COMPLETE').write_text('PASS\n')
