# Admission holdouts and denser arrival sweep

2026-09-18. Same HIP `500e91ca76c0b4b6e80a0f7439b9624cf850a286a1763f53697781b9eab14d90`
and HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
Graph ordering and markers are at released-v9 defaults. All timing trials remain;
traces are separate. These diagnostics have no production qualification.

Job50458: node2/one GPU, 90 timing processes/16,500 correctness rows plus
24 trace processes/2,176 rows. Same useful kernels as the existing LLM and queued
suites; only runtime controls change. Full remote per-process coverage, correctness,
compiled trace/control and mapped-hash audit; retained CSV hashes/counts/outputs
and candidate mapped receipts were also rechecked locally.

Medians of three process medians, milliseconds:

| Workload | Stock | Guarded256 | Threshold 32 | Threshold 24 | Cost-relaxed |
|---|---:|---:|---:|---:|---:|
| Grouped prefetch on, 4 kernels/layer, 32 layers, graph | 8.948 | 8.956 | 8.944 | 8.945 | 9.542 |
| Grouped prefetch on, 25 kernels/layer, 32 layers, graph | 11.583 | 11.791 | 11.927 | 11.426 | 11.527 |
| Grouped prefetch on, 25 kernels/layer, 64 layers, graph | 23.101 | 23.644 | 23.900 | 22.767 | 22.959 |
| Grouped prefetch off, 25 kernels/layer, 32 layers, graph | 11.509 | 11.092 | 10.934 | 10.923 | 10.920 |
| Four experts, b16 balanced, graph | 0.2311 | 0.1523 | 0.1518 | 0.1512 | 0.1932 |
| Four experts, b64 balanced, graph | 0.1176 | 0.0964 | 0.0955 | 0.0955 | 0.1404 |
| Four experts, b64 skewed, graph | 0.1916 | 0.1601 | 0.1576 | 0.1569 | 0.1888 |
| Queued attention, two balanced streams, depth16 | 3.149 | 3.154 | 3.150 | 3.152 | 5.947 |
| Queued attention, four balanced streams, depth16 | 3.676 | 3.679 | 3.679 | 3.675 | 6.461 |
| Pending fanout, three consumers, cap4 | 9.976 | 3.560 | 3.568 | 3.575 | 3.575 |

Threshold 24 improves the longer grouped prefetch-on holdout 3.1–3.7% versus guarded,
while preserving shorter grouped, expert, queued and fanout behavior in this screen.
Neither 24 nor 32 has a >2% loss repeated in all three rounds versus guarded.
Threshold 32 is about 1.1% worse on the long grouped prefetch-on cells; it is not
selected merely because it clears a 2% gate. Relaxed still severely regresses the
short dependency controls. All figures remain conditional on these workloads.

Separate trace observations over whole processes include untimed setup/warmup:

| Fixture | Guarded emissions | Threshold 32 | Threshold 24 | Relaxed |
|---|---:|---:|---:|---:|
| Grouped 4 kernels/layer | 153 | 890 | 921 | 5913 |
| Grouped 25 kernels/layer | 1364 | 2328 | 4452 | 6186 |
| Experts | 0 | 0 | 0 | 427 |
| Queued attention | 0 | 0 | 0 | 61416 |

The relaxed queued trace also records8,190 instruction-pool fallbacks. The original
AQL path preserves correctness. These counts do not describe exact timing-run
admissions and must not be converted into per-packet timing estimates. History
length is not unread kernel count.

Job50478: node2/one GPU,21 timing processes/17,472 correctness rows plus six trace
processes/624 rows. It adds32/64/128 disjoint output-head launch counts to the same
attention producer; stock freezes 26 prefix calibrations shared by all policies.
Strict source/binary, coverage, output, mapped-library and control audit passed.
At h256/t256 producer-graph early arrival, microseconds:

| Launches | Guarded256 | Threshold 24 | Threshold 32 | Relaxed |
|---|---:|---:|---:|---:|
| 16 | 633.237 | 634.640 | 634.139 | 651.777 |
| 32 | 1243.139 | 1244.040 | 1242.937 | 1242.518 |
| 64 | 2464.759 | 2436.279 | 2437.180 | 2437.078 |
| 128 | 4885.700 | 4786.235 | 4778.438 | 4775.674 |

The sign changes near32 in this fixture, consistent with the measured dispatch
interference/handoff tradeoff. Threshold24 has no >2% loss repeated across all
rounds in this matrix. Threshold 32 has a repeated ~4% long-shape shift also present
in alone and CPU-ready controls; it is retained and not attributed to waiting.
Threshold 64 is reserved as a subsequent model intervention. None of this proves a
universal dispatch threshold or a calibrated model-to-micro scaling factor.

Job50502:39 existing lifecycle/framework checks passed on exact bytes, including
1,920 PyTorch correctness rows. It covers event reuse, multithreaded queue reuse,
callbacks, upload round trips, cooperative work, queue churn, graph/event behavior,
and native-off/guarded/threshold24 controls. Pool pressure at threshold24 records
2,048 native waits, one rotation and 252 nonblocking fallbacks, with correct outputs.

Threshold 24 is therefore advanced to a **matched diagnostic C1 evaluation**, not
a release. Predictions were written before model submission in
`iterations/stream-wait-calibration-20260918/C1_PREDICTIONS.md` outside this repository.
The first model job compares guarded256/threshold24/relaxed on identical bytes,
three prefetch-on and three prefetch-off trials each, retained app/tapes/affinity,
with strict six-worker identity and mapped-library audits. It does not change graph
ordering, so it cannot recover that separate historical optimization by itself.
The historical14.897670ms/token best remains a separate target, not a current result.
