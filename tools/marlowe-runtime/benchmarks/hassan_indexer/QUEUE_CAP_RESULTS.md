# Physical queue-cap control — job 53011

Reducing the physical queue cap to one makes the unchanged event-graph workload substantially slower. It does not implement logical graph coalescing: two logical streams retain their dependency handling while sharing one physical queue.

Four balanced rounds, eight retained trials per process, original kernels and scheduler, 200 invocations per trial. All 16 processes, 256 timing rows and 320 numerical checks pass the artifact/library/source audit; all trials remain retained. Both eager and graph modes ran. No production qualification is claimed.

| Runtime | Physical queue cap | Graph GPU us | Graph host us |
| --- | ---: | ---: | ---: |
| Stock | 4 | 19.836004 | 19.877355 |
| Current | 4 | 22.156832 | 22.200230 |
| Stock | 1 | 25.482695 | 25.520430 |
| Current | 1 | 31.646597 | 31.686945 |

Current cap1 loses 42.83% versus current cap4, with 41.64–43.27% loss in every round. Stock also loses 28.47%. Eager current cap1/cap4 is approximately neutral at 50.57 us and remains dominated by host submission. The original current/stock cap4 regression is reproduced at 11.70%.

Separate untimed current-runtime receipts establish the intervention:

| Cap | Main segment | Side segment |
| --- | --- | --- |
| 4 | Logical1, physical1 | Logical4, physical4 |
| 1 | Logical1, physical1 | Logical4, physical1 |

The graph is unchanged: two initialization kernels plus Q on the main segment, K on the side segment. Logs prove assignments, not GPU waiting duration. They also explain why the cap1 result cannot be substituted for the original serial scheduler, whose graph has one logical segment.

This rejects the physical-cap setting as a remedy. It does not determine the cost of assigning both graph segments directly to the **same logical launch stream** and omitting unnecessary cross-stream dependencies. That is the next isolated runtime diagnostic, guarded to flat captured kernel graphs on one device. Universal serialization remains unsuitable as a production policy: other benchmarks benefit substantially from parallel queues.

Raw: `iterations/hassan-qk-micro-20260918/queue-cap-j53011`. Spec SHA256 `3212ad72a6a044be4f7efb1b77361234072da92cde0dd047b3d82beb1ba44841`. Library hashes remain stock HIP `f1043337…`, current HIP `cab16eff…`, common HSA `b8cdfe93…`; full hashes and per-process maps are in the retained artifacts. The benchmark source is byte-identical to job52868.
