"""Audit all fork/join measurements; summarize process medians without discarding trials."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,re,statistics,sys

def analyze(root):
 m=json.loads((root/'manifest.json').read_text());assert m['complete'] and (root/'COMPLETE').read_text().strip()=='PASS'
 assert hashlib.sha256((root/'benchmark').read_bytes()).hexdigest()==(root/'binary.sha256').read_text().strip()
 for name,digest in m['reference_sha256'].items():assert hashlib.sha256((root/'references'/name).read_bytes()).hexdigest()==digest
 expected_schedules={'serial','parallel','wide'};runs=[];allrows=[];hardware=[]
 for run in m['runs']:
  rows=list(csv.DictReader((root/(run['name']+'.csv')).open()));log=(root/(run['name']+'.log')).read_text()
  match=re.search(r'CUs=(\d+) wave=(\d+) concurrent=(\d+) rate_khz=(\d+) registers=(\d+) shared=(\d+) max_blocks_per_CU=(\d+)',log);assert match
  cu,wave,concurrent,rate,regs,shared,capacity=map(int,match.groups());assert wave==64 and concurrent==1 and capacity>=1
  hardware.append(dict(CUs=cu,wave=wave,registers=regs,shared_bytes=shared,max_blocks_per_CU=capacity))
  heads={cu//4,cu//2,cu} if m['head_divisor']==0 else {cu//m['head_divisor']}
  assert len(rows)==len(heads)*m['repeats']*3
  assert {(int(r['heads']),int(r['trial']),r['schedule']) for r in rows}=={(h,t,s) for h in heads for t in range(m['repeats']) for s in expected_schedules}
  for r in rows:
   assert int(r['tokens_per_partition'])==m['tokens'] and int(r['seed'])==int(r['trial'])%4+1
   assert r['correct']=='1' and float(r['max_abs_error'])<=2e-5
   assert float(r['total_us'])>0 and 0<=float(r['overlap_us'])<=min(float(r['a_span_us']),float(r['b_span_us']))+0.1
   if r['schedule']=='serial':assert float(r['overlap_us'])<=1
   if 'join_after_branches_us' in r:assert float(r['join_after_branches_us'])>=-1
   allrows.append(dict(r,runtime=run['mode'],round=run['round']))
  for h in sorted(heads):
   cells={}
   for schedule in sorted(expected_schedules):
    group=[r for r in rows if int(r['heads'])==h and r['schedule']==schedule]
    columns=['total_us','host_us','a_span_us','b_span_us','overlap_us','span_union_us','a_start_offset_us','b_start_offset_us','join_after_branches_us','join_span_us']
    cell={k:statistics.median(float(r[k]) for r in group) for k in columns if k in group[0]}
    cell.update(n=len(group),min_total_us=min(float(r['total_us']) for r in group),max_total_us=max(float(r['total_us']) for r in group),max_abs_error=max(float(r['max_abs_error']) for r in group),pending_joins=sum(r['join_pending']=='1' for r in group))
    cells[schedule]=cell
   runs.append({'round':run['round'],'runtime':run['mode'],'heads':h,'cells':cells,'parallel_speedup':cells['serial']['total_us']/cells['parallel']['total_us'],'wide_speedup':cells['serial']['total_us']/cells['wide']['total_us']})
 assert all(x==hardware[0] for x in hardware)
 grouped=defaultdict(list)
 for x in runs:grouped[(x['heads'],x['runtime'])].append(x)
 aggregates=[]
 for (h,mode),reps in sorted(grouped.items()):
  aggregates.append({'heads':h,'runtime':mode,'processes':len(reps),'cells':{s:{k:statistics.median(r['cells'][s][k] for r in reps) for k in reps[0]['cells'][s]} for s in expected_schedules},'parallel_speedup':statistics.median(r['parallel_speedup'] for r in reps),'process_parallel_speedups':[r['parallel_speedup'] for r in reps]})
 comparisons=[]
 for h in sorted({x['heads'] for x in runs}):
  for rnd in range(m['rounds']):
   row={r['runtime']:r for r in runs if r['round']==rnd and r['heads']==h}
   comparisons.append({'heads':h,'round':rnd,'native_on_vs_off_parallel_pct':100*(row['on']['cells']['parallel']['total_us']/row['off']['cells']['parallel']['total_us']-1),'native_on_vs_off_serial_pct':100*(row['on']['cells']['serial']['total_us']/row['off']['cells']['serial']['total_us']-1),'native_on_vs_off_wide_pct':100*(row['on']['cells']['wide']['total_us']/row['off']['cells']['wide']['total_us']-1)})
 return {'complete':True,'job':m['job'],'node':m['node'],'processes':len(m['runs']),'measured_operations':len(allrows),'checked_measured_elements':sum(int(r['heads'])*64 for r in allrows),'max_absolute_reference_error':max(float(r['max_abs_error']) for r in allrows),'all_parallel_joins_pending':all(r['join_pending']=='1' for r in allrows if r['schedule']=='parallel'),'hardware':hardware[0],'runs':runs,'aggregates':aggregates,'comparisons':comparisons,'limitations':['Synthetic FP32 attention-like implementation, not tuned production attention.','One GPU allocation, three fresh processes per runtime; repeats within a process are not independent jobs.','Per-CTA timestamps establish kernel envelopes, not exact CU utilization.','Same work can also be exposed in a wider single-stream launch.','CPU reference uses cached bytes generated from an independent double-precision implementation; hashes retained.','All timing samples retained; no clock locking or benchmark tuning after geometry qualification.']}
if __name__=='__main__':print(json.dumps(analyze(Path(sys.argv[1])),indent=2))
