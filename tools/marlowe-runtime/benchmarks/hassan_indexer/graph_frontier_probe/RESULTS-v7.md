# Graph frontier v7 checkpoint — jobs 55680 and 55683

V7 preserves the measured Hassan speedup while adding bounded private generations and prompt idle destruction. The original-sized two-stream Q/K case is **11.648577 µs per pair versus fresh stock 14.251965 µs (18.27% faster)**. The 50-pair graph is **7.283035 versus 10.054830 µs per pair (27.57% faster)**. Original kernels, shapes, scheduler, warm-capture protocol and all trials are unchanged. This remains a diagnostic runtime measured on a graph-only extraction; serving, HiSparse and GLM qualification are separate.

| GPU-event µs/pair | Fresh stock | Earlier v4 on, job 55581 | v7 off | v7 on | v7 on vs fresh stock |
|---|---:|---:|---:|---:|---:|
|Serial, one pair|13.499140|12.638410|12.467307|12.545105|-7.07%|
|Two streams, one pair|14.251965|11.704485|16.530837|11.648577|-18.27%|
|Serial, 50 pairs|8.690985|8.902590|8.736285|8.684183|-0.08%|
|Two streams, 50 pairs|10.054830|7.324440|10.322437|7.283035|-27.57%|

The earlier Hassan v4 column is historical, not a matched v4/v7 comparison. The current same-byte off/on improvement is 29.53% for one pair and 29.44% for 50 pairs. Host elapsed is 11.708180 and 7.322128 µs per pair, respectively. CPU submission is 2.576950 and 1.000825 µs per pair. Both trace and timestamp instrumentation are off in timing runs. Dispatch-overlap evidence was measured separately on v4 (OVERLAP-v4.md); v7 changes lifetime/capacity handling and has not repeated that instrumented measurement.

Job 55680 completed 0:0 on node 2, one GPU. Both remote and downloaded local audits pass: 8 untimed proof processes, 36 timing processes, 288 timing rows and 6,732 numerical comparisons. Medians use three rotated process rounds, eight trials per case/round. Job 55683 ran concurrently on a different allocated GPU on the same node; it compares stock, previous v4 on, and v7 off/on. No other node was used.

## Frozen expert and small-transfer KV holdouts

Job 55683 completed 0:0 and passes remote/local audits: 48 timing processes, 6 untimed proof processes, four rotated rounds, 76 cells and 9,728 retained timing rows. The workload binary, reference files, shapes and schedules match the earlier suite exactly.

V7 is faster than stock in **63/76 cells**, with **no median regression above 2%**; the largest slowdown is **0.805%**. Against the matched previous v4 build, the range is **−0.985% to +1.635%**, with no median regression above 2%. The existing expert conflict persists: five cells are more than 2% slower than v7 off. The largest is batch64 balanced/four streams: **99.413000 µs on versus 89.842999 µs off (+10.65%)**, with every round between +9.80% and +11.62%. V4 on is 99.553501 µs in the same run. This is an existing frontier-path tradeoff, not a new v7 lifetime regression; its internal cause remains unresolved.

| Expert graph, GPU µs | Stock | Matched v4 on | v7 off | v7 on | v7 on/off |
|---|---:|---:|---:|---:|---:|
|b16-balanced, 2 streams|233.717|228.978|222.247|228.387|+2.76%|
|b16-balanced, 4 streams|233.658|154.575|148.824|153.855|+3.38%|
|b64-balanced, 2 streams|111.253|111.653|106.743|110.553|+3.57%|
|b64-balanced, 4 streams|116.394|99.554|89.843|99.413|+10.65%|
|b64-skewed, 2 streams|195.046|195.266|187.116|195.136|+4.29%|
|b64-skewed, 4 streams|196.716|155.215|154.125|154.105|-0.01%|

The grouped transfer graphs fall back to ordinary lowering; their improvements over stock are not evidence for the new private-frontier path. The suite does not include all original long-producer waiter, attention-chain and queued-stream microbenchmarks. Those remain a qualification gate.

## Correctness and architectural checkpoint

CAPACITY-v7.md records the resource/lifetime change, tests and rejected intermediate implementations. The hard cap is per GraphExec arena count, not a global byte budget. V7 uses ordinary graph lowering under pressure without an explicit CPU completion wait. Seven capacity/lifecycle cases pass, including a caller-released GPU dependency whose launch calls must return before the caller can release it. Nine preflight processes and the required ownership checks pass on the exact same runtime bytes. Fatal device-error quarantine remains source-reviewed rather than injected.

This checkpoint supports preserving v7 as the hardened Goal1 candidate. It does not establish a universally best configuration or production readiness. The next performance lead remains measured first-pair start skew at graph boundaries. A distributed predecessor-tail design requires a separate ordering/fence proof before implementation. Do not silently weaken graph ordering or add workload-specific thresholds to recover performance.

## Reproduction identity

- HIP SHA256: `e692e09467765565866387bd4918468b1cbb43459c7c2c3fd2b1242031713ff0`.
- HSA SHA256: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- Candidate patch SHA256: `a74278542225208a9bca02959d3d927031ad43e439a7ac08f431d74d00af57a3`.
- Full patch SHA256: `dc13347a5cd733ce35267af392b16bc3a84bf5e4456d21f1eee03a282f1eca0c`.
- Source manifest SHA256: `bd8d3de42c84685c4bf3445e19ccbe824dfbb44ad8704a86ac87094d893dca24`.
- Hassan raw manifest SHA256: `86e61d68ed20d1ec77a51163d432568e1cace1f3e9852ecd2a666cba40978a8b`.
- Holdout specification SHA256: `0af55e6fe9d836bf42350db5e67644309d1165183c64da77f35d46d3fd72093b`.
- Holdout raw manifest SHA256: `ad99e6d9a30591f7259b6d59f71a87a1a9cae7aa3e86fe90c89f81638f998191`.

Use both libraries in lib-v7 and the exact local controls in protocol.json. Recheck with `python3 run.py --audit --out results-j55680`, `python3 capacity_v3.py --audit --out capacity-j55677`, and `python3 holdouts-v7/run.py --audit --spec holdouts-v7-spec.json --out holdouts-j55683`. Full raw data remain in this local iteration directory and its /workspace/home/sasha cluster mirror. Frozen source, reports, launchers and manifests are archived in PR1 separately from its main runtime implementation.

Goal1 and Goal2 remain incomplete. No new HiSparse or GLM full-model run was launched. Goal1 cutoff remains September 20 at 09:00 UTC; reassess after each two or three targeted experiments and switch early if evidence no longer supports a concrete lead.
