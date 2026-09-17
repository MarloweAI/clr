from pathlib import Path
import csv,json,statistics,collections
import argparse
p=argparse.ArgumentParser();p.add_argument('directory',type=Path);r=p.parse_args().directory;m=json.loads((r/'manifest.json').read_text());assert m['passed']
g=collections.defaultdict(list)
for p in m['processes']:
 rows=list(csv.DictReader((r/(p['tag']+'.csv')).open()))
 for x in rows:
  key=(p['case'],p['queue_cap'])+tuple(x[k] for k in (['config','branches','depth'] if p['case']=='queued_chains' else ['consumers','consumer_delay_us']))
  for metric in (['total_us','host_per_trial_us','branch_span_sum_us','join_gap_sum_us','branch_start_skew_sum_us'] if p['case']=='queued_chains' else ['producer_us','total_us','host_us','resume_gap_us']):
   g[(key,metric,p['mode'],p['round'])].append(float(x[metric]))
med={k:statistics.median(v) for k,v in g.items()};out=[]
for key,metric in sorted({(k[0],k[1]) for k in med}):
 row=dict(case=key,metric=metric)
 for mode in ['stock','off','on','previous']:row[mode]=[med[key,metric,mode,rd] for rd in range(3)]
 row['comparisons']={base:[100*(x/y-1) for x,y in zip(row['on'],row[base])] for base in ['stock','off','previous']}
 row['repeatable_regressions']=[base for base,ds in row['comparisons'].items() if min(ds)>2]
 out.append(row)
headline=[x for x in out if x['metric'] in ['total_us','producer_us','host_us','host_per_trial_us']]
report=dict(rows=out,performance_screen_passed=not any(x['repeatable_regressions'] for x in headline),rule='Fail if on exceeds any control by over 2 percent in every paired round; headline GPU and host totals. Components retained separately.')
(r/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
for row in out:
 if row['metric'] in ['total_us','producer_us']:
  print(row['case'],row['metric'],{k:round(statistics.median(row[k]),2) for k in ['stock','off','on','previous']},'FAIL',row['repeatable_regressions'])
print('Other metric flags:')
for row in out:
 if row['metric'] not in ['total_us','producer_us'] and row['repeatable_regressions']:print(row)
