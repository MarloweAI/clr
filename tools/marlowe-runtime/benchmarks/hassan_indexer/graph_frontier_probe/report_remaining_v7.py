from pathlib import Path
from collections import defaultdict
import json,csv
G=Path(__file__).resolve().parent;s=json.loads((G/'remaining-j55732/summary.json').read_text());groups=defaultdict(list)
for c in s['cells']:groups[c['family']].append(c)
lines=['# Expanded v7 microbenchmark holdouts — job 55732','', 'The expanded gate finds four median regressions against stock above 2%: three pipeline cells (+2.66% to +3.51%) and one mixed graph (+3.29%). The matched previous v4 candidate has the same behavior; no cell is more than 2% slower than v4. This qualifies neither v7 nor v4 as universally neutral against stock.','', 'Node2, one GPU, four rotated rounds, 96 processes and 29,888 timing rows across 208 cells. Exact historical executables, references, shapes, loop counts and schedules were reused from the frozen fused-bridge-broad suite. Runtime tracing was off. Remote and downloaded local audits pass; every trial is retained.','', '| Family | Cells | Faster than stock | >2% slower than stock | Worst vs stock | Worst vs v4 |','|---|---:|---:|---:|---:|---:|']
for family,cells in groups.items():
 lines.append(f"|{family}|{len(cells)}|{sum(c['contrasts']['stock']['percent']<0 for c in cells)}|{sum(c['contrasts']['stock']['percent']>2 for c in cells)}|{max(c['contrasts']['stock']['percent'] for c in cells):+.3f}%|{max(c['contrasts']['previous']['percent'] for c in cells):+.3f}%|")
lines+=['','| Regressing cell (GPU µs) | Stock | Matched v4 | v7 off | v7 on | On/stock | On/off |','|---|---:|---:|---:|---:|---:|---:|']
for c in s['cells']:
 if c['contrasts']['stock']['percent']<=2:continue
 m=c['medians'];f=c['metric'];lines.append('|'+c['family']+'/'+ '/'.join(c['cell'])+'|'+ '|'.join(f"{m[k][f]:.3f}" for k in ['stock','previous','off','local'])+f"|{c['contrasts']['stock']['percent']:+.3f}%|{c['contrasts']['off']['percent']:+.3f}%|")
lines+=['', 'The three pipeline regressions repeat in all four rounds (approximately +2.55% to +3.66%). Their v7 on/off difference is below 0.8%, so these measurements do not implicate the private graph-frontier path. The mixed total graph has more variation (+1.15%, +8.03%, +1.48%, +3.55% versus stock) and remains slower than the feature-off runtime. No internal mechanism is established by this gate.','', 'This adds attention-fetch, pipeline, mixed compute/copy, queued chains, and fanout at queue caps 4 and 8 to the existing expert/KV and original waiter/attention-dispatch coverage. It does not establish exhaustive coverage of every historical fixture, full-model behavior, or production readiness.','', 'The v7 HIP is e692e09467765565866387bd4918468b1cbb43459c7c2c3fd2b1242031713ff0; HSA is 2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12. V4 and stock are measured in the same allocation. All cell/round results are in remaining-j55732/summary.json and REMAINING-v7-cells.csv. Manifest SHA256: '+s['manifest_sha256']+'.','', 'Audit: `python3 remaining-v7/run.py --audit --out remaining-j55732`. Complete raw artifacts remain in this iteration directory and its cluster mirror. Hassan gains and waiter-overhead removal are reported separately; this additional evidence limits any broader claim of neutrality.']
(G/'REMAINING-v7.md').write_text('\n'.join(lines)+'\n')
with (G/'REMAINING-v7-cells.csv').open('w') as out:
 w=csv.writer(out);w.writerow(['family','cell','metric','stock','previous_v4','v7_off','v7_on','on_vs_stock_percent','on_vs_previous_percent','on_vs_off_percent','stock_round_percent'])
 for c in s['cells']:
  f=c['metric'];w.writerow([c['family'],'/'.join(c['cell']),f,*[c['medians'][m][f] for m in ['stock','previous','off','local']],*[c['contrasts'][m]['percent'] for m in ['stock','previous','off']],json.dumps(c['contrasts']['stock']['round_percent'])])
print('\n'.join(lines[:13]))
