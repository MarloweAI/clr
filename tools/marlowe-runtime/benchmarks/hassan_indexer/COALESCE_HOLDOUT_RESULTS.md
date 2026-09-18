# One-stream diagnostic holdouts — job 53134

The original Hassan win does not generalize to parallel experts. Mapping every eligible flat kernel graph to one logical stream is rejected as a production policy. Preserve multiple streams where overlap helps.

Same HIP862f3cd7 bytes and HSA b8cdfe93 as job53091. The frozen expert and grouped-KV binaries, CPU reference files, inputs and timing protocol from the earlier acceptance matrix are unchanged. Stock and three new-binary settings run in four balanced process orders, eight trials per case. Node2, one GPU. All48 timing processes,9,728 timing rows,76 cells and6 separate structural proof processes pass remote and local source/artifact/control/library/numerical audits. Every trial is retained.

Representative original graph GPU microseconds:

| Workload | Stock | New diagnostics off | One stream + shared retirement | Versus stock |
| --- | ---: | ---: | ---: | ---: |
| Experts b16 balanced, 2 streams | 234.168 | 230.338 | 410.313 | +75.22% |
| Experts b16 balanced, 4 streams | 235.778 | 158.995 | 410.173 | +73.97% |
| Experts b64 balanced, 2 streams | 111.114 | 114.704 | 168.575 | +51.71% |
| Experts b64 balanced, 4 streams | 116.354 | 98.363 | 169.326 | +45.53% |
| Experts b64 skewed, 4 streams | 192.516 | 163.886 | 307.490 | +59.72% |

The three new-binary settings preserve serial/batched expert performance closely. Grouped-KV graphs contain non-kernel nodes and do not enter the coalescing/shared-retirement path; structural receipts confirm fallback. Their existing native-wait/placement behavior remains: split1 is near stock and split22 is faster, but those gains cannot be attributed to the inactive new diagnostics.

The new-off balanced two-stream expert still loses approximately3.23% against stock. The four-stream improvements remain when parallel placement is retained. The next bounded candidate is sharing completion regions within each logical stream while preserving parallel roots: source accounting finds three accumulators can become two in the two-stream expert graph, and five can become four in its four-stream graph. This is not a measured performance gain yet. Keep all current cross-stream markers and final tail joins for that first intervention.

A generic lane selector remains unresolved. Static resource counts alone cannot reliably bound arbitrary kernel duration. A bounded tuner using actual requested replays, without extra kernel executions, was reviewed as an opt-in possibility; probe bias, initial exploration cost, variable inputs and concurrency prevent treating it as a ready default. No runtime change is promoted and no HiSparse qualification transfers.

Job53125 stopped before timing because the observer combined reused graph addresses. The corrected observer starts a new lifetime at each mapping-selection receipt; it validated the original proof as26 lifetimes and208 correct rows before the clean53134 rerun. The runtime/benchmark stayed unchanged and original failed files are preserved.

Raw: `iterations/hassan-qk-micro-20260918/coalesce-holdouts-v2-j53134`; runner/spec: `coalesce_holdouts_v2`. Spec SHA256 `3f891a4659440b2439084c223b74e08d163a05f70802b81f2332c9fb793b27de`.
