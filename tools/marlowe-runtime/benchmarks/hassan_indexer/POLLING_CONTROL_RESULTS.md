# Hassan Q/K: graph boundaries and GPU polling

2026-09-18. Stock-only diagnostic job 54181, node2, one GPU. Slurm 0:0; remote finalizer and independent local audit PASS. Original Q/K GEMMs, dispatch configurations and BF16 inputs are unchanged. This is a separate C++ submission-loop protocol, not a replacement for the original Python-replay benchmark.

**GPU polling reduces the matched split-graph event case by 30.63%, but still does not make the two-stream workload faster than serial or the unsplit graph.** The user-provided long-producer reproduction predicts a useful mechanism, not an automatic short-dependency/full-model win.

| Execution | GPU µs/pair | CPU submission µs/pair | Host total µs/pair |
|---|---:|---:|---:|
| One graph, serial Q then K | 13.694 | 1.733 | 13.732 |
| One graph, two streams | 14.254 | 3.659 | 14.293 |
| 50 pairs/graph, serial | 8.952 | 0.091 | 8.990 |
| 50 pairs/graph, two streams | 10.071 | 5.457 | 10.123 |
| Separate Q/K graphs, serial | 18.465 | 3.313 | 18.504 |
| Separate Q/K graphs, event waits | 30.263 | 6.251 | 30.303 |
| Separate Q/K graphs, GPU polling | 20.993 | 13.103 | 21.028 |
| Separate Q/K graphs, CP memory waits | 31.386 | 9.658 | 31.424 |

Poll vs event at identical split boundaries: -9.270 µs/pair (-30.63%); all four round deltas improve. Poll vs CP with identical stream-memory calls and signal-generation protocol: -10.393 µs/pair (-33.11%). Split polling remains 13.69% slower than split serial and 47.27% slower than the unsplit two-stream graph. Serial splitting alone costs 4.771 µs/pair. CPU submission is higher for polling (13.103µs) than events (6.251µs), despite lower GPU elapsed; do not call polling universally cheaper or attribute all wall time to firmware.

Interpretation: breaking the graph and replacing waits are distinct changes. Event vs polling uses exactly the same two graph boundaries and ready/join dependencies. Poll vs CP uses the same writes, memory, counters and launches. It changes only the runtime wait implementation. The remaining loss can include graph entry/exit packets, signal writes, wait-kernel launches, memory ordering and host supply. This test does not separate those costs or establish a firmware bug. It also does not prove Q/K overlap; the earlier independently calibrated stock wave timeline supplies evidence of overlap only for its own protocol.

Implementation: native HIP stream-memory APIs execute outside graph capture. Main writes ready, launches Q; side waits ready, launches K and writes done; main waits done before the next pair. Two signal-memory words use strictly increasing 32-bit generations, with final values checked. The existing stock [wait implementation](https://github.com/ROCm/clr/blob/rocm-7.2.4/rocclr/device/rocm/rocvirtual.cpp#L3169) chooses a compute polling kernel or a CP barrier-value packet. This is distinct from our PM4 native-prewait extension; neither custom native-wait admission nor a new runtime build is used here.

Validation: 32 fresh timing processes in 4 reversed orders, 8 trials/process, 256 timings retained. Eight separate untimed copy-log proofs verify exactly 8 GPU-wait receipts for polling and zero for CP; performance logging is off. 3,180 numerical output checks include changed input publication, initial/final FP32 references and all grouped outputs. Actual capture streams are warmed; DOTs require zero initialization fills and the original Q/K grids. Exact loaded HIP/HSA, AITER source, input data, helper and launch sources are hashed. Independent reviewer found no semantic mismatch in the matched split comparisons.

Identities:

- HIP `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`.
- HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Harness `fc656a2e51f209fb44eb3450b07dc4c253ed491615eb2d118a5fba55e6e35152`.
- Results manifest `2e51a27df43d276302cc15da22ac5648d2f460efe4dfdb5125a58f9bf9e5890f`.

Raw local: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-polling-control-20260918/results-j54181`. Remote mirror: `/workspace/home/sasha/amd-runtime-production/iterations/hassan-polling-control-20260918/results-j54181`. Reproduce with frozen `polling_control/` sources and documented container path.

Next architectural question: can the runtime preserve the unified graph while eliminating redundant completion/notification packets and, if needed, use a GPU waiter against the already-existing producer completion signal? That could avoid split-graph API/write costs. It requires signal lifetime, queue-alias/progress, full-width condition and memory-scope proofs before timing. No such GPU-polling runtime candidate is implemented or qualified by this result.
