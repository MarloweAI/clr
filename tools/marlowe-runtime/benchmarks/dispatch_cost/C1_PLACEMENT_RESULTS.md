# HiSparse C1: placement gain transfers to the retained model benchmark

Job 51180 completed 0:0 on node2, one TP4 allocation. Standalone root-owned launch,
wait and validation completed in about 33 minutes including container preflight;
resident work took 31.1 minutes. All 36 trial means, 36 worker identities/maps and
controls passed the strict audit. A second audit from the downloaded raw cohorts
reproduced the remote result exactly after normalizing JSON integer object keys.
No trials were trimmed, no gaps investigated, no application or benchmark math
changed. No active allocation remains from this experiment.

## Result

Lower is better, ms/token. Each cell contains forward-block / reverse-block
medians, each based on three retained requests in a separately started resident.

| C1 configuration | Guarded256 | Admission24 | Placement + admission24 |
|---|---:|---:|---:|
| Prefetch on | 18.053503 / 18.001993 | 16.766245 / 16.749011 | **15.259813 / 15.234404** |
| Prefetch off | 15.089747 / 15.099674 | 15.061193 / 15.092761 | **15.083341 / 15.053128** |

Placement adds an 8.98% / 9.04% prefetch-on improvement over admission24. The combined
candidate is 15.47% / 15.37% faster than guarded256. Admission24 alone repeats its
previous approximately 7% benefit. Prefetch-off stays effectively neutral:
placement changes +0.15% / −0.26% versus admission24 and −0.04% / −0.31% versus guarded.

Both frozen gates pass: at least 2% prefetch-on improvement in each block, and no
more than 1% prefetch-off regression against either contemporary control. The
microbenchmark's directional scheduling prediction therefore transfers; its
approximately 4–5% gain did not predict the exact 9% model magnitude. Previously,
grouped25 also predicted the held-out admission64 intervention. This is evidence
of usefulness across these interventions, not a universal model proxy.

Historical best 14.897670 ms/token is from a separate graph-optimized cohort.
The new candidate remains 2.43% / 2.26% above it (0.362 / 0.337 ms/token). This is close,
but it does not meet a strict within 2% target. Do not interpret the residual as a
causal marker cost or compare prefetch-off against that prefetch-on reference.

## Frozen implementation and protocol

Package marlowe-hip-7.2.4-graph-tail-diagnostic1, unqualified for production.
HIP d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3;
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
Base cab5670 plus patch 38a91fb038a72604057955a7ab7b140d808c5b8543d6d5aa31a88a88648e6dfc.

Three same-byte states, separately restarted in order:
guarded-a, threshold24-a, placement24-a, placement24-b, threshold24-b, guarded-b.
Each executes three alternating C1 prefetch-on/off requests. All 192 measured
token intervals per request are retained after the standard 64-token warmup.
All source/tape/client identities and controls are pinned; application e4b3fe5d,
TP4, CPU affinity inherited, trace0, SIDEWAIT0, no marker omission, no unconditional
admission bypass. Placement changes cached assignment by descending own segment
node count, stable ties, preserving baseline enqueue order. Actual stream-tail
completion is corrected. All original AQL dependencies and native physical-queue,
signal-ABI/value/retirement guards remain.

The 6 residents are the intervention units, with two starts per mode; 36 request
means are nested observations. ABCCBA balances linear drift, but a nonlinear
middle-of-run effect could favor both placement residents. Frozen gates are
screening criteria, not confidence bounds. Broad micro and repeated grouped
factorials support this screen; this one allocation is not final qualification.

## All retained request means

| Resident | Prefetch-on trials | Prefetch-off trials |
|---|---|---|
| guarded-a | 18.018751,18.053503,18.056210 | 15.083728,15.357406,15.089747 |
| threshold24-a | 16.643422,16.766245,16.774953 | 15.071137,15.060207,15.061193 |
| placement24-a | 15.280158,15.259813,15.216025 | 15.077807,15.086865,15.083341 |
| placement24-b | 15.237065,15.227761,15.234404 | 15.053128,15.063709,15.052782 |
| threshold24-b | 16.739570,16.749011,16.789014 | 15.094954,15.086636,15.092761 |
| guarded-b | 18.008667,17.985543,18.001993 | 15.105339,15.096698,15.099674 |

## Remaining work

1. Executed physical placement is verified on all four ranks under trace1 through
   a narrower same-graph/pool counterfactual. The planned exact cross-resident graph
   match failed because captures differ; it remains recorded as failed. This does
   not establish a fixed-graph mechanism for the measured gain.
2. The existing trace0 natural-generation probes passed 12/12 across admission24
   and placement24, on/off. This is a limited retrieval screen. See [model checks](C1_MODEL_CHECKS.md).
3. C4 has now passed its retained screen: on improves about10% versus guarded,
   off remains within0.16% of controls; about1% above the separate historical best.
   See [C4 results and limits](C4_PLACEMENT_RESULTS.md).
4. Port only the selected policy into a minimal default-off implementation,
   restricted to qualified single-device graphs. Keep the unconditional generic
   actual-tail fix. Remove rejected diagnostic policies and tracing machinery.
   Rebuild bridges, correctness checks and a final model confirmation must use
   exact production-candidate bytes before packaging/deployment.

The generic actual-tail correction is already pushed to PR1 (b36e37b); placement24
remains in the versioned diagnostic patch/package. Publishing this result does not
change the release lock or deploy a runtime. The remaining historical residual
should not trigger another optimization until the current candidate is qualified.

Artifacts: c1-placement-j51180/{manifest.json,audit.json,mirror-audit.json,contrasts.json}
and all six downloaded cohort roots under cohorts/. Remote raw roots:
/workspace/home/sasha/hisparse-runtime-combined-20260916/results/
c1-investigation-j51180-graph-placement-{guarded,threshold24,placement24}-{a,b}.
Full hashes, source/control receipts, request events and logs are retained.
