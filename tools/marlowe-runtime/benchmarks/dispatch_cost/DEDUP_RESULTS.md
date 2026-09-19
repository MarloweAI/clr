# Duplicate prewait ablation — job 50391

Node2, one GPU; 33 timing processes / 11,088 retained correctness rows, plus six separate trace processes / 252 rows. Strict coverage, output and mapped-library audits passed. HIP `5f65d49af029567e518b1dad04692e6649dbd5620e905de93b3ccbff319ad75c`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. All same-byte policy controls retain original AQL waits. Cost-source native-off/guarded/threshold8/relaxed bridges are included. This diagnostic is not production-qualified.

Medians of three process medians, GPU microseconds:

| Attention case | Stock | Guarded | Threshold 8 | Threshold 8 + dedup | Relaxed | Relaxed + dedup |
|---|---:|---:|---:|---:|---:|---:|
| 256 / 256 / 16 / graph / parallel | 634.663 | 634.418 | 672.359 | 670.098 | 703.880 | 700.400 |
| 256 / 256 / 1 / eager / parallel | 69.582 | 69.801 | 69.582 | 69.761 | 126.302 | 126.323 |
| 64 / 8192 / 1 / eager / parallel | 1544.851 | 1541.631 | 1544.870 | 1539.371 | 1609.133 | 1607.332 |

The 16-launch graph trace confirms that the two native prewaits belong to the same virtual consumer, physical queue, signal object instance and generation. Dedup emits one and skips the second. Across all trace cells, threshold 8 emissions fall from 20 to 16, with four duplicate receipts; relaxed has nine duplicate receipts. Queue-cap1 emits no native packet. These are separate trace observations, not exact timing-run counts.

Despite that successful suppression, the failing 16-launch graph remains **5.63% slower than guarded** with threshold 8 + dedup. Removing the second prewait saves only 2.261 µs of total time here; the main handoff penalty remains. The single-launch short and original long-kernel regressions also remain with relaxed + dedup. This independently supports the single-admission finding from the arrival experiment: duplicates are not the main cause. Do not promote dedup as the solution.

No old-cost→new-dedup bridge shows a >2% loss repeated in every round of this matrix; native-off median differences range approximately −1.27% to +1.70%, guarded −0.74% to +0.52%. This does not qualify signal-churn or multithreaded allocation overhead. The instance allocator runs at signal construction even when native wait is disabled, so those remain required if dedup is ever considered for promotion.

Next test packet ordering, narrow non-offloaded interval values and matched stable-zero-target controls on new bytes. Those controls retain the original real AQL dependency; zero-target can restore AQL producer interference and is not a pure packet-cost subtraction.
