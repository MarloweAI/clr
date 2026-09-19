#!/usr/bin/env python3
import csv,hashlib,json,math,os,statistics,struct,sys
from pathlib import Path
from collections import Counter,defaultdict
p=Path(sys.argv[1]);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
rows=list(csv.DictReader((p/'trials.csv').open()));meta=json.loads((p/'device.json').read_text());hz=meta['timestamp_hz'];assert hz>0 and meta['agent']=='gfx950'
want=Counter((str(r),str(t),case,mode,str(i),str(o)) for r in range(2) for t in range(3) for case in ['ready','delayed','chain32','chain2048'] for mode in ['none','barrier','nop_barrier','native_barrier'] for i in range(2) for o in range(2))
assert Counter(tuple(x[k] for k in ['round','trial','case','mode','independent','observer']) for x in rows)==want
assert [int(x['id']) for x in rows]==list(range(384))
groups=defaultdict(list);negative=[];probes=[]
for row in rows:
 assert row['correct']=='1';n=int(row['producer_count']);ni=int(row['independent_count']);obs=int(row['observer']);raw=(p/row['trace']).read_bytes();assert len(raw)==48*(n+1+ni+obs)
 samples=list(struct.iter_unpack('<6Q',raw));assert all(0<x[0]<=x[1] for x in samples)
 assert all(samples[i][0]>=samples[i-1][1] for i in range(1,n))
 assert all(samples[i][1]-samples[i][0]>=int(row['delay_ticks']) for i in range(n))
 assert all(samples[i][0]>=samples[i-1][1] for i in range(n+2,n+1+ni))
 if row['mode']!='none':assert samples[n][4]==0
 metrics={'producer_span_us':(samples[n-1][1]-samples[0][0])*1e6/hz,'consumer_after_producer_sample_us':(samples[n][0]-samples[n-1][1])*1e6/hz}
 if ni:
  metrics['independent_span_us']=(samples[n+ni][1]-samples[n+1][0])*1e6/hz
  metrics['independent_median_period_us']=statistics.median(samples[i][0]-samples[i-1][0] for i in range(n+2,n+1+ni))*1e6/hz
  # Relative starts are same device clock, not host/device clock subtraction.
  metrics['independent_start_after_producer_start_us']=(samples[n+1][0]-samples[0][0])*1e6/hz
 if obs:
  s=samples[-1];assert s[4]==0 and s[3] and s[5]
  if s[2]:
   assert s[0]<=s[2]<=s[3]<=s[1] and s[5]>=2
   metrics['readiness_bracket_us']=(s[3]-s[2])*1e6/hz
   metrics['consumer_after_ready_lower_us']=(samples[n][0]-s[3])*1e6/hz
   metrics['consumer_after_ready_upper_us']=(samples[n][0]-s[2])*1e6/hz
   if row['mode']!='none' and metrics['consumer_after_ready_upper_us']<0:negative.append(row['id'])
  else:metrics['observer_initially_ready']=1
 groups[(row['case'],row['mode'],row['independent'],row['observer'])].append(metrics)
 probes.append(dict(id=row['id'],trace=row['trace'],sha256=sha(p/row['trace']),metrics=metrics))
summary=[]
for key,rr in sorted(groups.items()):
 fields=set().union(*(x.keys() for x in rr));values={f:[x[f] for x in rr if f in x] for f in fields}
 summary.append(dict(case=key[0],mode=key[1],independent=int(key[2]),observer=int(key[3]),trials=len(rr),metrics={f:dict(median=statistics.median(v),min=min(v),max=max(v),samples=len(v)) for f,v in values.items()}))
result=dict(audit_passed=True,pilot_only=True,firmware_bug_established=False,trials=len(rows),groups=len(summary),timestamp_hz=hz,readiness_cross_queue_order_anomalies=negative,summary=summary,traces=probes)
out=p/'analysis.json'
if '--verify' in sys.argv:assert result==json.loads(out.read_text())
else:out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['summary','traces']}))
for x in summary:
 if x['independent']==1 and x['observer']==1:print(json.dumps(x))
