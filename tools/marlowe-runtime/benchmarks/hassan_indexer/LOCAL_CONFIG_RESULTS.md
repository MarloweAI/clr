# Same-byte configuration control — job 55272

**Removing the inherited graph optimizations does not recover the original-sized short case. It makes it about 29% slower.** The grouped local-signal win survives, and native wait on/off is nearly neutral within the minimal configuration. Keep the full configuration as the best of these candidates; none qualifies for Goal 1.

Job 55272 completed 0:0 on node2, one GPU. Remote and local strict audits pass 10 lifecycle/failure fixtures, 16 untimed path proofs, 80 timing processes, 640 retained timing trials and 14,688 numerical rows. The same HIP/HSA bytes as 55216 were used. Benchmark, scheduler, kernel configurations, inputs and fixtures are unchanged from that frozen warm g1/g50 protocol. The 50-pair graph is synthetic; it is not Hassan's unchanged serving application.

| Microbenchmark graph | Stock | Full local candidate | Minimal, local off / native on | Minimal, local on / native on | Minimal, local on / native off |
|---|---:|---:|---:|---:|---:|
| Serial, one pair | 13.481339 | 12.490313 | 13.487440 | 13.501890 | 13.504889 |
| Two streams, one pair | 14.105010 | **16.676841** | 21.485256 | 21.555656 | 21.442150 |
| Serial, 50 pairs | 8.782491 | 8.695235 | 8.719535 | 8.787338 | 8.713135 |
| Two streams, 50 pairs | 9.980575 | **7.442394** | 11.155414 | 7.447145 | 7.463295 |

GPU-event elapsed µs per Q/K pair; lower is better. Values are medians of four round medians, eight trials per cell, 200 pairs per trial. All fixed trials are retained. The four orders reverse/rotate treatments but are not a complete Williams balance for five treatments; use round stability rather than an inferential significance claim.

## What this closes

- The full candidate reproduces the grouped win: −25.43% against contemporaneous stock, with all four paired rounds improving 25.04–25.99%. Its short two-stream regression also reproduces: +18.23%, worse in every round.
- Disabling six parent controls together makes short two-stream execution 29.26% slower (28.27–30.51% in every round). Those controls are node-count placement, lane retirement, covered-tail omission, dependency fusion, final fusion and kernel retirement. This is a bundle result; it does not attribute the effect to one component.
- Enabling local signals inside the minimal configuration improves the grouped case 33.24% against the same-byte local-off control, while changing the short case only +0.33%. Untimed proofs confirm that the short graph never enters the local path.
- Within the minimal/local configuration, turning native waits off changes the short case −0.53% and grouped case +0.22%; paired rounds have mixed signs. Native-wait disablement does not fix this configuration. A full-parent/native-off arm was not tested, so no universal interaction claim follows.
- The full and minimal/local configurations have essentially the same grouped time (7.442 vs 7.447), showing that the new token path's grouped benefit does not depend on the removed parent optimizations.

Host elapsed tracks these conclusions. Short full/minimal-native1/minimal-native0 is 16.716868/21.594955/21.483330 µs/pair. Grouped full/minimal-native1/minimal-native0 is 7.478703/7.483403/7.507301. Short CPU submission is 3.973650/4.516825/4.459593; grouped is 1.263176/1.250751/1.255413. CPU submission alone does not explain the large short-case gap.

## Verification and interpretation

Spare-queue policy and forced segmented scheduling remain fixed in every new-binary arm. Each two-stream proof verifies two distinct physical queues, the requested spare policy, and no logical coalescing. Each positive grouped local proof executes four graph launches, 400 original kernel packets, 392 cross-queue waits and GPU-local signal arenas. Serial proofs use one physical queue; short/serial proofs take no local-token path. Timing disables tracing; timed path behavior is inferred from matched untimed proofs with trace as the only control difference.

The new graph-entry ordering repair remains enabled even in minimal arms. Minimal is therefore not a rebuilt stock runtime. Removing that correctness requirement would invalidate asynchronous input visibility rather than solve performance. All changed configurations passed update/disable, alternate launch stream, destruction-before-sync, multiple in-flight generations and partial-publication failure screens before timing. These remain bounded tests, not production qualification.

Do not deploy the minimal configuration or add a workload threshold to hide its regression. The remaining original-sized case has no internal cross-queue edge, so the successful internal-token mechanism is not used there. The next useful architecture question is the cost of a graph's entry fork and final host retirement. A cheaper boundary must preserve the launch predecessor, both compute branches, memory visibility and all host lifetimes. `NEXT_GRAPH_BOUNDARY.md` records that bounded investigation; no new runtime or GPU job is included in it.

## Provenance

- HIP: `69f3df4efac18f3429ddc5951bdeb2d0dd821f8f1489bb78fb90e2f6dc8da254`.
- Private HSA: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- Harness manifest: `1cdb52ceb5df2be4f7c51ba335e0b3ed0f2c0a7ed4053523262b9372b681786e`.
- Raw manifest: `a4f86cd34cd20a7177352d45bbdc1e708547a40cc6f6a120945960688acd73a6`.

Task directory `/home/sashawork/dev/amd-runtime-production/iterations/hassan-local-config-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Raw `results-j55272`. `python3 run.py --out results-j55272 --audit` revalidates; `PERFORMANCE_CHECK.json` records derived contrasts. Source/build provenance is unchanged from 55216, including the separate private-HSA build. The prior independent review endorsed this control design; its follow-up invocation hit the agent thread limit, so this run has root prelaunch/post-run review and automated remote/local validation, not a new independent post-run review.
