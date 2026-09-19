# Actual unchanged-kernel dispatch overlap — v4 / job55564

The v4 graph-frontier runtime shows overlapping Q/K dispatch intervals on two distinct physical queues. All 1,600 post-warmup pairs in each graph size overlap. Kernels, inputs, scheduler and captured DAG are unchanged from the frozen warm benchmark. This is dispatch endpoint evidence, not a measurement of active-wave occupancy or the exact instant a dependency signal became ready.

| Post-warmup dispatch metric (µs) | One pair/graph | 50 pairs/graph |
|---|---:|---:|
| Median Q duration |4.96|4.44|
| Median K duration |4.60|4.44|
| Median pair span |7.84|4.56|
| Median overlapping interval |1.68|4.32|
| Median K start minus Q start |3.28|−0.12|
| Pairs with positive overlap |1600/1600|1600/1600|

The grouped graph's **first** pair still has median start skew3.4005µs and span8.0605µs across all38 launches. Later pairs have median start skew−0.12µs and span4.56µs. The median gap from completion of one pair to the first dispatch of the next is2.40µs inside the grouped graph. This supports investigating graph-entry synchronization as the next bottleneck; it does not isolate the cost of a specific fence or establish a firmware defect. Initialization launches remain in the raw data: one-pair1800/1802 and grouped1899/1900 pairs overlap across all phases.

The timestamp flag is separate from hot queue tracing. `GPU_GRAPH_DIAGNOSTIC_FRONTIER_TIMESTAMPS=1`, queue tracing0. Timestamps are read from each original dispatch's private completion signal only after ordinary retirement and all successor references retire, before signal reuse. Every measured segment contains exactly one original Q or K kernel. No tracing is emitted between publishing a launch's Q and K. Post-retirement logging can affect later host submissions, so **these runs are excluded from performance qualification**. Performance job55581 uses timestamps off.

## Analyzer correction and audit boundary

Slurm55564 remains FAILED1:0. All9 lifecycle processes passed, both benchmark children exited0, and both wrote COMPLETE with numerical checks. The failure was the first analyzer's assumption that adjacent numeric segment IDs are Q/K pairs. IDs are storage indices: grouped publication order is0,99,1,98,…,49,50. The runtime stores receipts in dependency-level publication order.

`timestamps_analysis_v2.py` independently audits the preserved raw files, original source/build/log/file hashes, mapped libraries, controls, all306 numerical rows, all7,404 dispatch records, both physical queues, and all3,702 pairs. It verifies the frozen DOT is a sequence of independent Q/K pairs with a complete join between successive pairs. It pairs ordinal Q and K receipts in publication order, checks every ID exactly once, and requires the next pair to start after both prior dispatch endpoints. It neither edits the failed manifest nor fabricates a successful original job. Output: `timestamps-j55564-analysis-v2.json`.

HIP SHA256 `b378fec20d524ae611b119bd986095fb0bd1d081be5cf485d2bbae6ce8cec78f`; HSA `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`. Original manifest `63e430af452732d89a9c19748aaaeb0670df444f224e1ea5a491573b60bd5da7`.

Revalidate with `python3 timestamps_analysis_v2.py --input timestamps-j55564 --output timestamps-j55564-analysis-v2.json` and `python3 preflight.py --audit --out preflight-j55564`.
