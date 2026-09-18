# Graph placement versus submission order — job 50925

2026-09-18, node2, one GPU, root-owned standalone submission/wait/audit.
Slurm completed0:0. Strict audit passes90 timing processes/19,200 correctness
rows,9 separate trace processes/960 rows and240 wide graph-completion observations.
No samples discarded. Six permutations balance the three same-byte interventions
for position/predecessor; stock and prior-byte bridges rotate separately.

New HIP459949c05bc2fc0ca2b584931d7aa09d98b3cc30903d19401a989453473de435,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
Base cab5670 plus patch64d0b8a87a6428392a4f2146dde134844133d6ad086087c3811479f1eb7d7fcf.
Build50920; earlier build50915 had a truncated trace queue-ID format, was retained
unused, and contributed no timing. All new modes use admission24 and SIDEWAIT0.
Previous bytes are HIP1db69; no application/workload source changed.

Microseconds, medians of six process medians:

| Workload | Stock | Prior admission24 | New baseline24 | Coupled length priority | Enqueue-only priority |
|---|---:|---:|---:|---:|---:|
| Matrix + KV parallel graph | 218.068 | 219.768 | 218.367 | 219.547 | 217.748 |
| Grouped25,32 layers,prefetch on | 11616.966 | 11474.829 | 11469.752 | 11001.813 | 11469.370 |
| Grouped25,64 layers,prefetch on | 23250.885 | 22906.190 | 22905.244 | 21833.980 | 22921.363 |
| Grouped25,32 layers,prefetch off | 11549.491 | 10968.803 | 10970.724 | 10950.243 | 10969.754 |
| Four experts,b16 balanced,graph | 232.918 | 151.965 | 151.995 | 152.645 | 152.265 |

Submission-only priority does not retain the grouped benefit:32/64 prefetch-on
changes −0.003%/+0.070% versus same-byte baseline. Coupled priority improves
4.08%/4.68%, with every paired round faster. The old/new baseline bridge is under
0.05% in these two cells. The enqueue-only candidate therefore does not advance
as a performance improvement even though no row loses>2% in all six rounds.

Mixed coupled priority is+0.540% versus baseline (rounds+2.520,+1.550,+0.967,
+0.839,+0.750,−1.886%); enqueue-only is−0.284% (one round+2.191%). These measurements
do not uniformly reproduce the earlier50851 combined-policy loss, and do not
prove universal neutrality or erase that independent result.

The separate mapping auditor proves that baseline and enqueue-only retain logical
assignment and physical queue equivalence across levels and graphs. Stable sort
actually changes490 grouped segment positions and2 mixed positions; experts have
no priority changes. Coupled and enqueue-only have the exact same traced segment
submission sequence, while their assignments differ. Thus the grouped gain depends
on changed placement in this comparison, not merely ordering host submissions.
This does not establish that placement alone without that order is sufficient.

For example, a grouped26-node continuation moves from a side stream to launch,
while a1-node branch moves to the side. Mixed instead swaps a2-node branch from
launch to side and a4-node branch onto launch. Node count does not estimate kernel
cost or hardware-resource pressure. Grouped aggregate native emissions are4473
baseline,4097 coupled,4473 enqueue-only. Mixed emits none. Counts are traced/setup
aggregates, not per-packet timings or proof of the saving mechanism.

The priority vector is copied and sorted at scheduling time, with stable ties;
stream assignment uses the baseline vector. No hot-replay sorting/allocation was
added. Graph cache lifetime was reviewed through clone/instantiate, recursive
children, fallback and parameter updates. The240 completion observations verify
launch-stream completion before a device-wide drain. These diagnostic bytes have
not passed the full lifecycle/PyTorch holdouts or C1 and are not production-qualified.

Next architecture review concerns dependency-aware placement: preserve continuity
of dependent work without using own-node-count as a duration estimate. Any rule
must retain the grouped gain and respect mixed/experts/queue-sharing holdouts.
Do not advance SIDEWAIT-only (50883 rejected it), or the neutral enqueue-only
candidate, to a full-model grid.

Full raw artifacts: graph-enqueue-j50925/{manifest.json,audit.json,mapping-audit.json,
contrasts.json}; graph-enqueue-terminal-j50925. Traces can perturb arrival timing;
queue-ID lookup can materialize queues on some paths. Placement evidence is scoped
to the traced single-device runs, with all timing collected separately trace0.
