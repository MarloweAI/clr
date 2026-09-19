# Expanded v7 microbenchmark holdouts — job 55732

The expanded gate finds four median regressions against stock above 2%: three pipeline cells (+2.66% to +3.51%) and one mixed graph (+3.29%). The matched previous v4 candidate has the same behavior; no cell is more than 2% slower than v4. This qualifies neither v7 nor v4 as universally neutral against stock.

Node2, one GPU, four rotated rounds, 96 processes and 29,888 timing rows across 208 cells. Exact historical executables, references, shapes, loop counts and schedules were reused from the frozen fused-bridge-broad suite. Runtime tracing was off. Remote and downloaded local audits pass; every trial is retained.

| Family | Cells | Faster than stock | >2% slower than stock | Worst vs stock | Worst vs v4 |
|---|---:|---:|---:|---:|---:|
|attention_fetch|120|77|0|+1.205%|+0.622%|
|fanout_q4|6|3|0|+0.082%|+0.569%|
|fanout_q8|6|3|0|+0.076%|+0.425%|
|mixed|16|12|1|+3.292%|+0.178%|
|pipeline|36|16|3|+3.513%|+0.574%|
|queued|24|6|0|+0.996%|+1.516%|

| Regressing cell (GPU µs) | Stock | Matched v4 | v7 off | v7 on | On/stock | On/off |
|---|---:|---:|---:|---:|---:|---:|
|mixed/matrix-kv/parallel/total/graph|214.437|224.267|208.967|221.497|+3.292%|+5.996%|
|pipeline/h128-l8-miss128/two_streams/total/graph|2168.210|2227.051|2225.392|2225.892|+2.660%|+0.022%|
|pipeline/h32-l32-miss128/two_streams/total/graph|8626.066|8894.386|8902.546|8898.615|+3.160%|-0.044%|
|pipeline/h32-l8-miss32/two_streams/total/graph|1700.932|1759.395|1760.135|1760.684|+3.513%|+0.031%|

The three pipeline regressions repeat in all four rounds (approximately +2.55% to +3.66%). Their v7 on/off difference is below 0.8%, so these measurements do not implicate the private graph-frontier path. The mixed total graph has more variation (+1.15%, +8.03%, +1.48%, +3.55% versus stock) and remains slower than the feature-off runtime. No internal mechanism is established by this gate.

This adds attention-fetch, pipeline, mixed compute/copy, queued chains, and fanout at queue caps 4 and 8 to the existing expert/KV and original waiter/attention-dispatch coverage. It does not establish exhaustive coverage of every historical fixture, full-model behavior, or production readiness.

The v7 HIP is e692e09467765565866387bd4918468b1cbb43459c7c2c3fd2b1242031713ff0; HSA is 2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12. V4 and stock are measured in the same allocation. All cell/round results are in remaining-j55732/summary.json and REMAINING-v7-cells.csv. Manifest SHA256: 7214893c89b43d5ac05f7b0b6e12714798bbdac448d1cb4098f3c73fc154c991.

Audit: `python3 remaining-v7/run.py --audit --out remaining-j55732`. Complete raw artifacts remain in this iteration directory and its cluster mirror. Hassan gains and waiter-overhead removal are reported separately; this additional evidence limits any broader claim of neutrality.
