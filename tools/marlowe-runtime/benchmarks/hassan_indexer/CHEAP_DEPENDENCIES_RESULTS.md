# Hassan Q/K: explicit scheduler and structural marker fusion

2026-09-18. Job 54192 on node2, one GPU, completed 0:0. Remote and independent local audits pass all 72 timing processes / 576 retained timings, 64 semantic fixture processes, four active-path proofs and 22,800 numerical checks. No full-model experiment.

**No winning parallel runtime candidate emerged.** The structural changes reduce CPU submission cost substantially, but recover little GPU time in the repeated fork/join chain. Keep the current production/default selection unchanged.

| Runtime / scheduler | Serial GPU µs/pair | Two-stream GPU µs/pair | Two-stream CPU submission µs/pair |
|---|---:|---:|---:|
| Stock, automatic (classic for this graph) | 8.750639 | 10.071631 | 5.429937 |
| Stock, forced segmented | 8.760938 | 11.057362 | 3.527226 |
| New bytes, forced segmented, B0/T0 | 8.759989 | 11.334273 | 4.066551 |
| Same bytes, B1/T0 | 8.748037 | 11.251570 | 3.084950 |
| Same bytes, B0/T1 | 8.768186 | 11.295573 | 4.079727 |
| Same bytes, B1/T1 | 8.759737 | 11.159668 | 3.054912 |

B imports the same retained internal dependencies into the following captured batch, removing a separate consumer marker command/completion. T folds the final side-tail join into the graph-release completion marker. Actual dependency waits, scopes, changed-input correctness and two physical queues remain. Neither optimization coalesces the graph or tunes kernels.

Same-byte B1/T1 versus B0/T0: GPU elapsed 11.334273 → 11.159668 µs (-1.54%), CPU submission 4.066551 → 3.054913 µs (-24.88%). The two-stream candidate remains 10.80% slower than stock's automatic scheduler and about 27.6% slower than serial. Stock forced segmented itself is 9.79% slower than stock automatic despite lower CPU submission. The whole scheduler change must not be confused with the incremental fusion effect. This is evidence against host bookkeeping alone explaining the observed loss; it does not isolate an individual GPU packet or prove a firmware defect.

Protocol: exact same HIP build as 54155, no rebuild. Original Q/K GEMMs, dispatch configurations, input tensors and begin/fork/join dependencies; actual capture streams warmed; 50 pairs per graph, 200 pairs per trial, eight trials per process, six balanced mode orders. CPU submit, GPU elapsed and total host time all retained. Original input/output and library/source hashes audited. This is the Python replay protocol, distinct from the tight C++ launcher used in the polling-control experiment.

Coverage: stock's inherited heuristic sends at least 16 short segments to classic execution unless DEBUG_HIP_GRAPH_SEGMENT_SCHEDULING=2. This run makes that switch an explicit factor. Each new-runtime untimed proof has 400 segment executions on two physical queues across four replays; B-enabled proofs have exactly 392 dependency imports; T-enabled proofs have exactly four final joins fused. These assertions pass before timings begin. Failed-prefix fixtures preserve ordinary retained joins. Default-scheduler 54155 remains an original qualification failure, separately audited as fallback-path evidence; its artifacts are unchanged.

Small-graph companion result (54155, one pair per graph, automatic scheduler): same-byte final fusion alone improves 21.525958 → 17.605378 µs (-18.21%), still slower than stock 14.123665 µs. Thus T removes a meaningful per-graph cost, but amortizing it across 50 pairs makes its impact small. B has no internal edges to optimize in the one-pair case.

The GPU-polling control 54181 gives a complementary result: at identical split-Q/K graph boundaries, events 30.263145 versus GPU polling 20.992790 µs (-30.63%); the same stream-memory API using CP waits takes 31.385779 µs. Polling still loses to split serial 18.464658 and unsplit two-stream 14.254271. Preserve the unified graph while investigating wait/completion packets; simply splitting it is not the solution for this extracted case.

Next candidates, not yet integrated into this candidate or qualified on Hassan:

1. Publish segment completion on the final real kernel packet instead of a separate retirement packet, preserving full-prefix completion, signal generation ownership, scopes and failed-prefix handling. An error/lifetime review is necessary before replacing the existing retirement mechanism.
2. Isolate graph-entry acquire and release scopes using actual packet-header receipts. The current entry helper calls addSystemScope(), which can strengthen both scopes; check the original captured header first. Do not narrow a required scope or infer a gain from the source alone. A previous [scope discriminator](../dispatch_cost/ENTRY_SCOPE_RESULTS.md) (52028) already tested SYSTEM-acquire/AGENT-release on expert/KV graphs and found no material gain; reuse that implementation and evidence instead of treating this as a new general explanation. Hassan was not in that cohort, so this is a lower-priority, bounded check.
3. Evaluate a GPU compute prewait against the existing retained producer completion signal, keeping the original full-width AQL dependency/fences. This could avoid split-graph and write-value API costs. It needs queue-alias, CU-resource/progress, signal lifetime and nonrecursive packet-construction checks; the explicit stock polling workaround does not establish an automatically safe runtime substitution.

No new heuristic based on Hassan's kernel names, shapes, splitK or observed duration is proposed. Broad microbenchmark holdouts follow a candidate that actually improves Hassan; no broad default promotion or production claim is made here.

Exact bytes/source:

- libamdhip64: `102cf658a8cbe7f02f36a85a9f9dbdb344b3cbb23be1b1b0141d6ce93214597c`.
- libhsa-runtime64: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Source content branch: [8246bd7](https://github.com/MarloweAI/clr/commit/8246bd7), `marlowe/graph-cheap-dependencies-diagnostic-20260918`. The build was made before this content commit, from `cab5670a350678f2b0a6feb388fcbbca56c426a1` plus patch `a7b04c7d9ad46330ed74221ad09cffe3cf93dc205174cf7e7599620c66f41c0c`. Rebuilding at the content commit may change version metadata.
- Result manifest: `8b723c0172f156f29098c70ffebfd51f66e0b504ec2f14e1ce9f1c8572716884`.

Reports/raw roots: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-cheap-dependencies-20260918`, `hassan-segmented-control-20260918`, `hassan-polling-control-20260918`; remote mirrors under `/workspace/home/sasha/amd-runtime-production/iterations/`. Original plans, controls, harness hashes, all logs, per-round data and independent auditors remain there. PR1 contains the polling reproducer and reports; diagnostic runtime changes remain on the separate branch.
