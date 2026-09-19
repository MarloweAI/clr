# Recovered RC1 and clean rebuild — September 19 checkpoint

**Model qualification remains incomplete.** The clean rebuild preserves recovered RC1 in this microbenchmark cohort, including its two stock-relative regressions. It is separate from the newer V10 graph-frontier experiment.

Node2 job55940 completed0:0: 192 fresh processes, four rotated runtime orders, 61,952 retained timing rows, all numerical and mapped-library checks passed. The table uses medians of four process medians; no trials were removed. Of294 measured cells,158 measure complete workloads; isolated-stage rows remain in the raw report. A two-percent screen is not an equivalence proof.

| Complete workload | Stock µs | Recovered RC1 µs | Clean on µs | Clean off µs | Clean on / stock |
| --- | ---: | ---: | ---: | ---: | ---: |
| Waiter producer alone | 3168.859 | 3162.077 | 3157.647 | 3145.060 | -0.35% |
| Waiter producer with pending waiter | 5245.373 | 3242.730 | 3239.032 | 5252.112 | -38.25% |
| Hassan serial, one pair | 13.450 | 13.347 | 13.416 | 13.532 | -0.25% |
| Hassan two streams, one pair | 14.106 | 21.567 | 21.540 | 21.491 | +52.70% |
| Hassan serial, 50-pair graph (per pair) | 8.929 | 8.847 | 8.922 | 8.907 | -0.07% |
| Hassan two streams, 50-pair graph (per pair) | 10.083 | 10.093 | 10.093 | 10.059 | +0.09% |
| Balanced experts, batch64, two streams, graph | 110.763 | 115.104 | 115.314 | 115.424 | +4.11% |

Waiter overhead means pending-wait minus producer-alone within each runtime. This falls from 2076.514µs on stock to 81.385µs on clean-on: **96.08% removed**. Total producer elapsed time with a pending waiter improves 38.25%; those are different statistics.

| Family | Complete-workload cells | Clean >2% slower than stock | Worst clean / recovered RC1 |
| --- | ---: | ---: | ---: |
| attention_fetch | 40 | 0 | +0.26% |
| attention_fork_join | 9 | 0 | +0.19% |
| attention_stream_chains | 42 | 0 | +0.30% |
| experts | 22 | 1 | +0.80% |
| grouped_prefetch | 12 | 0 | +0.04% |
| hassan | 4 | 1 | +0.85% |
| mixed | 8 | 0 | +0.35% |
| pipeline | 18 | 0 | +0.21% |
| waiter | 3 | 0 | -0.11% |

All158 complete-workload cells stay within0.85% slowdown of recovered RC1. The two stock-relative failures remain visible above; candidate-off also retains graph entry/completion changes, so disabling the optional policies is not stock rollback. This cohort does not establish the mechanism of either regression.

For context, the separate V10 checkpoint measured Hassan two-stream1/50-pair graphs at10.207/7.208µs per pair versus its matched stock14.273/10.087. That uses a different runtime/HSA implementation and a separate cohort. Its gains are not attributed to this branch. The implementation and full report remain in PR1 under `tools/marlowe-runtime/benchmarks/hassan_indexer/graph_frontier_probe/QUALIFICATION-v10.md`.

## Identities and remaining work

Runtime-only source commit: `cd7f4ee9bd8a425139904c45fc5de3386f42f74a`; micro runner commit: `bdadee8705d8d47ff0ec991f3904ccc89446f68a`. Both optional policies are1/1 in clean-on and recovered-reference,0/0 in clean-off. Queue cap4, direct dispatch1, native tracing0, stream-memory CP wait0. CPU affinity is inherited. Hassan warms the actual capture stream; grouped50 is a synthetic control. Grouped prefetch here uses default depth1; prior depth8/wider-grid diagnostics are not implicitly covered.

| Arm | HIP SHA256 | HSA SHA256 |
| --- | --- | --- |
| stock | `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac` | `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4` |
| reference | `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04` | `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4` |
| on | `f13cd3eb6deda8c3af4e174d91949d2e357ca75645cfaa29555fb0e9db6b4812` | `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4` |

Rebuilt-byte correctness job55922 passed120 lifecycle/PyTorch/pool/publication processes plus2 two-device invalidation processes. This is correctness evidence, separate from performance. Fresh retained HiSparse C1/C4 and standard GLM without HiSparse remain pending; the latter currently screens the exact recovered package before a rebuilt-byte model bridge. No production qualification is claimed.

Raw artifacts and all294 cell comparisons: `/workspace/home/sasha/amd-runtime-production/iterations/e2e-qualification-20260919/clean-micro-j55940` (mirrored under the same suffix in `/home/sashawork/dev/amd-runtime-production`). `performance-summary.json` retains round medians; `performance-cells.csv` contains every cell. Source/binary/control/identity receipts and all raw rows remain alongside them. Manifest SHA256: `1c93f29a611f42e3128d4bc1725a2742a766a84e51e26faa4528202859562ca6`.
