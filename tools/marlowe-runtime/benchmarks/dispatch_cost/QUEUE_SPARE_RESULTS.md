# Spare-stream allocation: causal benefit and regression

Job52606 identifies a real allocation-policy tradeoff. On **identical diagnostic
runtime bytes**, removing the optional spare restores long grouped-prefetch graphs
to approximately stock performance, but loses 20–51% on four-stream expert graphs.
Global spare removal is rejected. The two-stream expert stock regression is
unchanged and remains a separate problem. No runtime change is promoted.

## Same-byte result

GPU microseconds; medians of four process medians, eight retained trials each:

| Graph cell | Stock | Immutable current off | Diagnostic spare on | Same bytes spare off | Off/on effect |
|---|---:|---:|---:|---:|---:|
|Grouped s22 L32, prefetch on|11540.309|11790.548|11788.547|11543.709|-2.077%|
|Grouped s22 L64, prefetch on|23121.444|23640.332|23610.650|23084.913|-2.227%|
|Experts b16 balanced, 4 streams|232.237|158.525|157.965|238.378|+50.905%|
|Experts b64 balanced, 4 streams|117.804|99.383|99.764|121.434|+21.722%|
|Experts b64 skewed, 4 streams|194.716|166.095|163.935|196.846|+20.076%|
|Experts b64 balanced, 2 streams|111.224|114.934|115.024|115.024|approximately0%|

Grouped off/on GPU deltas are -244.838us and -525.737us; host effects are
-2.076750% and -2.223758%, submission -4.922412% and -1.229316%. Their GPU
round effects are L32 -1.775558/-2.224956/-2.559490/-1.884985% and L64
-2.390713/-2.248765/-2.042549/-2.217940%. All rounds improve; only L64 exceeds
2% in every round. Spare-off versus stock is +0.029461% at L32 and -0.157994%
at L64, recovering the current-off penalties of +2.168390% and +2.244185%.

Four-stream expert off/on losses exceed 18% GPU in every round. Host losses are
+47.695334%, +19.543353%, +18.706965% in table order. Two-stream b64 GPU remains
+3.416762% versus stock (all rounds >2%), so spare removal cannot solve that loss.

Across all76 cells, spare-off/on has two >2% GPU/host improvement cells (the long
grouped graphs) and three loss cells (four-stream experts), with no other >2%
GPU/host changes. Submission has 14 improvements and six losses above2%; these
remain part of the evidence. The rebuilt spare-on/immutable-off control has no
>2% GPU change, but does have a retained isolated b64 merge/graph host loss of
+2.139986% (+0.4525us; rounds +3.008596/+1.525822/+1.983664/+2.048595%). The
rebuild is not claimed neutral everywhere. Target rebuild GPU deltas are small:
L32 -0.016972%, L64 -0.125555%, balanced two-stream +0.078305%.

## What queue observations establish

Untimed selected-dispatch-queue receipts show:

| Graph | Spare off: used physical queues | Spare on: used physical queues |
|---|---:|---:|
|Grouped prefetch off, all lengths|2|2|
|Grouped prefetch on, all lengths|2|3|
|Two-stream experts, all routings|2|2|
|Four-stream experts, all routings|3|4|

The spare repairs an actual physical queue collision for four independent expert
branches. The grouped prefetch-on graph also gains a physical queue, but gets
slower. This rules out the simple explanation that an unused allocation alone
causes the grouped penalty. It does not isolate a particular engine stall or
prove exactly which queue handoff dominates. Spare creation occurs during
instantiation, outside the timed replay, so this measures its queue/resource
consequences rather than a per-launch allocation cost. Numeric queue IDs are
process-local; the relevant comparison is the aliasing and distinct-count pattern. A queue selected for submission is
not evidence of GPU completion or SDMA engine identity.

Both grouped-off and two-stream experts can select a third candidate with spare
on while using only two; unused candidates and physical aliases are explicitly
allowed by the audit. A policy that merely allocates lazily upon collision would
still add a spare for grouped-on, so that alone is not a demonstrated solution.
Allocation and placement must be considered together: the same additional
physical parallelism can help independent compute branches and hurt a dependent
compute/copy graph. Root-count or fixture-width special cases are not justified.

## Protocol and checks

Root submitted/monitored node2, one GPU, with the standalone launcher. Slurm0:0,
remote finalizer, local saved-artifact audit, and supplemental full expert-coverage
audit pass. Existing unmodified grouped_s1, grouped_s22 and experts families run
48 timing processes / 9,728 rows / 76 cells in four Williams orders. No full-model
run, workload tuning, gap investigation, pooling or timing exclusion occurred.
AMD_DIRECT_DISPATCH=1, native=0, placement=0, queue cap4, streamops=0,
DEBUG_HIP_DYNAMIC_QUEUES=0; all timing logs/queue traces/DOT output are off.

Before timing, 144 existing correctness processes / 3,744 rows cover six entry,
tail, lifecycle, publication, transfer and disabled-root fixtures; native/placement
four combinations; spare off/on; queue caps1/4/8. Four untimed proofs contribute
512 arithmetic rows, excluded from timings. Both grouped proofs verify all six
one-root instantiate DAGs and actual selected logical/physical queue pairs.
Both expert proofs pass an additional source-derived completeness audit: 26 graph
generations, 44 segment generations, 208 launches and 352 execution receipts,
including reused graph addresses. Each segmented graph runs four warmups plus four
retained observation trials. Independent review recomputed all9,728 timing rows,
all76 signed cells and rounds, frozen29 inputs, and correctness/proof receipts.

The source diagnostic adds a spare-allocation boolean (default true) and disabled
queue receipt hooks. It preserves required stream count, OOM fallback, graph
edges, fences and retirement. With dynamic queues disabled, observation reads
stable selected queues. No graph/application code or retained package is changed.

## Artifacts

Local root: /home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918.
Remote uses the same suffix under /workspace/home/sasha/amd-runtime-production/iterations.
Raw: queue-spare-j52606; package: queue-spare-lib; spec: queue-spare-spec.json;
runner: run_queue_spare.py; build/submit: build_and_run_queue_spare.sh and
submit_queue_spare.sh; proof helpers: queue_spare_checks.py, queue_spare_observer.py;
supplement: audit_queue_spare_expert_coverage.py / queue-spare-expert-coverage.json.
All signed values are in the raw contrasts.json. Prior job52568 is retained separately.

- Diagnostic HIP:75b840f48b0414fbb6724a1283aa7d94574955130f82a029e33d7e630d0f9e0f.
- Immutable HIP:1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04.
- Stock HIP:f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac.
- Shared HSA:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Frozen spec:ba1bce20404abd2625e4dda33e5689aff1d4916f999cc222277b6a94c489885b.
- Manifest:20a2a91abad13baf24b8af1583d268fc1bd7cec69a320c08713b4d2a159732a0.
- Expert supplement:86da1852a9471f80536f2199ce5d706e175cffb87b4bcc5ca750af89008ab51e.
