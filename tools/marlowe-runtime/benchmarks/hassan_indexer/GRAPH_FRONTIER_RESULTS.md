# Actual HIP graph-frontier checkpoint — job55508

The original-sized warm Q/K microbenchmark now improves with actual HIP/PyTorch replay: **11.764 µs/pair versus stock14.197 (−17.14%)**, while the synthetic50-pair graph is **7.304 versus10.038 (−27.24%)**. The previous graph-local candidate still regressed the one-pair case. This closes that specific regression in the controlled microbenchmark. It does not yet establish Hassan's unchanged serving-application result, direct dispatch overlap, broad microbenchmark nonregression, or production qualification.

Job55508 completed0:0 on node2 with one GPU. Both the remote audit and the downloaded local audit pass:8 separate untimed path-proof processes,36 timing processes,288 retained timing trials, and6,732 numerical comparison rows. Three rotated rounds contain8 trials per cell; values below are medians of round medians. No trial is removed. Runtime tracing is off during timing.

| GPU-event µs per Q/K pair; lower is better | Fresh stock | Previous local candidate, job55216 | Current bytes, frontier off | Current frontier on | Current vs fresh stock |
|---|---:|---:|---:|---:|---:|
| Serial, one pair/graph |13.343240|12.638310|12.539910|12.356908|−7.39%|
| Two streams, one pair/graph |14.196970|16.650690|16.754055|**11.763788**|**−17.14%**|
| Serial,50 pairs/graph |8.791988|8.840636|8.782490|8.889690|+1.11%|
| Two streams,50 pairs/graph |10.037930|7.477191|10.233137|**7.303642**|**−27.24%**|

The previous candidate column is historical context from a separate cohort; it is not a matched causal contrast. The same-byte frontier toggle improves two-stream one-pair time29.79% and grouped time28.63%. These are effects of the complete new lowering/retirement path, not isolated attribution to one fence, signal placement or packet. The three per-round original-sized stock comparisons improve15.94–18.19%; grouped improves27.21–29.25%.

Host elapsed agrees: one-pair stock14.236203 →frontier11.803303 µs/pair; grouped10.081275 →7.342150. CPU submission is one-pair4.423975 →2.608728 and grouped5.488000 →0.986400 µs/pair. Thus the packet-level headroom survived actual runtime submission in this experiment.

The new two-stream result is4.80% below its own serial control at one pair and17.84% below it at50 pairs. Those controls use different eligible runtime paths, so this alone does not prove simultaneous kernel execution. Untimed receipts verify separate physical queues and the new path on both two-stream graph sizes. Direct overlap/occupancy evidence for this exact runtime remains a gate. Serial grouped is+1.11% versus stock; this small suite does not justify saying every other workload is neutral.

## What changed

GPU dependency completion is separated from host retirement. Each graph owns private GPU-local segment, entry and final tokens. Its final join covers every touched physical lane and releases to SYSTEM. A following eligible graph consumes the prior graph's final token; the main queue already orders after that final join. Ordinary commands, event notification, queries, callbacks, copies and synchronization first materialize a preallocated ordinary marker that retires the host batch. Cached value-pointer reset avoids CPU reads of GPU-local signal metadata, and the first kernel on each lane performs SYSTEM acquire without forcing every intermediate kernel to release to SYSTEM.

The graph command retains its generation until all successor references retire. Its successful completion releases its predecessor reference, preventing chains from accumulating forever across watermarks. All private packet copies and partial-prefix final joins are prepared before publication. No private handle enters normal CPU-wait, HwEvent, IRQ or native-wait-admission machinery. No graph splitting, kernel change, tensor-size threshold or logical-stream coalescing was added.

## Scope and correctness

`benchmark.py`, Hassan's extracted stream/event scheduler, AITER/FlyDSL kernels, dimensions, arguments and seeded input bytes match the preceding warm experiment. The capture stream is prewarmed; one pair has two kernel nodes. Fifty pairs is a synthetic100-kernel grouped graph. This is graph-only replay of Hassan's kernels, not the unchanged TP8/L10 serving reproducer. It must not be presented as full-model or HiSparse/GLM performance. Stock, off and on use the same benchmark/protocol within this run. Each timing trial executes200 pairs.

Separate job55504 passed all9 lifecycle/failure processes, with mapped-library/source/binary hashes audited. Checks cover pending asynchronous inputs, D2H copies after a private graph tail, exact public events before later work, host callbacks, concurrent queries, a1,104-launch updated-argument chain, two-stream parameter updates, executable destruction before sync, stream destruction, one-physical-queue fallback, disabled-node fallback and a sealed partial-publication failure. See `PREFLIGHT-v1.md` for exact receipts and limitations. The watermark bounds unsealed batch length but does not by itself cap all generations while callbacks lag; batch8 reached82 live generations. A hard capacity policy is still required.

Independent xhigh source/hook review is recorded in `REVIEW-v1.md`. It cleared this bounded default-off test surface, not production. v1 does not explicitly retain the exact compiled kernel across function-changing updates/module unload. A follow-up source change retains the kernel at packet capture and leases those owners per launch; v2 compiled as job55521 but has not been tested or timed. v1 results do not qualify v2.

## Remaining work and decision

1. Validate exact compiled-function/program ownership, function-changing updates/module unload, and a bounded in-flight resource policy.
2. Obtain untimed dispatch-overlap evidence for the actual new path with unchanged Q/K kernels. HSA packet timestamps are dispatch endpoints, not active-wave occupancy or completion-signal-ready timestamps.
3. Preserve the short and grouped gains on the next safe candidate; run the broader existing microbenchmark holdouts and Hassan's canonical serving graph as required by Goal1. Do not substitute the synthetic grouped graph for the original case.
4. At the September20 09:00UTC cutoff, checkpoint and move to Goal2 (or earlier if concrete leads end): recover/retest the best HiSparse runtime, validate GLM5.2 resident E2E without HiSparse, and create the clean minimal PR.

The current result justifies continuing Goal1. Neither goal is complete. No new HiSparse or GLM job ran in this checkpoint, and no production runtime is deployed.

## Provenance and reproduction

- HIP SHA256: `3de08d266bed17cba7a9aa93a217a1724edd50feaadcbdd9429da13ae51aecbe`.
- Private HSA SHA256: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- v1 candidate patch against isolated diagnostic baseline7d32325: `8442025c3adb0402996609f36465f63d002dfe779c3aeca9759e657bcc4617a7`.
- Full patch against `cab5670a350678f2b0a6feb388fcbbca56c426a1`: `d229f4123d51017dd5fcddb965486b14caeb925e053fb5dfdded3b2d3ba15083`.
- Source manifest: `a10a8926d2d649c76f0c830101e405d55dc88a1e0406eb5ff16a072eaa53acea`.
- Raw result manifest: `47e2cb0dedab0fca7135e5535250b57eb85802f84c07e0a5e43ba9f4ec02e159`.

Working directory: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-graph-frontier-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Raw roots are `preflight-j55504` and `results-j55508`. `python3 preflight.py --audit --out preflight-j55504` and `python3 run.py --audit --out results-j55508` revalidate them. Build jobs55490/v1 and55521/v2 used0 GPUs on node2. Root-owned standalone observers waited for terminal state and validated outputs; no benchmark agent or duplicate job was used.

The diagnostic package is the remote `lib-v1` directory. Both custom libraries are required, together with the exact `local` controls in `protocol.json`, including `GPU_GRAPH_DIAGNOSTIC_FRONTIER=1`. Defaults remain off. This is an experiment artifact, not the recommended HiSparse/GLM release package. The PR archives the patch and experiment separately; its main runtime implementation is unchanged by this checkpoint.
