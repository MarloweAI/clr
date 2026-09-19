# HiSparse C4: the selected policy passes the retained concurrency screen

Job51509 completed Slurm0:0 on node2, one TP4 allocation, in about37 minutes.
All36 timing trials,36 worker identities/maps and per-worker controls passed the
strict audit. A second audit of all downloaded raw cohorts reproduced it exactly.
All observations remain retained; no application or benchmark math was changed.

Lower is better, ms/token. Each entry is the forward / reverse block median from
three trials in a separately restarted resident. These are same-byte diagnostic
controls, **not the stock runtime**.

| C4 configuration | Guarded256 | Admission24 | Placement + admission24 |
|---|---:|---:|---:|
| Prefetch on |19.976529 /19.993014|19.169364 /19.144277|**17.984107 /17.953166**|
| Prefetch off |18.015178 /18.023144|18.019099 /17.983410|**18.038518 /18.010935**|

Combined prefetch-on improves9.97% /10.20% versus guarded256. Placement adds
6.18% /6.22% over admission24; admission alone improves4.04% /4.25%. All off
comparisons remain within0.16%. All three frozen screens pass: combined on gains
at least2% in each block, off has no loss greater than1% versus either control,
and placement on has no loss greater than2% versus admission24.

Historical best C4 on17.800 and off18.090 are separate-cohort context. The new
on result is1.03% /0.86% above that historical best; off is0.28% /0.44% faster.
Within this allocation, combined prefetch-on is only about0.3% faster than off.
This closes most of the previous runtime regression; it does not establish a
large remaining prefetch benefit or production qualification.

## Implementation and protocol

Same immutable graph-tail-diagnostic1 package as the C1 comparison:
HIP d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
The selected policy preserves original enqueue order and all AQL dependencies;
strict native admission24 plus stable node-count assignment; no bypass, marker
omission or launch-role suppression. Trace0 throughout.

Six residents in guarded-a,threshold24-a,placement24-a,placement24-b,threshold24-b,
guarded-b order. Three alternating on/off trials per resident, four concurrent
requests each. Trial TPOT is the mean of four per-request means, each retaining
all192 measured token intervals after64 warmup tokens. The unchanged client hash,
e4b3fe5d application, fixed tapes, exact outputs, cache/retraction controls, stable
four-rank PID linkage and six mapped HIP/HSA identities per resident are audited.
CPU affinity is inherited.

The corrected isolated harness waits for the retained server's explicit ordinary
warmup-complete marker before publishing READY. HTTP readiness alone allowed
ordinary warmup to race controlled requests in job51432; its mixed-request guard
rejected the first reverse resident. That incomplete run and the earlier51421
pre-start mount failure remain preserved, outside this complete comparison. The
new gate pins http_server.py SHA9b0e79aca44388fc1d301ce08de1c5eb4d739df4c3823895f3ed4eba24879526
and records the exact startup log prefix. No application or token-forcing guard
was changed. The final watcher's relative-path summary error was corrected
offline after Slurm and the strict audit had passed; it required no GPU rerun.

## All retained trial means

| Resident | Prefetch-on trials | Prefetch-off trials |
|---|---|---|
| guarded-a | 19.976529, 20.009037, 19.969531 | 18.015178, 18.031424, 18.012286 |
| threshold24-a | 19.171124, 19.169364, 19.140921 | 18.027892, 18.019099, 18.010461 |
| placement24-a | 17.984107, 17.993921, 17.980053 | 18.053781, 18.026299, 18.038518 |
| placement24-b | 17.948917, 17.953166, 17.959593 | 18.033066, 18.005570, 18.010935 |
| threshold24-b | 19.148927, 19.144277, 19.141030 | 17.978359, 17.997124, 17.983410 |
| guarded-b | 19.980134, 20.004566, 19.993014 | 18.023144, 18.030397, 17.995850 |

## Limits and next step

Only two resident starts per mode; trial means are nested observations. ABCCBA
balances linear drift but cannot exclude nonlinear time effects. Other users had
distinct one-GPU allocations on node2: job50930 throughout, and job51534 beginning
09:34:02 UTC, after the first guarded resident. This was not whole-node isolation;
that snapshot does not establish interference. Keep both blocks and the neutral
off controls when interpreting the result. Frozen screens are not confidence bounds.

The directional grouped-micro placement prediction transfers to both C1 and C4;
it does not predict the exact magnitude or prove a unique physical mechanism.
C1 remains about2.3–2.4% above its separate historical best; C4 is within about1%.
The diagnostic package remains unqualified. Qualification now requires exact-byte correctness on the minimal selected-policy
build, unchanged microbenchmark bridges and a final retained C1/C4/natural
comparison. No additional scheduling policy is added
before that qualification. The production release lock remains unchanged.

Artifacts: iteration stream-wait-calibration-20260918/c4-readiness-j51509 contains
manifest.json,audit.json,mirror-audit.json,contrasts.json and six raw cohorts.
Remote raw roots: /workspace/home/sasha/hisparse-runtime-combined-20260916/results/
c1-investigation-j51509-graph-placement-c4-ready-{guarded,threshold24,placement24}-{a,b}.
The readiness gate/predictions and C4_NODE_COLOCATION.md retain the launch contract
and recorded node context.
