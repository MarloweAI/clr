# Grouped flags-off attribution: spare-stream hypothesis remains causal work

Job52568 reproduces the long grouped-prefetch graph regression in current fusedRC1
with native admission and node-count placement disabled. Against a clean build
containing only generic entry-ordering and actual-tail correctness repairs,
current-off is **2.458% slower at L32 and 2.656% slower at L64**. Both losses exceed
2% in every one of four rounds. This localizes the penalty beyond those repairs;
it does not yet assign causality to the spare-stream policy.

## Corrected architecture explanation

All six grouped s22 instantiate DAGs have **one root and one leaf**. Capture starts
with plan, advance and gather on stream0. The prefetch and backup streams inherit
captured dependencies before their first work. The launch-entry fork requires
multiple level-zero segments and is inactive here. D2H prevents all-kernel entry
fusion eligibility, but it does not create a fallback entry marker in a one-root
graph. The earlier explanation in ENTRY_JOINT_RESULTS was incorrect and is corrected.

Internal cross-segment dependencies remain numerous. For this topology the old
and repaired tail selectors choose the same last command per assigned stream.
Actual instantiate DOTs and scheduler receipts agree across stock, clean vanilla,
repair-only, and current-off: (nodes, segments, max dependency level, max streams)
are (220,16,8,2), (220,24,10,3), (880,64,32,2), (880,96,40,3),
(1760,128,64,2), (1760,192,80,3), in L8/L32/L64 prefetch-off/on order.

An active structural difference is optional spare allocation: stock/vanilla/repair
create 1/2 extra streams for off/on, whereas current-off creates 2/3. CODE/QUEUE
logs establish allocations and candidates, not final physical queue assignment.
DOT StreamId is logical. The next bounded diagnostic toggles only this optional
allocation on identical bytes, retaining required streams, OOM fallback, dependency
edges and retirement. Actual selected dispatch queues will be observed separately
from timings; such receipts do not prove GPU packet completion or SDMA overlap.

## Frozen comparison and results

Root directly submitted and monitored node2/oneGPU, Slurm0:0. No application or
benchmark changes, model runs, tuning, gap investigation or sample exclusions.
The unchanged job52217 executable and references run the complete grouped_s1 and
grouped_s22 families, eight trials per process, four Williams orders. There are
32 timing processes, 3,072 timing rows and 24 cells. Medians of within-process
trial medians are shown below; all signed GPU, host and submission effects and
per-round values remain in contrasts.json. Four separate untimed s22 observations
are excluded from performance. Direct dispatch=1, queue cap4, streamops=0; timing
logging and DOT output are explicitly disabled.

Prefetch-on / total / graph, GPU microseconds (lower is better):

| Layers | Stock | Clean vanilla | Repair-only | Current off |
|---|---:|---:|---:|---:|
|32|11546.319723|11528.090716|11544.070959|11827.771425|
|64|23042.393685|23118.335724|23047.574044|23659.763813|

| Current off / repair-only | GPU | Host | Submission | GPU delta |
|---|---:|---:|---:|---:|
|L32|+2.457543%|+2.452800%|+9.187993%|+283.700466us|
|L64|+2.656200%|+2.651393%|+2.785233%|+612.189769us|

GPU effects by round: L32 +2.152068/+2.601321/+2.352240/+2.617955%;
L64 +2.598422/+2.689251/+2.344827/+2.727823%.
Against stock, current-off loses 2.437588% and 2.679279% respectively.
These are the only cells exceeding 2% GPU/host change for current-off/repair-only
or current-off/stock. Clean vanilla/stock and repair-only/vanilla have **zero
absolute GPU or host changes above 2% across all24 cells**. This statement does
not claim neutral submission cost.

In-container, local saved-artifact and independent Codex review audits pass.
The reviewer independently recomputed all3,072 timing rows, every signed contrast
and round, all23 frozen inputs, mapped-library receipts and all24 instantiate DAGs.
No production qualification follows from this attribution.

## Failed preparation and immutable evidence

Job52561 failed before any timing: the observer used AMD_LOG_MASK=0x4010 while
this runtime parses that uint flag using atoi, yielding zero. Its benchmark and
DOT generation completed but expected CODE/QUEUE observations were absent.
All original artifacts remain failed and unchanged. Job52568 uses decimal16400
in new v2 files, otherwise unchanged runtime/workload/binary/protocol.

Local iteration root: /home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918.
Remote mirror uses /workspace/home/sasha/amd-runtime-production/iterations with
the same suffix. Raw roots: grouped-attribution-j52561 (failed),
grouped-attribution-v2-j52568 (complete). Frozen runner: run_grouped_attribution_v2.py;
observation: grouped_attribution_observer_v2.py; launcher: submit_grouped_attribution_v2.sh.

- Stock HIP: f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac.
- Vanilla HIP: e2331511d322c6c6aed0fb98197a5703319ca4393d84329dccdcbf025ea9115c.
- Repair-only HIP: 4f1d72c5388340ecfba70b6c48002c78591968566f31bc6ae6f92be1a173bc95.
- Current HIP: 1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04.
- Shared HSA: b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Benchmark: de0bc5d2fa4d589868a6ed43dd831c461eb54cca8706fad42c3d4003df50e83b.
- V2 spec: 9becb36e66d32091c4ce63d115599e369d31ed7787a7be228a901bad0c32ad08.
- Manifest: 343d084d80cab31676e537efcca3392a4d8cc5fd7fc6abe05137c2d2e76ebb6f.
