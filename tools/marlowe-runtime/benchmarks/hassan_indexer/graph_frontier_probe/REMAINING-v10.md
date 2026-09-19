# Expanded v10 holdout gate — job 55818

The distributed-boundary toggle does not introduce a median slowdown above 2% versus identical-byte central mode in these 208 cells. Four cells remain more than 2% slower than stock: three pipeline graphs and one mixed parallel graph. All four also lose to stock with the matched previous v7 runtime. Four other mixed cells lose 2.24–2.49% versus matched v7, while remaining between −0.31% and +0.66% of stock. These are retained regressions, not universal neutrality.

The first phase of job 55818 completed with 96 timing processes and 29,888 retained rows. Four rotated rounds use the exact historical binary, references, shapes, schedules and loop counts. Mapped-library/control and numerical audits pass remotely and on the downloaded artifacts. No instrumentation was enabled.

| Family | Cells | Faster than stock | >2% loss vs stock | Worst vs stock | Worst vs v7 | Worst vs central |
|---|---:|---:|---:|---:|---:|---:|
|attention_fetch|120|73|0|+1.367%|+0.852%|+1.009%|
|fanout_q4|6|3|0|+0.080%|+0.003%|+0.171%|
|fanout_q8|6|3|0|+0.072%|+0.639%|+0.514%|
|mixed|16|10|1|+2.192%|+2.486%|+1.708%|
|pipeline|36|16|3|+3.440%|+1.207%|+1.735%|
|queued|24|17|0|+0.631%|+0.569%|+0.347%|

| Stock-regressing cell, GPU µs | Stock | Matched v7 | V10 central | V10 distributed | Distributed / stock |
|---|---:|---:|---:|---:|---:|
|mixed/matrix-kv/parallel/total/graph|218.057|222.657|225.827|222.837|+2.192%|
|pipeline/h128-l8-miss128/two_streams/total/graph|2168.200|2228.892|2228.412|2224.792|+2.610%|
|pipeline/h32-l32-miss128/two_streams/total/graph|8634.898|8899.106|8899.697|8889.706|+2.951%|
|pipeline/h32-l8-miss32/two_streams/total/graph|1701.693|1759.325|1759.955|1760.235|+3.440%|

The pipeline losses repeat in every round. Their distributed/central changes are −0.16%, −0.11%, and +0.02%, so this matched experiment does not attribute those losses to the new distributed policy. The mixed parallel graph loss varies between −0.50% and +4.83% versus stock; its median is +2.19%, and it is effectively unchanged from matched v7 (+0.08%).

The additional mixed v7 regressions are kv-kv parallel eager, matrix-kv parallel eager, and matrix-kv serial eager/graph. They are not a confirmed distributed-toggle effect: the same-byte contrasts are all below 1.71%. Their cause remains unresolved. No gap investigation, case removal, or workload tuning was performed.

This gate adds attention-fetch, pipeline, mixed compute/copy, queued chains, and fanout at queue caps 4 and 8. It does not establish full-model performance or production readiness. See RESULTS-v10.md for Hassan, expert/KV, attention-dispatch and waiter results.

Manifest SHA256: 133262bf2887ca1e429eaa5af8f9e15b38b4b0f1232af4f931a41bc236ce8739. Exact V10 libraries and build patches are identified in BOUNDARY-v10.md. Audit with `python3 remaining-boundary/run.py --audit --out boundary-remaining-j55818`. All cells and round contrasts are retained in the raw summary; REMAINING-v10-cells.csv provides the complete median comparison.
