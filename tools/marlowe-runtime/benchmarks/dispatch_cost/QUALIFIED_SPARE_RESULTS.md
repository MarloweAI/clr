# Qualified spare policy: grouped regression recovered, expert gains retained

Job52660 tests a narrower spare policy on new diagnostic bytes. Relative to the
same-byte legacy policy it improves grouped L32/L64 prefetch-on graph GPU time by
**2.370%/2.320%**, each exceeding2% in all four rounds. These cells return to
approximately stock performance. Four-stream expert gains are retained. Across
these76 cells there are zero >2% GPU/host regressions versus same-byte legacy;
against stock the remaining >2% elapsed loss is balanced b64/two-stream graph.
The broader suite, heterogeneous queue-pool history and new-byte model bridge
remain unqualified. No production package is promoted.

## Policy and semantic limits

The diagnostic permits the optional spare at instantiation when either existing
cached eligibility matches the instantiation device:

- Flat, single-device, packet-capture-eligible kernel-only graph.
- Flat, single-device graph with the existing node-count placement policy enabled.

Otherwise it uses the stock required-count allocation. Required streams, graph
edges, actual-tail joins, launch-entry ordering, caps/device restrictions,
retirement and optional-allocation OOM retry are unchanged. This is a semantic
eligibility boundary, with no root-count, width, shape or benchmark-name rules.
`GPU_GRAPH_DIAGNOSTIC_QUALIFIED_SPARE=0/1` selects legacy/qualified on identical
bytes; its diagnostic default remains0. Both arms request the existing spare
feature globally, but the qualified arm contracts its eligible graph domain.

Source review found no allocation/lifetime blocker. Scheduling computes these
caches before Init; classic fallback clears them, cross-device setters invalidate
them, and child/multidevice graphs fail the flat single-device predicates.
Later invalidation does not resize an already allocated stream pool. The trace's
`spare_requested` field is pre-allocation intent; successful stream-creation and
selected-dispatch receipts independently establish actual allocation/use. OOM
retry may reduce actual allocation; intent alone is not proof.

## Matched timings

GPU microseconds, lower is better; medians of four process medians, eight trials each:

| Graph cell | Stock | Immutable current off | Diagnostic legacy | Same bytes qualified |
|---|---:|---:|---:|---:|
|Grouped s22 L32, prefetch on|11525.143|11810.829|11804.718|11524.890|
|Grouped s22 L64, prefetch on|23077.283|23635.991|23629.082|23080.975|
|Experts b16 balanced, 4 streams|233.538|158.486|158.705|159.895|
|Experts b64 balanced, 4 streams|116.654|99.783|100.523|99.383|
|Experts b64 skewed, 4 streams|194.556|161.766|161.485|161.146|
|Experts b64 balanced, 2 streams|109.704|115.304|114.714|114.294|

Qualified/legacy L32 GPU effects by round are -2.485539/-2.294634/-2.303704/
-2.438978%; L64 -2.393543/-2.002856/-2.545572/-2.324420%. Host effects agree,
-2.354126%/-2.316161%. Submission also improves5.966851%/2.925272%.
Qualified/stock GPU is -0.002193% L32 and +0.015999% L64; host+0.011622%/+0.019579%.
Thus this cohort recovers the immutable-current-off losses of2.478807%/2.421031%.

Four-stream expert qualified/stock GPU gains are31.533446%,14.805321%,17.172691%
in table order, with corresponding host gains29.871778%,13.749232%,16.597201%.
Qualified/legacy GPU effects are+0.749980%,-1.134315%,-0.210389%; no >2% elapsed
loss appears anywhere in the76-cell same-byte comparison.

The remaining balanced b64 two-stream graph is **4.183996% slower than stock GPU**
(+4.590001us), host+3.866801% (+4.602750us), submission+6.780126%. GPU rounds are
+3.910626/+2.776175/+4.831042/+4.458566%. The qualifier/legacy difference is only
-0.366127%, consistent with the same allocation path. This experiment does not
solve that deficit or establish an unavoidable synchronization floor.

All side effects remain: qualified/legacy has seven submission gains and six
losses above2%; qualified/stock has28 gains and16 losses. The rebuild control
legacy/current-off has no >2% GPU changes but a b16 isolated merge/eager host
loss of3.250215% (+0.4725us). Qualified/legacy shows a3.347768% host improvement
in that same eager cell; it does not execute graph policy, so neither is claimed
a direct mechanism effect. All samples/rounds remain in contrasts.json.

## Validation and coverage

Root directly submitted and monitored node2, one GPU, with the standalone launcher.
Slurm0:0, in-container final audit and local saved-artifact audit pass. New runtime
bytes reran144 existing correctness processes /3,744 rows: six entry/tail/lifecycle/
transfer/publication/disabled-root fixtures, all native/placement combinations,
legacy/qualified, queue caps1/4/8. Prior-byte correctness was not substituted.

Four separate untimed proofs contribute512 arithmetic rows, excluded from timing.
Grouped proofs validate all six one-root DAGs, actual creation counts, requested
eligibility and selected logical/physical queue binding. Expert proofs validate
26 graph generations,44 segment generations,208 launches,352 execution receipts
per arm. Successful allocation and selected-queue receipts show the qualified arm
keeps expert extra streams2/4 and four physical queues for four-stream experts;
grouped extra streams become1/2 and prefetch-on uses two physical queues. All
samples are retained; no gap investigation, workload/application changes or models.

The unchanged job52217 benchmark/reference bytes cover grouped_s1, grouped_s22
and experts in four Williams orders:48 timing processes /9,728 rows /76 cells.
Direct dispatch1, native0, placement0, cap4, dynamic queues0, streamops0; all timing
logging/tracing/DOT output off. Proofs and timings audit mapped HIP/HSA/rocBLAS
hashes. Independent review verified all30 frozen hashes and recomputed every
signed median, round and contrast from all9,728 rows. It additionally bound every
allocation-intent receipt to the following matching selection generation, including
reused graph addresses, and confirmed both complete expert proofs. This is a bounded flags-off screen, not the full313-cell suite or a new
HiSparse result. The immutable fusedRC1 C1/C4 evidence remains separate.

## Artifacts and remaining work

Local iteration root: /home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918;
remote uses the same suffix under /workspace/home/sasha/amd-runtime-production/iterations.
Raw:qualified-spare-j52660; libraries:qualified-spare-lib; isolated source:
qualified-spare-src. Reproduction:run_qualified_spare.py, qualified_spare_checks.py,
qualified_spare_observer.py, build_and_run_qualified_spare.sh, submit_qualified_spare.sh,
qualified-spare-spec.json. The diagnostic source delta is retained in
[qualified_spare_diagnostic.patch](qualified_spare_diagnostic.patch); it is not
applied to the PR's runtime files.

- Diagnostic HIP:cab16effd6d3b4af9205437fb0e1249e68cf87cb4379d77c737d12786c7bd6ff.
- Shared HSA:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Current HIP:1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04.
- Stock HIP:f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac.
- Frozen spec:c11ea847ba44754c3a05528fcdf5422578ea1fa2855b925d21e4a8c57a1da2de.
- Manifest:a7f2c356c6c2b514daf357c75bd1ffd25629ad484165aaaced1f705ef7841c9e.

Next acceptance work includes heterogeneous kernel/copy graphs sharing one pool,
full-family on/off comparisons, and resolving the two-stream expert penalty.
The per-graph policy can change pool history even when each individual graph
chooses a previously measured arm. Historical model/waiter results cannot be
assigned to these new bytes. Keep production qualification false.
