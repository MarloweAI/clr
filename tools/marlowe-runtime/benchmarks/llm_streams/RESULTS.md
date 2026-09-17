# LLM stream microbenchmarks: first-round report, 2026-09-17

Four microbenchmarks are implemented and measured. They found a reproducible graph queue collision: four independent expert branches use only three hardware queues in stock/v8. A bounded spare stream fixes that collision in this test and reduces four-stream graph latency by 18–35%. All new full-schedule correctness checks, the existing performance screen, and PyTorch microchecks passed. The original waiter benchmark still removes approximately 96% of the added overhead.

This is a one-GPU microbenchmark report, not a reproduction of the full-model C1/C4 results. No GLM/model jobs ran. Allocation 48445 on `marlowe-mi355x-2` has been released.

## Old runtime, new runtime and expected latency

All values are **microseconds**, lower is better. “Previous experimental” is c82cf08 with its accepted graph controls, the old candidate in the supplied HiSparse report. “PR1 v8” is the exact reported package, enabled. “Revised” is v8 plus the graph spare change. Stock is included so the two meanings of “old runtime” remain explicit.

| Captured-graph case | Stock | Previous experimental | PR1 v8 | Revised | Expected, no interference |
|---|---:|---:|---:|---:|---:|
| Sparse KV restore + resident attention | 699.6 | 731.3 | 696.2 | 695.5 | 668.4 |
| 32-layer KV pipeline, two streams | 8561.0 | 8628.9 | 8558.6 | 8553.1 | 7468.3 |
| Four expert MLPs, batch 16 | 231.4 | 183.3 | 231.4 | 151.3 | 120.8 |
| Four expert MLPs, batch 64 | 115.6 | 110.9 | 116.9 | 95.8 | 60.6 |
| Four expert MLPs, batch 64 skewed | 192.3 | 173.4 | 194.7 | 158.7 | 120.6 |
| Matrix MLP + KV scan | 215.4 | 244.9 | 215.7 | 214.6 | 160.1 |
| Two KV scans | 284.8 | 283.6 | 282.9 | 284.6 | 160.4 |

Expected numbers come from stock isolated-stage medians and the actual dependency DAG. They estimate ideal overlap without resource interference; they are not a universal lower bound or a promise of hardware performance. Isolated and combined kernels also have different cache/clock states. The full tables below retain v8-off, eager execution, serial schedules, copy alternatives and batched GEMM.

## What got faster, and what did not

- **Expert graphs:** batch-16 four-stream latency falls from 231.5 to 151.3 us, a 34.6% reduction; the old experimental candidate takes 183.4 us. Batch-64 balanced/skewed improve 18.0%/18.5%. A profiler pass shows the queue count changing from three to four. Two expert chains previously occupied the launch queue and ran in sequence; the revised runtime places one chain on each queue. The same eager schedules already had four queues. This is a graph queue selection defect, separate from native-wait enablement.
- **Streams versus serial:** with the revised runtime, batch-16 expert graphs improve from 407.2 to 151.3 us (2.69x). Sparse KV restore plus resident attention improves from 748.9 to 695.5 us (1.08x). Matrix-plus-KV work improves from 262.1 to 214.6 us (1.22x). These are concurrency gains; only the expert-graph gain above is attributable to the new spare change.
- **Batched control:** batch-16 strided-batched MLPs take about 84 us, faster than separate four-stream MLPs. Their kernel geometry changes, so the independent-expert DAG estimate does not apply. This control prevents treating streams as the best possible implementation for every shape.
- **Small KV pipeline:** two-stream prefetch still provides little benefit. For 32 layers it takes 8,553.1 us versus 8,540.7 us serial. Three streams add overhead. In the diagnostic trace, two streams overlap about 195 of 207 us of gather-kernel time with attention, but attention itself accounts for roughly 8,231 us. The small overlap savings are consumed by increased kernel/coordination time. This trace does not isolate every source of that increase. The optimistic 7,468-us estimate also understates attention cost in the complete sequence.
- **Mixed resources:** overlap is real, but the isolated-stage ideal is too optimistic. In the separate profiler run, matrix kernel time rises from about 93 to 182 us and scan kernel time from 153 to 201 us when concurrent. This supports resource interference; it does not uniquely identify HBM, cache, compute-unit or issue pressure without counters. Two KV scans show the same limitation: some speedup, well short of the no-interference ideal. The scan is memory-heavy, not a demonstrated saturation of peak HBM bandwidth.
- **V8 native-wait on/off:** these new cases mostly track each other. The reproduced expert regression is also present in stock, which points to graph queue selection rather than the new 256-packet admission threshold.
- **Regression scope:** across the 88 final full-schedule rows, the largest revised-versus-v8 increase in median latency is 1.05%. The existing fixed suite reports no total-latency regression exceeding 2% in all three rounds. This is the stated screen, not proof of neutrality for every untested workload or internal gap metric.

## Connection to the supplied HiSparse results

The supplied model results compare whole runtime candidates: c82cf08 additionally changes graph scheduling, marker behavior, spare queue selection and native-wait controls. The microbenchmarks reproduce the direction of a substantial whole-package regression in the four-stream expert case, and isolate a concrete queue collision that can be fixed without importing the whole experimental stack. They do **not** establish that this collision caused the C1/C4 11.88–18.70% model differences.

The small-transfer pipeline retains the useful features for testing that hypothesis: BF16 1,152-byte KV records, a 16-block/1,024-thread GPU gather from pinned host memory, reusable buffers, per-layer event dependencies, small D2H backups, and eager/captured graph paths. It reproduces prefetch failing to help, but not the reported v8-versus-experimental slowdown: v8 is slightly faster than the experimental candidate in these pipeline shapes. GPU planning, TP4 collectives, a real model and the full production graph are outside this microbenchmark.

## Validation and identities

- Final matrix: 60 fresh processes, 40,320 retained timings, three rotated runtime-order rounds, 12 measured trials per cell, four warmups. Full-schedule outputs checked against independent CPU arithmetic. Isolated phases are timed components; their composed output is checked in the complete schedules.
- All schedules reuse the same arithmetic, addresses and transferred bytes. Graph capture, allocation, pinning, CPU references, poison/reset and warmup are excluded from timing. Host submission/completion times remain in CSV alongside GPU intervals.
- Exact HIP/HSA/rocBLAS mappings are hashed per process; c82cf08 marker mode 2 and wait policy 1/interval 4 are verified through its APIs. Hardware queue cap is four for the primary comparisons. No explicit CPU affinity changes. One allocation and one GPU; other GPUs on the node were not reserved by this task.
- Final existing suite: 54 processes; correctness and performance screen passed. Waiter total latency: stock 5,230.8 us, revised enabled 3,222.3 us. Per-round added overhead falls from 2,089–2,095 us to 84–92 us: **95.6–96.0% removed**.
- PyTorch microchecks: 1,280 correctness rows across eight processes, native-wait off/on and hardware queue caps one/four; includes eager event and captured-graph behavior. These are framework microchecks, not a model performance qualification.
- Diagnostic profiling is separate from primary timings. Kernel timeline numbers above are explicitly profiler results; raw diagnostic timing CSVs are retained and are not mixed into the final medians.
- Initial pilot compilation needed a macro-variable rename. The first runtime build invocation omitted the Python dependency path for its build phase; the corrected build used the existing pinned dependency directory. Both attempts and successful logs are retained. No measurement failures or samples were filtered from the final matrix.

| Runtime | HIP SHA-256 |
|---|---|
| Stock ROCm 7.2.4 | `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac` |
| Exact PR1 v8, 77c75b8 | `d0a78f9a1cf0afb3e213c9f2e2f7c326ef0270a7f59a29c149057b6e8c63ac35` |
| Previous experimental, c82cf08 | `ad99498d98335d4a8b1f3bb2201fae09f7d39f333f43c7c347403bb50cab4fd2` |
| Revised v8 plus bounded spare | `496f497674390218403c946026713663c33c46b6c3cef5eb66e8d5e7d3cb2c9c` |

All HSA hashes: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.

## Code, artifacts and package status

Runtime fix commit: `f76a622aa56976f3ec9f238373cce28a17a83ed4`, `hipamd/src/hip_graph_internal.cpp`. It gives segmented graphs one extra candidate stream on the instantiation device, respects the existing graph queue cap, retains the collision fallback, and retries the required count if allocation of the optional spare fails. It does not change the native-wait admission rule. The tested runtime was built from 77c75b8 plus the identical `candidate-spare-v2.patch`; its embedded version string remains 77c75b8, so the library hash is the authoritative binary identity.

The internal PR receives the source fix and these microbenchmarks. The pinned release recipe in `tools/marlowe-runtime/source-lock.json` still selects the existing v8 package. **That existing package does not acquire this fix by pulling the PR.** The measured revised library is a separate preview build, not a newly qualified production package. Packaging and full-model validation are not part of this first microbenchmark round.

- Source: `tools/marlowe-runtime/benchmarks/llm_streams/` (README, producer, runner and analyzer).
- Local artifact root: `/home/sashawork/dev/amd-runtime-production/iterations/llm-streams-round1-20260917`.
- Remote artifact root: `/workspace/home/sasha/amd-runtime-production/iterations/llm-streams-round1-20260917`.
- Measured preview libraries: remote `candidate-v2-lib/`; use its HIP and the recorded ROCm HSA with `GPU_NATIVE_EVENT_WAIT=1`. They were compiled with the same ROCm 7.2.4 build settings as v8.
- Final raw measurements, per-process identity receipts and references: `measurements-final/`; complete derived tables: `totals.csv` and `analysis.json` within it.
- Existing regression controls: `final-existing-controls/`; framework results: `candidate-framework/`.
- Traces: `diagnostic-profile-on/`, `profile-final-experts/`, `profile-final-pipeline/`, `profile-final-mixed/`; derived timeline metrics: `profile-analysis.json`.
- Earlier measured producer/candidate rounds remain in `measurements-round1/` and `measurements-revised/`; queue-cap diagnostics remain in `diagnostic-queuecap/`. They are separate from final primary numbers. Raising the queue cap alone improved some schedules and regressed others, so it was not adopted as the fix.

## Complete captured-graph results

Each row is a median of fresh-process medians, in microseconds. Expected values use the stock isolated-stage model described in the producer README. “—” means a distinct batched-kernel implementation with no independently modeled expectation.

| Case | Shape | Schedule | Stock | V8 off | V8 on | Experimental | Revised | Expected |
|---|---|---|---:|---:|---:|---:|---:|---:|
| attention_fetch | h128-miss128-r1152 | gather-parallel | 703.0 | 704.7 | 704.9 | 738.1 | 704.9 | 670.2 |
| attention_fetch | h128-miss128-r1152 | gather-serial | 750.6 | 751.4 | 749.7 | 751.3 | 750.8 | 741.2 |
| attention_fetch | h128-miss128-r1152 | memcpy-parallel | 718.4 | 725.1 | 714.4 | 731.0 | 721.8 | 669.8 |
| attention_fetch | h128-miss128-r1152 | memcpy-serial | 1022.3 | 1021.9 | 1019.8 | 1024.5 | 1021.8 | 1002.5 |
| attention_fetch | h32-miss128-r1152 | gather-parallel | 699.6 | 695.8 | 696.2 | 731.3 | 695.5 | 668.4 |
| attention_fetch | h32-miss128-r1152 | gather-serial | 750.0 | 750.0 | 749.8 | 748.6 | 748.9 | 739.3 |
| attention_fetch | h32-miss128-r1152 | memcpy-parallel | 704.1 | 705.2 | 703.6 | 714.6 | 700.0 | 668.4 |
| attention_fetch | h32-miss128-r1152 | memcpy-serial | 1022.6 | 1021.4 | 1020.2 | 1019.6 | 1019.7 | 1000.9 |
| attention_fetch | h32-miss128-r584 | gather-parallel | 596.0 | 595.5 | 595.9 | 629.7 | 593.7 | 580.2 |
| attention_fetch | h32-miss128-r584 | gather-serial | 633.9 | 634.3 | 635.1 | 634.4 | 635.3 | 643.9 |
| attention_fetch | h32-miss128-r584 | memcpy-parallel | 602.5 | 604.2 | 604.3 | 615.3 | 603.3 | 580.1 |
| attention_fetch | h32-miss128-r584 | memcpy-serial | 902.6 | 903.4 | 903.9 | 902.5 | 905.4 | 904.9 |
| attention_fetch | h32-miss256-r1152 | gather-parallel | 690.0 | 689.5 | 691.2 | 729.5 | 690.6 | 625.0 |
| attention_fetch | h32-miss256-r1152 | gather-serial | 792.0 | 792.6 | 793.2 | 792.8 | 791.5 | 741.2 |
| attention_fetch | h32-miss256-r1152 | memcpy-parallel | 734.5 | 737.1 | 731.8 | 740.7 | 733.7 | 655.2 |
| attention_fetch | h32-miss256-r1152 | memcpy-serial | 1337.2 | 1341.3 | 1336.2 | 1341.9 | 1340.8 | 1267.7 |
| attention_fetch | h32-miss32-r1152 | gather-parallel | 703.8 | 701.5 | 703.3 | 747.9 | 705.2 | 699.4 |
| attention_fetch | h32-miss32-r1152 | gather-serial | 717.6 | 718.5 | 718.7 | 718.2 | 718.5 | 736.3 |
| attention_fetch | h32-miss32-r1152 | memcpy-parallel | 706.7 | 706.1 | 705.2 | 749.4 | 704.5 | 700.2 |
| attention_fetch | h32-miss32-r1152 | memcpy-serial | 783.2 | 783.7 | 784.0 | 784.0 | 784.3 | 800.2 |
| experts | b16-balanced | 1_streams | 407.7 | 407.1 | 407.1 | 406.6 | 407.2 | 443.1 |
| experts | b16-balanced | 2_streams | 228.1 | 229.8 | 226.9 | 268.8 | 228.6 | 228.1 |
| experts | b16-balanced | 4_streams | 231.4 | 231.7 | 231.4 | 183.3 | 151.3 | 120.8 |
| experts | b16-balanced | batched | 84.0 | 83.8 | 83.9 | 84.0 | 83.9 | — |
| experts | b64-balanced | 1_streams | 166.9 | 167.3 | 166.9 | 167.3 | 167.1 | 202.4 |
| experts | b64-balanced | 2_streams | 110.7 | 110.3 | 111.1 | 118.4 | 110.6 | 107.8 |
| experts | b64-balanced | 4_streams | 115.6 | 116.6 | 116.9 | 110.9 | 95.8 | 60.6 |
| experts | b64-balanced | batched | 95.1 | 95.2 | 95.6 | 95.4 | 95.5 | — |
| experts | b64-skewed | 1_streams | 304.5 | 306.3 | 308.5 | 305.7 | 303.8 | 322.8 |
| experts | b64-skewed | 2_streams | 192.6 | 194.2 | 193.8 | 199.2 | 192.8 | 168.2 |
| experts | b64-skewed | 4_streams | 192.3 | 193.5 | 194.7 | 173.4 | 158.7 | 120.6 |
| mixed | kv-kv | parallel | 284.8 | 279.6 | 282.9 | 283.6 | 284.6 | 160.4 |
| mixed | kv-kv | serial | 318.1 | 312.3 | 318.8 | 315.4 | 318.5 | 319.4 |
| mixed | matrix-kv | parallel | 215.4 | 212.3 | 215.7 | 244.9 | 214.6 | 160.1 |
| mixed | matrix-kv | serial | 263.0 | 256.5 | 263.0 | 261.5 | 262.1 | 262.2 |
| pipeline | h128-l8-miss128 | serial | 2144.6 | 2143.8 | 2144.1 | 2146.7 | 2142.4 | 2093.8 |
| pipeline | h128-l8-miss128 | three_streams | 2177.1 | 2180.1 | 2178.0 | 2235.9 | 2177.1 | 1892.8 |
| pipeline | h128-l8-miss128 | two_streams | 2160.1 | 2161.3 | 2159.5 | 2222.5 | 2160.0 | 1892.8 |
| pipeline | h32-l32-miss128 | serial | 8551.0 | 8546.7 | 8546.6 | 8550.3 | 8540.7 | 8357.4 |
| pipeline | h32-l32-miss128 | three_streams | 8670.1 | 8668.2 | 8666.2 | 8695.1 | 8669.7 | 7468.3 |
| pipeline | h32-l32-miss128 | two_streams | 8561.0 | 8567.0 | 8558.6 | 8628.9 | 8553.1 | 7468.3 |
| pipeline | h32-l8-miss32 | serial | 1674.3 | 1675.0 | 1674.0 | 1675.0 | 1674.5 | 1822.3 |
| pipeline | h32-l8-miss32 | three_streams | 1705.0 | 1704.7 | 1705.5 | 1758.7 | 1704.7 | 1629.7 |
| pipeline | h32-l8-miss32 | two_streams | 1690.0 | 1690.0 | 1689.0 | 1755.8 | 1688.3 | 1629.7 |

## Complete eager results

| Case | Shape | Schedule | Stock | V8 off | V8 on | Experimental | Revised | Expected |
|---|---|---|---:|---:|---:|---:|---:|---:|
| attention_fetch | h128-miss128-r1152 | gather-parallel | 694.2 | 695.8 | 696.0 | 699.5 | 696.3 | 657.2 |
| attention_fetch | h128-miss128-r1152 | gather-serial | 743.4 | 745.1 | 743.0 | 744.3 | 743.9 | 714.5 |
| attention_fetch | h128-miss128-r1152 | memcpy-parallel | 957.3 | 957.8 | 957.4 | 956.8 | 955.0 | 655.8 |
| attention_fetch | h128-miss128-r1152 | memcpy-serial | 1021.6 | 1019.6 | 1018.4 | 1018.7 | 1017.2 | 974.8 |
| attention_fetch | h32-miss128-r1152 | gather-parallel | 690.4 | 691.3 | 691.7 | 691.1 | 688.5 | 654.7 |
| attention_fetch | h32-miss128-r1152 | gather-serial | 744.2 | 742.2 | 743.2 | 742.2 | 743.4 | 711.8 |
| attention_fetch | h32-miss128-r1152 | memcpy-parallel | 955.6 | 951.8 | 954.5 | 956.5 | 950.3 | 654.7 |
| attention_fetch | h32-miss128-r1152 | memcpy-serial | 1018.4 | 1017.3 | 1018.0 | 1017.8 | 1014.7 | 973.8 |
| attention_fetch | h32-miss128-r584 | gather-parallel | 585.6 | 585.5 | 587.3 | 589.8 | 587.3 | 567.0 |
| attention_fetch | h32-miss128-r584 | gather-serial | 628.1 | 628.0 | 628.9 | 628.4 | 629.4 | 617.0 |
| attention_fetch | h32-miss128-r584 | memcpy-parallel | 869.0 | 864.2 | 864.4 | 866.8 | 862.9 | 565.8 |
| attention_fetch | h32-miss128-r584 | memcpy-serial | 905.8 | 901.2 | 902.4 | 902.9 | 904.0 | 891.4 |
| attention_fetch | h32-miss256-r1152 | gather-parallel | 677.9 | 683.4 | 683.2 | 684.9 | 685.8 | 611.1 |
| attention_fetch | h32-miss256-r1152 | gather-serial | 786.2 | 786.7 | 786.7 | 787.2 | 786.5 | 713.5 |
| attention_fetch | h32-miss256-r1152 | memcpy-parallel | 1217.9 | 1214.7 | 1213.7 | 1216.6 | 1211.9 | 638.9 |
| attention_fetch | h32-miss256-r1152 | memcpy-serial | 1341.5 | 1340.5 | 1338.8 | 1341.5 | 1337.3 | 1244.2 |
| attention_fetch | h32-miss32-r1152 | gather-parallel | 698.0 | 696.4 | 697.4 | 700.3 | 695.3 | 686.6 |
| attention_fetch | h32-miss32-r1152 | gather-serial | 711.1 | 711.9 | 711.5 | 710.7 | 712.0 | 710.0 |
| attention_fetch | h32-miss32-r1152 | memcpy-parallel | 763.0 | 761.8 | 765.0 | 766.1 | 763.5 | 686.9 |
| attention_fetch | h32-miss32-r1152 | memcpy-serial | 776.6 | 778.1 | 777.9 | 777.0 | 776.2 | 773.8 |
| experts | b16-balanced | 1_streams | 414.2 | 415.4 | 413.8 | 412.8 | 412.8 | 427.1 |
| experts | b16-balanced | 2_streams | 243.5 | 243.5 | 243.0 | 287.6 | 242.3 | 216.9 |
| experts | b16-balanced | 4_streams | 195.5 | 192.7 | 191.7 | 214.1 | 191.8 | 111.5 |
| experts | b16-balanced | batched | 82.7 | 83.1 | 82.6 | 82.6 | 82.6 | — |
| experts | b64-balanced | 1_streams | 174.1 | 175.2 | 174.5 | 174.1 | 173.9 | 184.8 |
| experts | b64-balanced | 2_streams | 126.4 | 126.1 | 125.9 | 169.3 | 125.5 | 95.7 |
| experts | b64-balanced | 4_streams | 124.7 | 122.7 | 121.3 | 141.2 | 121.8 | 51.2 |
| experts | b64-balanced | batched | 94.1 | 94.5 | 95.6 | 94.4 | 94.3 | — |
| experts | b64-skewed | 1_streams | 311.5 | 310.8 | 312.2 | 311.3 | 309.0 | 305.4 |
| experts | b64-skewed | 2_streams | 198.7 | 198.7 | 198.7 | 265.2 | 196.4 | 155.8 |
| experts | b64-skewed | 4_streams | 191.3 | 190.4 | 192.3 | 208.8 | 191.2 | 110.9 |
| mixed | kv-kv | parallel | 284.2 | 280.2 | 284.6 | 286.9 | 284.3 | 153.1 |
| mixed | kv-kv | serial | 311.7 | 305.7 | 311.4 | 309.5 | 311.4 | 305.6 |
| mixed | matrix-kv | parallel | 224.4 | 218.6 | 224.0 | 274.0 | 224.0 | 153.1 |
| mixed | matrix-kv | serial | 260.9 | 254.7 | 261.6 | 259.8 | 261.5 | 254.3 |
| pipeline | h128-l8-miss128 | serial | 2147.5 | 2146.9 | 2145.0 | 2148.5 | 2147.8 | 1924.2 |
| pipeline | h128-l8-miss128 | three_streams | 2261.4 | 2259.0 | 2259.7 | 2354.3 | 2260.9 | 1819.6 |
| pipeline | h128-l8-miss128 | two_streams | 2251.6 | 2253.7 | 2253.6 | 2355.3 | 2252.4 | 1819.6 |
| pipeline | h32-l32-miss128 | serial | 8552.9 | 8551.8 | 8556.6 | 8554.4 | 8556.0 | 7714.2 |
| pipeline | h32-l32-miss128 | three_streams | 8914.1 | 8909.6 | 8912.7 | 8962.4 | 8913.0 | 7248.5 |
| pipeline | h32-l32-miss128 | two_streams | 8872.9 | 8862.1 | 8870.0 | 8957.9 | 8863.3 | 7248.5 |
| pipeline | h32-l8-miss32 | serial | 1674.4 | 1675.4 | 1674.6 | 1674.5 | 1674.6 | 1663.3 |
| pipeline | h32-l8-miss32 | three_streams | 1792.9 | 1792.1 | 1793.0 | 1870.6 | 1792.7 | 1566.1 |
| pipeline | h32-l8-miss32 | two_streams | 1783.6 | 1784.0 | 1783.4 | 1883.0 | 1783.2 | 1566.1 |
