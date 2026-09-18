# One logical launch stream — job 53029

Assigning the unchanged event graph to one logical launch stream recovers most of its current-runtime regression. It is not yet a passing or production-qualified configuration: two rounds exceed the 2% performance limit, and review found update/device-fallback scope holes outside the fixed-graph experiment.

Original kernels, inputs, scheduler and 200-replay protocol remain unchanged. Four balanced rounds compare stock, the immutable current parent, and one new diagnostic binary with the logical-coalescing switch off/on. All 16 timing processes, 256 timing rows and 320 numerical checks pass the existing artifact/source/library audit. A separate set of 36 entry/tail/lifecycle/transfer/publication/disabled-root fixture processes passes across queue caps1/4/8. Those fixtures do not cover every update/device fallback.

| Runtime configuration | Graph GPU us | Graph host us | CPU submit us |
| --- | ---: | ---: | ---: |
| Stock | 19.913642 | 19.959366 | 4.671400 |
| Immutable current parent | 22.147719 | 22.195130 | 4.637865 |
| New diagnostic, coalescing off | 22.057503 | 22.103893 | 4.700388 |
| Identical diagnostic bytes, coalescing on | 20.261650 | 20.307180 | 3.321351 |

The same-byte intervention saves1.795853us GPU. Rebuild-off versus parent is −0.407% aggregate GPU, within±0.64% in every round; host agrees. Coalescing-on versus stock is +1.748% aggregate GPU, but per-round losses are2.109%,2.236%,1.217%,1.866%. Host also exceeds2% in the first two rounds. **The predeclared all-round performance screen fails.** Eager execution is unaffected structurally and remains near50us, dominated by host submission; no eager-path optimization is claimed.

Separate untimed receipts verify two logical/physical streams with the switch off and one logical/physical launch stream with it on. The captured graph still has four kernels and the original edges. Unlike the failed physical-cap experiment, logical coalescing makes root/internal/final cross-stream dependency lists unnecessary. Topological segment enqueue order remains unchanged.

## Scope and review

This is an unconditional structural diagnostic for eligible flat captured kernel graphs on one device. It is not a policy that should be enabled for every graph: other microbenchmarks benefit from parallel queues. No HiSparse, waiter or broad microbenchmark qualification transfers to these bytes.

Source review identified two blockers to general qualification: the guard must explicitly match instantiation and launch devices, and cached coalesced stream mappings must refresh when executable eligibility is invalidated even if the launch stream pointer is unchanged. Existing invalidation coverage creates fresh streams and misses the latter case. The fixed same-device, unchanged graphs in this experiment do not exercise either hole.

The next diagnostic will address those guards and test whether the serial mapping can share one retirement command across consecutive segments. Current source still creates/enqueues an accumulator per segment even after assigning both to one stream. This is a concrete remaining difference from the original serial graph, not yet a measured attribution of its residual cost. Preserve topology, changed-input ordering, failed-prefix retirement and callback lifetime; do not remove required graph completion.

A future general planner must choose parallel lanes when overlap repays dependency cost. Static resource descriptors alone do not establish kernel duration. Shape/name exceptions, universal serialization, and copying stock's unordered run-ahead are not acceptable substitutes for that architecture.

Diagnostic HIP SHA256: `02397c7e7cf78611b7feb012fa78ce73130110573fbb3f56e32ce3b046bc70aa`. HSA remains `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Timing spec SHA256: `45d134c845b2374923095237a4f4b728945579e526d794fce71ad0e7d8918afc`.

Raw: `iterations/hassan-qk-micro-20260918/logical-coalesce-j53029`; frozen diagnostic source/patch: `logical-coalesce-src`, `logical-coalesce-port.patch`, `logical-coalesce-full.patch`, `logical-coalesce-source.json`. The implementation remains outside the production PR runtime source; this report does not promote it.
