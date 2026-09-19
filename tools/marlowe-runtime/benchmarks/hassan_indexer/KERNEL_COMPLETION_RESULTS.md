# Hassan Q/K: completion on the final kernel

2026-09-18, job 54286, node2, one GPU. **The candidate reduces retirement cost but does not deliver a parallel speedup over serial.** It remains diagnostic/default-off. All 80 timing processes (640 retained trials), 42 semantic fixtures, 6 packet proofs and 13,158 numerical checks pass the separate corrected audit. The original final audit failed on an incorrect new-fixture join expectation; Slurm FAILED 1:0 and frozen artifacts remain preserved.

| Runtime / scheduler | Serial, 1 pair | Two streams, 1 pair | Serial, 50 pairs | Two streams, 50 pairs |
|---|---:|---:|---:|---:|
| Stock, automatic | 13.498347 | 14.178071 | 8.858241 | 10.096337 |
| Stock, forced segmented | 13.592199 | 14.255074 | 8.878142 | 11.116819 |
| Previous B/T runtime, forced segmented | 13.688404 | 17.670487 | 8.891144 | 11.208623 |
| New bytes, completion feature off | 13.513849 | 17.551731 | 8.901095 | 11.205320 |
| Same new bytes, completion feature on | 12.575815 | 16.738554 | 8.873894 | 10.245336 |

GPU µs/pair, lower is better. Median of four process-round medians; eight trials of 200 pairs per process. Original GEMMs/shapes/splitK/configurations/inputs and two-stream graph dependencies; actual capture streams warmed. Stock automatic versus forced segmented is an explicit scheduler control. All three diagnostic modes enable prior B/T dependency/final-marker fusion. Feature off/on differs only by the new runtime flag on identical library bytes.

Same-byte effects: two-stream group 50 improves 11.205320→10.245336 µs (-8.57%), improving in every round (-7.58% to -9.03%). CPU submission improves 2.965464→2.771412 µs (-6.54%). This recovers most of the previous segmented-path gap but still loses to stock automatic 10.096337 µs by 1.48%, and to its own serial path 8.873894 µs by 15.45%. Single-pair two-stream improves 17.551731→16.738554 µs (-4.63%) but remains 18.06% slower than stock. Single-pair serial also improves 6.94%; grouped serial is effectively neutral (-0.31%).

The rebuild bridge is small: previous versus new-off two-stream group 50 is 11.208623 versus 11.205320 µs (-0.03%); group 1 is 17.670487 versus 17.551731 µs (-0.67%). Do not use an on/off win as a stock or parallel qualification.

## Mechanism and proof

A proven retirement region now carries its normal command completion signal on the final real barrier-ordered kernel. It avoids a separate retirement NOP. Nonterminal packets carry no completion signal, including across physical publication chunks. Original kernel packet headers/scopes, launch predecessor, imported graph dependencies, two logical/physical queues, batch callbacks and signal references remain. Unsupported/empty/unordered tails use ordinary retirement. No kernel-name, shape, duration or coalescing heuristic selects the change.

Each enabled Q/K proof across four replays has 8 final-kernel completions for group 1 or 400 for group 50; disabled/parent proofs have zero. Both physical queues are used. All expected internal dependency imports (392 for group 50) and four final-marker fusions are verified. Every packet trace requires signal 0 until the last packet, and last-packet barrier 1/nonzero completion. These path proofs run before timing; all timed traces are off. This proves the packet mechanism, not a new calibrated overlap timeline. Existing stock timeline evidence establishes real Q/K overlap with expensive intervals between pairs; no firmware bug is inferred here.

Correctness includes launch ordering, lifetime, terminal completion, host/device transfers, publication, disabled nodes, graph updates and immediate graph/exec destruction with work pending. The new 80-node/two-chain fixture changes terminal parameters, disables final/root nodes, alternates launch streams, and uses publication chunks 1/4/256. A 2 ms first kernel makes premature completion observable. Injection after exactly three published packets tests fallback before a terminal signal exists, with exact three-output and zero-other-output assertions. One/four physical queue caps pass. Source and injected-failure callback reviews found no blocker.

## Original final-audit failure and correction

The old lane-failure fixture fails after three graph segments, including side work, so it must retain a nonempty side join. The new physical-prefix fixture fails after three kernel packets in the first launch-stream segment, before any side work. Its required trace is one launch-stream execution, ordinary FALLBACK retirement, and side_tails=retained=marker=0. The original final auditor incorrectly demanded the old nonempty side join for both fixtures.

A separate audit_corrected.py requires the exact zero-side topology for the new fixture and retains the original nonempty-join requirement for the older fixture. It preserves all artifact/source/library/control/packet/numerical assertions. Independent source review confirmed this cleanup behavior. No timings, runtime or original auditor were changed; no original COMPLETE marker was created. The job remains FAILED 1:0 with a passing corrected evidence audit, not a runtime qualification. Future launchers should run the same complete fixture auditor before timing and at finalization.

## Interpretation and next step

This removes measurable synchronization machinery inside the original graph, complementing the [split-graph GPU-polling control](POLLING_CONTROL_RESULTS.md). Polling cut split-event time 30.63%, but graph splitting still lost to the unified graph. Removing a completion packet cuts another cost without changing the application graph; the remaining dependency/dispatch cost is still too large.

Next: one bounded physical-publication test at the 98 imported INTERNAL dependency edges per grouped graph, keeping graph entry unchanged. Publish an eligible wait and its terminal consumer kernel together while preserving the actual completion signal and all ordering. Physical entry co-publication was already tested in jobs52496/52519 and was neutral on expert kernels (+0.209% same-byte); that closed entry-only experiment must not be repeated. This new site combines dense internal waits with K's terminal completion, which the old timestamp-free entry path did not support. Imported edges are not necessarily emitted barriers because ready signals can be filtered; require actual treatment receipts, exact packet identity and zero treatment in the one-pair negative control.

Bounded OCKL GPU polling inside the unified graph remains secondary. Earlier V8 long-producer graphs improved 5.250→3.324 ms, but capacity-sized cooperative kernels were delayed by the polling budget. Preserve the original full-width dependency/fences and finite fallback if that mechanism is revisited. Neither new port has been implemented or launched. Broad PM4 entry relaxation already produced substantial regressions in51906 and is not a new candidate.

## Provenance

- HIP SHA256: `0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4`.
- HSA SHA256: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Build: base `cab5670a350678f2b0a6feb388fcbbca56c426a1` plus full patch `cb4ae1d8d5e3e5ccfc31cae6b22e454cbcf5d72c4fd0e1797337beba981429c2`; parent patch `a7b04c7d9ad46330ed74221ad09cffe3cf93dc205174cf7e7599620c66f41c0c`.
- Source content: [d4d8e82](https://github.com/MarloweAI/clr/commit/d4d8e82), branch `marlowe/graph-kernel-completion-diagnostic-20260918`. The content commit was created after building; rebuild version metadata can differ.
- New control: `GPU_GRAPH_DIAGNOSTIC_KERNEL_RETIRE=0/1`, default 0. Failure injection `GPU_GRAPH_DIAGNOSTIC_KERNEL_RETIRE_FAIL_AFTER_PACKETS=3` is untimed only. Both diagnostic controls remain outside PR1 main runtime.
- Result manifest SHA256: `cae98240ff73a155e579b80dd098ef0e3bed6eefeeb2b7c9971701659be1b562`.

Frozen launchers/harness/source/patch, original failed audit/log, corrected auditor, exact mirrored libraries, reviews and all raw results: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-kernel-completion-20260918`; cluster mirror under `/workspace/home/sasha/amd-runtime-production/iterations/`. Raw root `results-j54286`. [Per-round medians](kernel-completion-rounds.csv) retain every round.
