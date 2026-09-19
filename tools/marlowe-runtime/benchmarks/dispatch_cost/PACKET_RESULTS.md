# Packet controls and attention arrival — job 50424

2026-09-18, node2, one GPU. Strict audit passed 113 processes: 27,120 retained timing
rows and 1,624 separate trace rows. Three rotated process rounds. HIP
`500e91ca76c0b4b6e80a0f7439b9624cf850a286a1763f53697781b9eab14d90`, HSA
`b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
Mapped libraries, exact workload coverage, every output, compiled controls,
source/binary hashes, references and frozen arrival calibrations passed.
All measured trials remain; trace timings are excluded. Diagnostic only.

The same-byte matrix compares real/zero native target × ordered/unordered header
at interval4, plus unordered real intervals1/16. Stock, native-off, guarded and
previous-cost-build relaxed controls are included. Every packet mode retains the
original real AQL dependency, executes seven instruction DWORDs and allocates
32 bytes with the same 64-byte alignment. The extra word is initialized in every
mode. No graph schedule, marker policy or useful workload was changed.

## Pending handoff remains

GPU microseconds; median of three process medians. Attention is h256/t256/K1 eager,
with no initial fork and an early cross-queue consumer.

| Configuration | Total | Producer CTA span | Handoff |
|---|---:|---:|---:|
| New bytes, native off | 49.90 | 33.48 | 9.62 |
| Guarded | 49.52 | 33.47 | 9.52 |
| Relaxed, interval 4 | 81.06 | 33.23 | 40.69 |
| Relaxed, interval 1 | 80.86 | 33.50 | 40.20 |
| Relaxed, interval 16 | 81.30 | 33.36 | 40.91 |
| Relaxed, ordered | 80.92 | 33.82 | 40.19 |
| Relaxed, stable-zero | 49.96 | 33.38 | 9.62 |

The intervals and ordering bit do not remove the approximately 31 µs early handoff
penalty. Balanced fork/join regressions also remain. In the original long-kernel
eager holdout, guarded total1539.83 µs versus relaxed 1596.97 µs and ordered 1591.93 µs;
zero1541.51µs. In the short K16 captured fork/join, guarded636.94µs versus
relaxed 702.26 µs, ordered 705.64 µs and zero 639.88 µs. No real-target packet setting
qualifies as a global fix.

Delayed arrival exposes approximately 3.5 µs extra after the prefix for real and
zero targets, ordered and unordered. Ordering does not change this measurement.
This does not prove whether the hardware ignores the vendor header or whether its
ordering effect is unexposed here. The in-kernel timestamp is not the signal's
zero transition. The zero target changes memory/coherence traffic and moves the
real pending wait back to AQL, so it is not a pure packet-cost subtraction.

## Producer protection still works

The original 2,048-increment waiter retains the historical benefit:

| Configuration | Alone µs | Pending waiter µs | Added waiter cost µs |
|---|---:|---:|---:|
| Stock | 3152.44 | 5238.26 | 2085.82 |
| Guarded | 3147.52 | 3232.88 | 85.36 |
| Relaxed | 3147.02 | 3234.60 | 87.58 |
| Ordered | 3146.94 | 3234.70 | 87.76 |
| Stable-zero | 3149.82 | 5227.19 | 2077.37 |

Guarded removes 95.9% of the added waiter overhead in this run. The zero target
restores the interference, as expected when the real pending dependency is left
to AQL. Removing the optional packet's blocking behavior removes its benefit too.

There is now a positive **real-attention** control. For h256/t256/K256 with the
producer captured as a graph, compute early-minus-alone within each mode/process
before taking the median across rounds:

| Configuration | Additional producer span µs | Additional total µs |
|---|---:|---:|
| Native off | 279.28 | 284.99 |
| Guarded | 6.16 | 43.20 |
| Stable-zero | 273.06 | 278.11 |

At K16, corresponding producer-span excess is guarded 15.595 µs, relaxed 0.25 µs,
zero 15.52 µs. Thus this fixture exposes about 1 µs of interference per dispatch,
while native waiting adds roughly 30 µs to early handoff. This explains opposite
signs at 16 and 256 in this fixture; it does not identify a universal break-even
count or validate a HiSparse predictor yet.

Some modes have producer-duration shifts even in alone/CPU-ready controls: e.g.
K16 graph alone is about594µs in stock/previous-cost/ordered-zero but537µs in most
new modes. No native dependency is emitted in alone, so those shifts are not
attributed to waiting. All rows and absolute timings remain. Within-process
contrasts above help isolate the measured interference; they do not replace raw
performance results. No multi-second-gap investigation was undertaken.

## Decision

Do not promote interval changes, ordering or duplicate suppression as the fix.
Test guarded/threshold24/32/relaxed on unchanged grouped4/25-kernel prefetch,
experts and queued/fanout holdouts. Densify the attention launch-count sweep with
32/64/128, retaining isolated, early, delayed and CPU-ready controls. Record
admissions separately: neutrality with no native packet is not a successful
cost prediction.

A bounded untimed C1 census is still needed. Recorded history count is not unread
count; compare recorded actual-kernel positions with the producer read index.
Separate missing provenance, intentional history breaks, short/drained segments,
engine and queue exclusions. Buffer observations and emit after the diagnostic
window to limit synchronous trace perturbation. No new HiSparse result or
production qualification is implied by these micro results.
