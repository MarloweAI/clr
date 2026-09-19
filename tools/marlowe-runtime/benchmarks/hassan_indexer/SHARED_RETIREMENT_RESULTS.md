# Logical mapping and shared retirement — job 53091

The diagnostic passes the original Hassan graph performance screen: 19.107965 us versus stock 19.903241 us, a 3.996% improvement. All four round comparisons improve GPU time by 3.83–5.15%; host time agrees. This qualifies the bounded workload experiment, not a production placement policy or other workloads.

Four balanced process orders compare stock with three settings of one new runtime binary. Original kernels, four-node graph, scheduler, dispatch, tensor identities and 200-replay protocol are unchanged. Timings use one GPU on node2. The two-GPU allocation additionally supports untimed retained-stream invalidation checks.

| Setting | Graph GPU us | Graph host us | CPU submission us |
| --- | ---: | ---: | ---: |
| Stock | 19.903241 | 19.943105 | 4.663239 |
| New binary, both diagnostics off | 22.186060 | 22.225018 | 4.668625 |
| Same binary, one logical stream | 20.174746 | 20.212943 | 3.384215 |
| Same binary, one stream and shared retirement | 19.107965 | 19.148080 | 2.513226 |

Logical coalescing saves 2.011314 us GPU. Sharing the retirement command across the original ordered segments saves another 1.066781 us GPU and 0.870989 us CPU submission. The latter intervention changes command allocation, completion signals/handlers, barriers and publication behavior together; it does not isolate the CPU allocator or identify a measured barrier duration. Each segment still publishes its original AQL packet batches separately.

The off/stock comparison reproduces the approximately 11.47% regression. Native wait and existing placement/spare controls remain fixed across the three new-binary arms. This is a sequence of conditional interventions, not a complete two-factor grid: the generic runner's saved `interaction` field has no factorial interpretation and is not used as evidence.

## Correctness and scope

Remote and local audits pass all 16 timing processes, 256 retained timing rows and 320 numerical checks. Exact source/artifact hashes, mapped libraries, dispatch and input identities are retained. There are also 54 existing fixture processes with 1,404 correctness rows across queue caps 1/4/8, three retained-stream fixture processes with 42 checks, and three untimed original-graph mapping/retirement proofs.

The mapping guard now matches instantiation and launch devices. Both replay entry paths refresh cached mapping if eligibility changes while the same launch stream remains alive. The new fixture covers successful executable parameter changes, source-graph-only updates, rejected wrong-device executable setters and restore, reinstantiate, and switching between retained launch streams. It does not execute a graph across devices.

Shared retirement is a default-off diagnostic confined to eligible flat captured kernel graphs mapped to one logical launch stream, normal HIP direct dispatch, and excluded profiler modes. Source review found no ownership blocker within that scope. Broader admission must exclude forced asynchronous packet controls or verify packet barrier headers. Per-kernel profiler metadata is incomplete when one accumulator is reused, so profiling exclusions remain essential. Partial-failure retirement is source-reviewed; exact-byte injected-failure testing remains outstanding.

No global serialization policy is justified. The next architectural task is choosing one versus multiple logical streams while preserving overlap-positive workloads. Balanced expert, broader stream/transfer microbenchmarks, waiter, PyTorch and HiSparse qualification are outstanding for these bytes. The production runtime in PR1 is unchanged.

HIP SHA256: `862f3cd7eded1e9cd4f4f2037f83de0871a36c27afca3c880b9d658a5c895473`; HSA: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Timing spec: `0cb3e5d452a05d3c9160d2bf7a125276417b5cb26fa703e2748f7bcb36ee1545`.

Frozen source/patch/scripts: `iterations/hassan-qk-micro-20260918/logical-coalesce-v2*`, `logical_coalesce_v2_bench`, `run_logical_coalesce_v2.py`. Raw: `logical-coalesce-v2-j53091`. Slurm completed 0:0; standalone monitor validated completion. No live root allocation remains.
