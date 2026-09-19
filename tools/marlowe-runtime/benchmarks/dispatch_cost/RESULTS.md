# Attention dispatch-count sweep — job 50308

2026-09-18, node2, one GPU. Exact audited HIP `e7f33a32329bb7d959cac1632078cd59787e9f8a4c02f1cfb2373450a183a4fd`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
Three rotated process rounds × seven modes × 42 cells × eight trials = 7,056 retained correctness/timing rows. Five separate trace processes add 210 correctness rows. Strict mapped-library, output, coverage and control audits passed. No trials were removed. All candidate modes use identical bytes; stock and released-v9 controls are separate libraries. Default graph order and marker policy are unchanged. This is a diagnostic, not a production candidate.

The producer partitions disjoint attention output heads across launches, preserving useful arithmetic and logical bytes at each shape. It changes occupancy and duration substantially. Both branches perform useful work, so this is a fork/join sweep; it does not yet test an idle consumer waiting early on a long dispatch sequence.

Parallel GPU microseconds below are medians of the three process medians. Percentage changes compare each mode with guarded on the same new bytes.

| Heads/tokens/launches/form | Stock µs | Guarded µs | Threshold32 Δ | Threshold8 Δ | Relaxed Δ | Relaxed round Δ range |
|---|---:|---:|---:|---:|---:|---:|
| 256 / 1024 / 1 / eager | 201.667 | 203.526 | +0.55% | -0.07% | +30.83% | +30.83–+30.93% |
| 256 / 1024 / 1 / graph | 210.806 | 212.487 | -0.05% | -0.11% | +26.74% | +25.02–+27.84% |
| 256 / 1024 / 16 / eager | 2418.479 | 2425.879 | -0.10% | +0.88% | +1.98% | +1.98–+2.17% |
| 256 / 1024 / 16 / graph | 2421.579 | 2422.838 | +0.82% | +0.99% | +2.66% | +1.70–+3.40% |
| 256 / 1024 / 256 / eager | 36331.660 | 36358.707 | +0.03% | -0.05% | +0.15% | -0.03–+0.43% |
| 256 / 1024 / 256 / graph | 36554.132 | 36619.780 | -0.10% | -0.25% | +0.07% | -0.09–+0.33% |
| 256 / 1024 / 4 / eager | 693.482 | 692.702 | -1.27% | -0.01% | +8.46% | +8.24–+10.60% |
| 256 / 1024 / 4 / graph | 703.483 | 701.163 | +0.54% | +0.12% | +9.79% | +9.04–+9.79% |
| 256 / 256 / 1 / eager | 69.441 | 68.922 | +0.87% | +0.52% | +83.05% | +80.99–+83.98% |
| 256 / 256 / 1 / graph | 76.642 | 76.642 | -0.52% | -0.03% | +84.65% | +84.37–+85.33% |
| 256 / 256 / 16 / eager | 648.378 | 646.638 | +0.20% | +0.67% | +6.31% | +6.21–+6.71% |
| 256 / 256 / 16 / graph | 633.217 | 633.618 | -0.08% | +6.12% | +10.99% | +10.97–+10.99% |
| 256 / 256 / 256 / eager | 9841.072 | 9829.116 | +0.02% | -0.09% | +0.06% | -0.15–+0.23% |
| 256 / 256 / 256 / graph | 9504.481 | 9531.928 | -0.08% | -0.08% | +0.31% | +0.24–+0.52% |
| 256 / 256 / 4 / eager | 182.424 | 183.324 | -0.08% | -0.17% | +35.82% | +35.75–+35.96% |
| 256 / 256 / 4 / graph | 193.764 | 194.205 | +0.03% | -0.25% | +32.81% | +32.81–+33.00% |
| 64 / 8192 / 1 / eager | 1546.951 | 1543.931 | -0.03% | +0.15% | +3.95% | +3.38–+4.58% |
| 64 / 8192 / 1 / graph | 1551.271 | 1549.430 | -0.00% | +0.32% | +3.89% | +3.61–+4.14% |

## Findings and limits

- The original 64-head / 8,192-token eager shape reproduces the regression: guarded 1,543.931 µs → relaxed 1,604.992 µs (+3.95%). Branch spans stay near 1,478/1,515 µs; the handoff grows from 9.730 to 40.150 µs and overlap falls. This supports boundary overhead, not slower attention arithmetic. It does not identify the firmware mechanism.
- Threshold8 fails a holdout: 256 heads / 256 tokens / 16 launches / captured parallel grows 633.618 → 672.399 µs (+6.12%). Its side branch finishes before the main branch in every timed trial. Handoff grows 6.710 → 41.920 µs. In the separate trace, two native packets on consumer queue1 use the **same signal and generation**, at packet indices453 and457. Trace affects timing; do not turn the two trace admissions into an exact per-packet timing estimate.
- The relaxed short one-launch case loses most overlap (34.795 → 0.545 µs) and total grows 68.922 → 126.163 µs. Separate traces admit both the initial fork and the final dependency. An aggregate per-wait cost cannot distinguish those two sites.
- Launch count alone does not make this balanced fork/join positive. Large-count cases approach neutrality in percentage terms because their useful work takes much longer. This does not falsify dispatch interference for an early waiting consumer, which this fixture has not supplied.
- Threshold 32 remains close to guarded on this matrix. That is a safe-screen observation, not evidence it recovers HiSparse performance. Threshold 8 is rejected as a global default from this result.
- Queue-cap1 trace reports81 same-physical-queue exclusions and no native packets. Trace counts over the whole process: guarded 4, threshold 32=10, threshold 8=20, relaxed 80 emitted packets (includes untimed setup). Per-cell records remain available in raw logs.

Next separate early-wait producer interference from the already-ready handoff, then test bounded duplicate-prewait suppression on a new runtime while retaining every original AQL dependency. Keep signal generations correct under reuse. Add threshold16 as a held-out diagnostic, then run grouped prefetch, queued/expert and original-waiter screens before narrow C1 confirmation.
