# Hassan Q/K: bounded GPU polling inside the original graph

Job54609, node2, one GPU. Original Q/K GEMMs, shapes, split-K, data and dependency DAG are unchanged; no application graph splitting. All numerical and path checks in the unmasked protocol pass. This is an experimental mechanism test; the per-stream-CU-mask shutdown holdout remains unresolved and full qualification is false.

**Decision: reject this polling variant for Hassan.** Entry polling slows the one-pair two-stream graph by 11.22%; internal polling slows the grouped graph by 17.14%, versus identical runtime bytes with polling off. Both regress in every round. Entry polling is approximately neutral on the grouped case (−0.45%), but remains 1.73% behind stock and 14.31% behind its own serial control. There is no useful new parallel winner and no runtime promotion.

The zero-budget helper already costs 6.21% on the one-pair entry case and 12.47% on the grouped internal case. Letting that helper poll adds another 4.72% and 4.15%, respectively. The experiment therefore exposes both the extra submission/dispatch cost and an additional loss from this polling policy; it does not isolate the latter into a unique firmware or cache mechanism. CPU submission also rises substantially. Do not subtract these controls to invent a constant per-helper GPU cost.

| Runtime / setting | Serial, 1 pair | Two streams, 1 pair | Serial, 50 pairs | Two streams, 50 pairs |
|---|---:|---:|---:|---:|
| Stock HIP (automatic scheduler) | 13.532 | 14.139 | 8.749 | 10.030 |
| Previous K binary | 12.258 | 16.681 | 8.908 | 10.283 |
| New binary, polling off | 12.557 | 16.588 | 8.867 | 10.250 |
| Entry, zero-budget control | 12.546 | 17.618 | 8.924 | 10.263 |
| Entry, 500 µs budget | 12.454 | 18.449 | 8.926 | 10.204 |
| Internal, zero-budget control | 12.370 | 16.670 | 8.830 | 11.528 |
| Internal, 500 µs budget | 12.346 | 16.686 | 8.918 | 12.007 |

GPU µs per original Q/K pair; lower is better. Medians of four process-round medians, eight retained trials each. Group50 amortizes Python/graph launch across 50 pairs while preserving the original fork/join at each pair. All modes use the same frozen HSA library; “stock” means stock HIP. All diagnostics use the same forced segmented scheduler and K features; stock automatic scheduling is an overall reference. New on/off/zero-budget differences are the matched causal comparisons.

| Matched comparison | One-pair graph | Grouped graph |
|---|---:|---:|
| Rebuild / new off vs prior K | -0.56% | -0.32% |
| Entry zero-budget vs off | +6.21% | +0.13% |
| Entry500 vs zero-budget | +4.72% | -0.58% |
| Entry500 vs off | +11.22% | -0.45% |
| Internal zero-budget vs off | +0.50% | +12.47% |
| Internal500 vs zero-budget | +0.10% | +4.15% |
| Internal500 vs off | +0.59% | +17.14% |

Per-round GPU deltas (all four retained):

- entry / off, events-g1: +10.30%, +11.08%, +11.93%, +11.61%.
- entry / entry-zero, events-g1: +3.71%, +5.07%, +5.85%, +4.85%.
- internal / off, events-g50: +17.65%, +13.16%, +17.21%, +15.99%.
- internal / internal-zero, events-g50: +5.13%, +3.07%, +3.58%, +3.30%.

| Setting | CPU submit, two streams / 1 pair | CPU submit, two streams / 50 pairs |
|---|---:|---:|
| Stock HIP (automatic scheduler) | 4.365 | 5.396 |
| Previous K binary | 3.611 | 2.653 |
| New binary, polling off | 3.708 | 2.750 |
| Entry, zero-budget control | 5.602 | 2.745 |
| Entry, 500 µs budget | 5.574 | 2.749 |
| Internal, zero-budget control | 3.628 | 6.650 |
| Internal, 500 µs budget | 3.722 | 6.764 |

CPU submission µs/pair is reported separately. GPU elapsed can include idle time from host supply; this protocol does not label every residual interval as firmware or barrier latency.

The helper is a one-work-item runtime kernel using an acquire HSA signal load, a realtime budget and s_sleep. The existing barrier is always retained. Entry-only and internal-only are separate controls; they are never combined here. Zero budget retains helper dispatch and its initial signal/clock checks but immediately expires if the producer is still pending. It is a dispatch-cost control, not an absence of all wait-related instructions. Actual native PM4 prewait publication suppresses the GPU helper, preventing stacked waits.

Validation: 80 fixture processes, 18 separate detailed/sparse path proofs, 112 timing processes, 896 retained timing trials and 19,890 Q/K numerical checks. Trace/fault controls are off during timing. Detailed proofs verify original two-physical-queue execution, original dependency barriers/scopes, helper descriptor/completion, GPU-observed satisfied/expired outcomes and correct signal generations. Sparse queued proofs require actual nonzero helper publication at each enabled target site. Sparse observations show 399/399 pending entry dependencies receiving helpers in g1,6/6 pending entries in g50, and 980/980 pending internal dependencies receiving helpers in g50. Internal g1 has exactly zero eligible internal edges. Thus the losses are not an unexercised feature. These are separate traced observations, not assumed per-trial timing counts. Captured kernel/data/library hashes are checked. No full-model or broad holdout jobs were run.

Failures are preserved:54519 stopped at an incorrect ready-receipt assertion;54594 stopped at an incorrect assumption that every replay retains an entry candidate. Synchronization can elide the frontier upstream. The final checker permits0..replay-count entry selections while keeping internal graph-edge counts exact and requiring actual helper publication in separate queued proofs.54540 exposed a custom CU-mask shutdown deadlock with no helper running; it also reproduced in prior K and with K retirement disabled. See [shutdown evidence](GRAPH_PREWAIT_SHUTDOWN.md). Final global-mask controls pass on ordinary pooled queues and do not qualify the custom-queue lifetime.

Identity:

- HIP `a44038ab743482b76dcbbd1ea673c3f5f83c0487d9a20054669973a5cbb8488f`.
- HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Source base `cab5670a350678f2b0a6feb388fcbbca56c426a1` + frozen patch `279b749eb622ff8a2f2a3a845640b729dec759d0240d61c10bef1cf2b6435648`.
- Source-content commit `f4b3a00` on internal branch `marlowe/graph-prewait-diagnostic-20260919`; committed after the build, so it identifies matching contents rather than a new binary.
- Manifest `69f77c1eb9af52dce77541cb78f93684445128ab326c77f3009a108196b4cb7d`.

Raw local: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-graph-prewait-20260919/v4/results-j54609`. Remote mirror: `/workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-prewait-20260919/v4/results-j54609`.

Hassan's independent 2048-kernel producer figures remove 90.29% of the added one-waiter penalty and 92.95% with two waiters. That is consistent with the earlier matched split-Q/K control, where GPU polling cut event-wait time 30.63%. Neither predicts a win for frequent short dependencies inside an unsplit graph: the added polling dispatch is poorly amortized here. No full-model reproduction is claimed.

The next source-reviewed hypothesis is [parallel graph layers on one AQL queue](NEXT_SAME_QUEUE_PARALLEL.md): co-publish independent kernels with barrier-free sibling dispatches, preserve layer joins, and retire the whole group with an ordered terminal barrier. This aims to remove cross-queue waits without serializing kernels. It has NOT been implemented or measured, and requires device-timestamp overlap proof before a performance claim.
