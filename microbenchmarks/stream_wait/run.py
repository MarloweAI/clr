#!/usr/bin/env python3
"""Run unchanged workload kernels with stock, candidate off, and candidate on."""
import argparse,csv,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LIBS=('libamdhip64.so','libhsa-runtime64.so')
CASES=('waiter','attention_fork_join','attention_stream_chains','attention_fetch','pipeline','experts','mixed','grouped_prefetch','hassan')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def env_for(mode,lib):
 env={k:v for k,v in os.environ.items() if not k.startswith(('GPU_','DEBUG_HIP_','AMD_LOG_','ROC_AQL_','LLM_','AFJ_','ASC_','MARLOWE_RUNTIME_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','LD_DEBUG','ROCP_TOOL_LIB','ROCPROFILER_TOOL_LIBRARIES')}
 controls={'AMD_DIRECT_DISPATCH':'1','GPU_NATIVE_EVENT_WAIT':str(int(mode=='on')),'GPU_GRAPH_NODE_COUNT_PLACEMENT':str(int(mode=='on')),'GPU_NATIVE_EVENT_TRACE':'0','GPU_MAX_HW_QUEUES':'4','GPU_STREAMOPS_CP_WAIT':'0'}
 env.update(controls,LD_LIBRARY_PATH=str(lib)+':/opt/rocm/lib',LD_PRELOAD='libamdhip64.so:libhsa-runtime64.so',LLM_RUNTIME_MODE=mode,AFJ_RUNTIME_MODE=mode,ASC_RUNTIME_MODE=mode)
 return env,controls

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--candidate-lib',type=Path,required=True);p.add_argument('--stock-lib',type=Path,default=Path('/opt/rocm/lib'))
 p.add_argument('--bin',type=Path);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--cases',nargs='+',choices=CASES,default=list(CASES));p.add_argument('--rounds',type=int,default=3)
 a=p.parse_args();assert a.rounds>=3 and os.environ.get('SLURM_JOB_ID'),'Use >=3 fresh-process rounds inside a one-GPU allocation'
 if any(c!='hassan' for c in a.cases):assert a.bin is not None
 a.output=a.output.resolve();a.output.mkdir(exist_ok=False);refs=a.output/'references';refs.mkdir()
 libs={'stock':a.stock_lib.resolve(),'off':a.candidate_lib.resolve(),'on':a.candidate_lib.resolve()}
 policy={mode:dict(lib=str(lib),libraries={n.removesuffix('.so'):sha(lib/n) for n in LIBS},controls=env_for(mode,lib)[1]) for mode,lib in libs.items()}
 source_hashes={str(f.relative_to(ROOT)):sha(f) for f in ROOT.rglob('*') if f.is_file() and '__pycache__' not in str(f)}
 manifest={'job':os.environ['SLURM_JOB_ID'],'node':os.environ.get('SLURMD_NODENAME'),'policy':policy,'sources':source_hashes,'rounds':a.rounds,'cases':a.cases,'runs':[],'complete':False}
 if a.bin:manifest['binaries']={name:sha(a.bin/name) for name in ['waiter','attention_fork_join','attention_stream_chains','llm_streams']}
 def save():write(a.output/'manifest.json',manifest)
 save()
 hs=json.loads((ROOT/'hassan/workload.json').read_text())|{'modes':policy,'sources':{f.name:sha(f) for f in (ROOT/'hassan').iterdir() if f.is_file()}}
 write(a.output/'hassan-spec.json',hs)
 modes=('stock','off','on');coverage={};data=None
 for round_id in range(a.rounds):
  for mode in modes[round_id%3:]+modes[:round_id%3]:
   for case in a.cases:
    subcases=list(hs['cases']) if case=='hassan' else [case]
    for subcase in subcases:
     tag=f'r{round_id}-{mode}-{subcase}';env,controls=env_for(mode,libs[mode])
     env.update(LLM_TRIALS='12',LLM_REFERENCE_DIR=str(refs),LLM_GROUP_DEPTH='1')
     if case=='hassan':cmd=[sys.executable,str(ROOT/'hassan/benchmark.py'),'--case',subcase,'--round',str(round_id),'--out',str(a.output/tag),'--spec',str(a.output/'hassan-spec.json'),'--mode',mode]
     else:
      binary=case if case in ('waiter','attention_fork_join','attention_stream_chains') else 'llm_streams'
      cmd=[str((a.bin/binary).resolve())]
      if case=='attention_fork_join':cmd+=['8192','24',str(refs),'0']
      elif case=='attention_stream_chains':cmd+=['16',str(refs),'0']
      elif binary=='llm_streams':cmd+=[case]
     rec={'tag':tag,'round':round_id,'mode':mode,'case':case,'subcase':subcase,'controls':controls,'command':cmd,'start':time.time()};manifest['runs'].append(rec);save();print('START',tag,flush=True)
     with (a.output/(tag+'.csv')).open('x') as out,(a.output/(tag+'.log')).open('x') as log:
      proc=subprocess.Popen(cmd,env=env,stdout=out,stderr=log);rec['pid']=proc.pid;save()
      while True:
       try:rc=proc.wait(timeout=600);break
       except subprocess.TimeoutExpired:print('INSPECT',tag,'still running; no automatic cancellation',flush=True)
     rec.update(returncode=rc,elapsed_s=time.time()-rec['start']);save();assert rc==0,(tag,rc)
     if case=='hassan':
      d=a.output/tag;assert (d/'COMPLETE').read_text()=='PASS\n';ident=json.loads((d/'identity.json').read_text())
      assert ident['controls']==controls and {k:v['sha256'] for k,v in ident['libraries'].items()}==policy[mode]['libraries']
      if data is None:data=ident['data_sha256']
      assert ident['data_sha256']==data
      timings=json.loads((d/'timings.json').read_text());assert len(timings)==8
      checks=json.loads((d/'correctness.json').read_text());assert len(checks)==6*hs['cases'][subcase]['group']
      assert all(x['finite'] and x['nrms']<=(.0067 if x['label']=='q' else .012) and x['nmax']<=(.20 if x['label']=='q' else .15) for x in checks)
      rec.update(rows=len(timings),checks=len(checks),artifacts={f.name:sha(f) for f in d.iterdir() if f.is_file()})
     else:
      rows=list(csv.DictReader((a.output/(tag+'.csv')).open()));assert rows and all(x['correct']=='1' for x in rows),(tag,'correctness')
      keys=[{k:v for k,v in row.items() if k in ('benchmark','config','schedule','phase','submission','trial','block','case','heads','tokens_per_partition','total_tokens','stages','branches','seed')} for row in rows]
      if case not in coverage:coverage[case]=keys
      assert keys==coverage[case],(tag,'sample coverage or order')
      log=(a.output/(tag+'.log')).read_text();mapped={}
      for stem in LIBS:
       paths={Path(x).resolve() for x in re.findall(r'(/[^\s]*'+re.escape(stem)+r'[^\s]*)',log)}
       assert paths and {sha(f) for f in paths}=={policy[mode]['libraries'][stem.removesuffix('.so')]},(tag,stem,paths)
       mapped[stem]=[str(f) for f in sorted(paths)]
      rec.update(rows=len(rows),mapped=mapped)
     rec['stdout_sha256']=sha(a.output/(tag+'.csv'));rec['stderr_sha256']=sha(a.output/(tag+'.log'));save();print('DONE',tag,rec['rows'],flush=True)
 manifest['references']={f.name:sha(f) for f in refs.iterdir() if f.is_file()};manifest['complete']=True;save();(a.output/'COMPLETE').write_text('PASS: all requested processes, identities and numerical checks. No production qualification implied.\n')
if __name__=='__main__':main()
