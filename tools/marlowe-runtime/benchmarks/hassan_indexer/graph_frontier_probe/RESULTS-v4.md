# Graph frontier v4 checkpoint — job55581

The ownership-hardened v4 candidate preserves the actual HIP/PyTorch speedup: **11.704485 µs per Q/K pair versus fresh stock14.279968 (18.04% faster)** for one pair per graph, and **7.324440 versus10.114332 (27.58% faster)** for50 pairs. The original kernels, scheduler, shapes and frozen warm benchmark protocol are unchanged. This remains a diagnostic runtime for a graph-only extraction, not a serving-application, HiSparse or GLM qualification.

Job55581 completed0:0 on node2/one GPU. Remote and downloaded local audits pass: the six-cell function/lifetime harness,8 separate path-proof processes,36 timing processes,288 timing trials and6,732 numerical comparison rows. All trials retained. Timings are medians of three rotated round medians, eight trials per cell. Both queue trace and dispatch timestamp instrumentation are disabled in performance processes.

| GPU-event µs/pair | Fresh stock | Earlier v1 on, job55508 | v4 off | v4 on | v4 on vs fresh stock |
|---|---:|---:|---:|---:|---:|
|Serial, one pair|13.316933|12.356908|12.753315|12.638410|-5.10%|
|Two streams, one pair|14.279968|11.763788|16.688542|11.704485|-18.04%|
|Serial,50 pairs|8.922692|8.889690|8.908895|8.902590|-0.23%|
|Two streams,50 pairs|10.114332|7.303642|10.352037|7.324440|-27.58%|

The earlier v1 column is historical, not a matched rebuild comparison. Same-byte v4 off/on improves one-pair two-stream time29.87% and grouped time29.25%. Current two-stream time is7.39% below its own serial at one pair and17.73% below its own serial when grouped. Serial uses a different eligible path, so direct overlap evidence comes from the separate timestamp experiment, not that comparison.

Host elapsed confirms the GPU-event result: stock14.318955 →v4 11.748803 µs for one pair;10.160455 →7.363475 grouped. CPU submission is4.414300 →2.661150 and5.407650 →1.007800 µs/pair respectively.

## Added lifetime safety and direct overlap

v2 retains the exact compiled kernel/program at packet capture and carries that ownership into each in-flight generation. v3/v4 also fall back if any captured kernel has no executable owner. v4 separates post-retirement timestamp collection from hot queue tracing. The unchanged nine lifecycle processes passed onv4/job55564; function replacement/exec destruction/early-unload stress passed the required v4 checks in55581. See `OWNERSHIP-v2.md` for the fixture boundary and preserved earlier harness failures; job55581 repeats the corrected harness on the exact v4 bytes.

`OVERLAP-v4.md` independently audits the preserved dispatch trace from55564: all1,600 post-warmup pairs overlap on two physical queues for each graph size. Single-pair median overlap1.68µs; grouped4.32µs. The grouped first pair still starts K about3.4µs after Q; later pairs start nearly together. This identifies graph-boundary synchronization as a concrete remaining lead. It is dispatch endpoint evidence, not active-wave occupancy or a firmware diagnosis.

## Remaining gates

[Frozen expert/grouped-KV holdouts](HOLDOUT-v4.md), job55597, pass the 9,728-row audit. Across76 cells, v4 is faster than stock in63; the largest slowdown is1.08%. However, frontier-off remains faster for some expert graphs: batch64 balanced/four-stream is89.533µs off versus99.293µs on (+10.90%). Earlier v1 shows the same conflict. The ownership change preserves the earlier winner, but a general configuration still needs to resolve that tradeoff. This holdout suite does not cover every original stream microbenchmark.

A hard bound on live generations and prompt idle destruction are still missing. `CAPACITY_REVIEW.md` specifies safe pending-command ownership and ordinary-completion backpressure; v4 does not implement it. `NEXT_BOUNDARY.md` describes a possible distributed boundary, motivated by the measured entry skew, preserving all cross-launch dependencies. It is a candidate design, not implemented or measured.

No new HiSparse/GLM job ran. Goal1 and Goal2 remain incomplete. Deadline September20 09:00UTC is unchanged; switch early if the current evidence stops supporting a concrete next step.

## Reproduction identity

- libamdhip64.so: `b378fec20d524ae611b119bd986095fb0bd1d081be5cf485d2bbae6ce8cec78f`.
- libhsa-runtime64.so: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- Raw manifest: `d92250ab6a219fb33f8059fe905ac7c25ba19bb59c3139bb68f12005002709e9`.
- Candidate patch: `823678959018010010c09e0e57f0b9431c550ce57acd916ffc2f63cb7866261f`.
- Full patch: `b6009733d3dcb65dad6244cc42e1a1f8cd34fb7950fde0252a13a4f2b2d9eece`.
- v4 source manifest: `0d576b5b47307c41b17f3a23c5863ed1cb2aac19736dea4ed4e03a2c42efe9b0`.

Use the exact `local` controls in `protocol.json` and both custom libraries in remote `lib-v4`; timestamps default off. `python3 run.py --audit --out results-j55581` and `python3 ownership_v3.py --audit --out ownership-checks-j55581` revalidate the downloaded data. `v1-to-v4.patch` shows only the follow-up changes; applying `full-v4.patch` to baselinecab5670a350678f2b0a6feb388fcbbca56c426a1 reconstructs the complete diagnostic source. The report/patch archive is separate from PR1 main runtime source.
