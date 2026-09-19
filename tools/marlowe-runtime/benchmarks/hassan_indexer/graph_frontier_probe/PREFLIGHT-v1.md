# v1 lifecycle preflight

Job55504 completed0:0 on node2. Remote and downloaded local audits pass all9 processes. HIP3de08d266bed17cba7a9aa93a217a1724edd50feaadcbdd9429da13ae51aecbe; HSA2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12.

| Case | Private launches | Chained | Peak live generations |
|---|---:|---:|---:|
| f0-q4-lane-fault0-batch1000 | 0 | 0 | 0 |
| f0-q4-boundary-fault0-batch1000 | 0 | 0 | 0 |
| f1-q1-lane-fault0-batch1000 | 0 | 0 | 0 |
| f1-q4-lane-fault0-batch1000 | 4 | 0 | 1 |
| f1-q4-lane-fault3-batch1000 | 1 | 0 | 1 |
| f1-q4-burst-fault0-batch1000 | 64 | 62 | 64 |
| f1-q4-boundary-fault0-batch1000 | 1139 | 1129 | 1001 |
| f1-q4-boundary-fault0-batch8 | 1139 | 1009 | 82 |
| f1-q4-burst-fault0-batch8 | 64 | 56 | 64 |

The numerical fixtures check asynchronous input visibility; graph parameter updates while64 generations are in flight on two streams; enabled/disabled fallback; three-segment injected failure and prefix retirement; D2H-copy insertion; public event boundaries before later200ms work; a host callback; concurrent stream queries; ring/watermark crossing; executable destruction before sync and stream destruction with a private tail. Exact runtime load hashes are checked from loader receipts; source and binary artifact hashes are re-audited.

The watermark bounds the length of an unsealed host batch; it does not alone impose a hard cap on all live signal generations while completion callbacks lag. The batch8 fixture reached82 live generations. A production capacity/backpressure policy remains open. Function-changing updates and module unload were not part of v1; local follow-up source now retains kernels from packet capture, but is unbuilt and untested.

No performance claim follows from these correctness checks. Actual unchanged warm Hassan g1/g50 job55508 is running separately with stock/off/frontier modes and tracing excluded from timing.
