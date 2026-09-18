# Graph-entry CPU retirement — job51745

Result: sharing the entry marker CPU retirement with the following segment batch is insufficient to resolve the RC2 regressions. On the five preselected affected cells the same-byte eager comparison ranges from0.51% faster to0.08% slower. No target reaches the preselected2% improvement screen. This extra runtime complexity is not selected for production.

Fresh diagnostic HIP `ae81d03eba0cc1612b6a6cde17b9e898e62351f3ccf9657bbbe5b9a8b5466e32`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Root standalone script on one node2 GPU, Slurm0:0. All192 correctness processes and180 timing processes passed source/control/map/row audits; local mirror re-audits. Six balanced orders cover all positions and all30 directed adjacent pairs once. All timings and trials retained.

The four diagnostic profiles share identical bytes: eager/lazy side-marker submission crossed with separate/shared CPU retirement. Stock and immutable RC2 are additional controls. The new path preserves the full-system dependency barrier, GPU completion signal and predecessor lifetime; only timestamp/handler/CPU batch retirement is shared. Profiling/event agents/non-DD/CPU-wait fallback retain ordinary markers. Partial failures retire all unvisited eager entry batches.

## Evidence

| Target graph cell | Same-byte eager us | Eager+batch us | Batch/eager | Lazy us | Lazy+batch us | Batch effect on lazy |
|---|---:|---:|---:|---:|---:|---:|
| attention_fetch, h32-miss256-r1152, gather-parallel, total, graph | 710.783 | 707.983 | -0.394% | 709.933 | 709.394 | -0.076% |
| experts, b16-balanced, 4_streams, total, graph | 161.966 | 161.486 | -0.296% | 160.806 | 160.576 | -0.143% |
| experts, b64-balanced, 2_streams, total, graph | 115.544 | 115.494 | -0.043% | 116.073 | 115.774 | -0.258% |
| experts, b64-balanced, 4_streams, total, graph | 105.404 | 105.484 | +0.076% | 103.674 | 103.343 | -0.319% |
| experts, b64-skewed, 4_streams, total, graph | 165.025 | 164.185 | -0.509% | 166.246 | 165.746 | -0.301% |

Waiter excess removal remains95.69–96.01% across enabled profiles. Eager+batch still loses2.28% versus contemporaneous stock on h32/miss256 gather graph and4.01% on b64-balanced/two-stream experts. The latter loses in all six rounds. Eager+batch has one >2% aggregate same-byte loss, an eager/wide fixed-attention cell with mixed round signs; it is retained. Lazy+batch has no >2% aggregate loss versus same-byte lazy. The fresh eager/batch-off control has no >2% aggregate loss versus immutable RC2.

Correctness adds pinned8KB/8MB external H2D, copy-first graph roots, a foreign producer forwarded through a launch-stream event wait, and consecutive launches without host synchronization. Every native/placement state, eager/lazy state and batch state ran at queue caps1/4/8. Separate untimed cap4 transfer traces confirm the actual entry path; performance trace is0 throughout. These checks qualify this experiment, not a production package.

Together with51714, these results show that submission scheduling and separate CPU retirement are not sufficient explanations or fixes for the repeated losses. They do not prove the exact residual cause. The next source review concerns the required system acquire at graph entry versus when consumer-side writes need a system release. No fence scope may be removed based solely on benchmark improvement; arbitrary external producers and engine/CPU transitions must stay ordered.

Raw root `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-batch-j51745`, mirrored under `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-batch-j51745`. Complete per-round GPU/host/submit measurements and all contrasts are in `contrasts.json`. The original full microbridge failure remains documented, and the final new-byte C1/C4 bridge remains held.
