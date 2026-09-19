#!/usr/bin/env python3
from pathlib import Path
import argparse,copy,hashlib,json,os,re,statistics,subprocess,sys
from preflight import cleanenv
W=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def analyze(log,case):
 groups={}
 for rec in re.findall(r'GRAPH_FRONTIER_DISPATCH [^\r\n]*',log):
  fields,name=rec.split(' kernel=',1);v=dict(re.findall(r'(\w+)=(\S+)',fields));assert v['valid']=='1' and int(v['end'])>int(v['start']) and int(v['frequency'])>0 and v['kernels']=='1'
  key=(v['graph'],int(v['serial']));segment=int(v['segment']);v.update(kernel=name,segment=segment);assert segment not in groups.setdefault(key,{});groups[key][segment]=v
 assert groups
 totals=[];overlaps=[];durations={};lanes=set();raw=[]
 for key,segments in sorted(groups.items(),key=lambda x:x[0][1]):
  ordered=sorted(segments.values(),key=lambda x:x['segment']);assert len(ordered)==(2 if case=='events-g1' else 100)
  freq={int(x['frequency']) for x in ordered};assert len(freq)==1;scale=1e6/freq.pop()
  for i in range(0,len(ordered),2):
   pair=ordered[i:i+2];assert len({x['physical'] for x in pair})==2
   names={x['kernel'] for x in pair};assert len(names)==2;lanes.update(x['physical'] for x in pair)
   start=[int(x['start']) for x in pair];end=[int(x['end']) for x in pair];overlap=max(0,min(end)-max(start))*scale;span=(max(end)-min(start))*scale
   overlaps.append(overlap);totals.append(span)
   for x in pair:durations.setdefault(x['kernel'],[]).append((int(x['end'])-int(x['start']))*scale)
   raw.append(dict(graph=key[0],serial=key[1],pair=i//2,overlap_us=overlap,span_us=span,kernels=pair))
 result=dict(graphs=len(groups),pairs=len(raw),physical_queues=len(lanes),overlap_pairs=sum(x>0 for x in overlaps),overlap_us_median=statistics.median(overlaps),overlap_us_min=min(overlaps),overlap_us_max=max(overlaps),span_us_median=statistics.median(totals),kernel_duration_us_median={k:statistics.median(v) for k,v in durations.items()})
 return result,raw

def audit(out):
 m=json.loads((out/'manifest.json').read_text());assert m['complete']
 for f,h in m['sources'].items():assert sha(W/f)==h
 assert m['build']==json.loads((W/('runtime-build-'+m['revision']+'.json')).read_text())
 assert [x['case'] for x in m['runs']]==['events-g1','events-g50']
 for v in m['runs']:
  d=out/v['case'];assert v['returncode']==0 and files(d)==v['files'] and sha(out/(v['case']+'.log'))==v['log_sha256'];assert (d/'COMPLETE').read_text()=='PASS\n'
  ident=json.loads((d/'identity.json').read_text());assert {k+'.so':x['sha256'] for k,x in ident['libraries'].items()}==m['build']['libraries'] and ident['controls']['GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS']=='1' and ident['controls']['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']=='0'
  summary,raw=analyze((out/(v['case']+'.log')).read_text(),v['case']);assert v['summary']==summary and json.loads((out/(v['case']+'-packets.json')).read_text())==raw
  assert summary['graphs']==(1802 if v['case']=='events-g1' else 38)
 print(json.dumps({'passed':True,'job':m['job'],'revision':m['revision'],'timing_eligible':False,'cases':{v['case']:v['summary'] for v in m['runs']}}),flush=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--revision',default='v4');ap.add_argument('--audit',action='store_true');a=ap.parse_args();out=a.out.resolve()
 if a.audit:audit(out);return
 out.mkdir(exist_ok=False);build=json.loads((W/('runtime-build-'+a.revision+'.json')).read_text());lib=W/('lib-'+a.revision)
 for f,h in build['libraries'].items():assert sha(lib/f)==h
 spec=json.loads((W/'protocol.json').read_text());sources=json.loads((W/'harness.json').read_text());sources['timestamps.py']=sha(W/'timestamps.py');spec['sources']=sources
 p=spec['modes']['local'];p['lib']=str(lib);p['libraries']={k.removesuffix('.so'):h for k,h in build['libraries'].items()};p['controls'].update(GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS='1',GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE='0')
 write(out/'spec.json',spec);m=dict(complete=False,job=os.environ['SLURM_JOB_ID'],revision=a.revision,build=build,sources=sources,runs=[])
 def save():write(out/'manifest.json',m)
 save()
 for case in ['events-g1','events-g50']:
  env=cleanenv(p['controls'],lib);env.pop('LD_DEBUG',None);env['GPU_GRAPH_DIAGNOSTIC_QUEUE_TRACE']='0';print('TIMESTAMPS',case,flush=True)
  cmd=[sys.executable,str(W/'benchmark.py'),'--case',case,'--round','0','--out',str(out/case),'--spec',str(out/'spec.json'),'--mode','local']
  with (out/(case+'.log')).open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  v=dict(case=case,returncode=r.returncode,files=files(out/case),log_sha256=sha(out/(case+'.log')));m['runs'].append(v);save();assert r.returncode==0,(case,r.returncode)
  summary,raw=analyze((out/(case+'.log')).read_text(),case);v['summary']=summary;write(out/(case+'-packets.json'),raw);save();print('OBSERVED',summary,flush=True)
 m['complete']=True;save();audit(out);(out/'COMPLETE').write_text('PASS\n')
if __name__=='__main__':main()
