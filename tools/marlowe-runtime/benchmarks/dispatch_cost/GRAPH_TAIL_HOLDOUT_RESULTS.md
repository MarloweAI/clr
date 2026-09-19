# Placement candidate: broad holdouts and independent attention confirmation

The exact corrected candidate preserves the original waiter improvement and is
ready for a bounded C1 comparison. This does not establish universal neutrality
or production qualification. No runtime or benchmark math changed during these
holdouts, no timings were trimmed, and no gap investigation was performed.

All jobs used node2, one GPU at a time, with root-owned standalone submission,
waiting and validation. HIP d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3;
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
Same-byte controls: guarded256, strict admission24, placement+admission24; stock
is a separate runtime. Four balanced orders, separate untimed traces. Placement
preserves baseline enqueue order and SIDEWAIT0. The actual-enqueue-tail fix is
included. Existing completion/lifecycle/PyTorch gates are reused on exact bytes.

## Completed coverage

Job 51137 passed 96 broad timing processes / 29,376 correctness rows and 18 trace
processes / 2,736 rows. Attention/waiter then passed 32 timing processes / 7,296
rows and 6 traces / 486 rows. All controls, exact mapped libraries, workload source
hashes, row coverage and references passed local and remote audits.

Job 51165 independently repeated the entire unchanged attention/waiter suite in
a fresh allocation: another 32 timing processes / 7,296 rows and 6 traces / 486
rows, strict audits passed. The repeat was required by noisy losses, not selected
from favorable timing trials. Both allocations remain part of the evidence.

## Performance

Worst median change among all cells in each family, placement24 versus comparator;
positive is slower. Each cell is the median of four process medians. This table
reports maxima, not means, confidence bounds or promises about untested workloads.

| Family | Cells | vs stock | vs guarded256 | vs admission24 |
|---|---:|---:|---:|---:|
| Small KV attention-fetch | 120 | +1.01% | +0.52% | +1.14% |
| H2D/D2H pipeline | 36 | +1.55% | +0.79% | +0.70% |
| Grouped4 prefetch | 12 | +0.19% | +0.17% | +0.03% |
| Queued chains | 8 | +0.65% | +0.53% | +0.60% |
| Fanout, queue cap4 | 6 | +0.07% | +0.66% | +0.69% |
| Fanout, queue cap8 | 6 | +0.07% | +0.002% | 0.00% |
| Fixed-work attention, initial 51137 | 42 | +4.24% | +2.03% | +1.67% |
| Fixed-work attention, independent 51165 | 42 | +1.54% | +1.19% | +0.30% |

Initial attention had seven >2% median losses versus stock and one versus guarded.
None exceeded 2% in every paired round, and none recurred above 2% in the independent
allocation. The independent allocation has no >2% aggregate loss against any of
the three comparators. The first allocation is retained; its noise is not evidence
of a specific runtime cause, and the second is not proof that all future runs are
neutral. No placement-vs-admission24 cell exceeded 2% in either allocation.

The candidate retains real stream overlap. On the 256-head / 1024-token / one-launch
graph attention case in 51165, serial is 355.152 us and parallel 211.627 us (about 1.68x
faster); stock is 354.642 us and 210.017 us respectively. Splitting helps this workload,
while the candidate itself is nearly neutral on that attention case.

Waiter excess is pending_wait minus alone; excess removal is measured against
contemporary stock, not the total kernel duration:

| Allocation | Stock excess | Guarded256 excess | Admission24 excess | Placement24 excess | Placement excess removed |
|---|---:|---:|---:|---:|---:|
| 51137 | 2090.714us | 82.242us | 84.941us | 86.311us | 95.872% |
| 51165 | 2087.188us | 86.774us | 85.949us | 89.420us | 95.716% |

Both pass the frozen >=95% band around the original approximately 96% result.
The prior grouped25 improvement remains approximately 4–5% in two allocations
(51026/51063); these broad holdouts test possible costs elsewhere.

## Trace scope and corrected harness failure

The broad traces show no changed assignment position in these holdout shapes.
They therefore test admission behavior and the overhead/fallback of enabling the
placement policy. They do not add active-placement topologies to the earlier
factorial, mixed-workload and completion evidence. Active-placement evidence comes
from 51026/51063, particularly grouped25; do not generalize it to arbitrary graphs.

Grouped4 captures graphs but emits no segmented-placement records. This is
consistent with the stock classic fallback for at least 16 segments averaging
fewer than 8 nodes, which happens before placement is computed. Small-KV/fanout/
pipeline traces do exercise segmented scheduling but do not change assignment.

The first attempt 51114 completed all 96 timing processes and then failed a harness
assertion incorrectly demanding segmented-placement records for grouped4. No
attention/waiter processes ran. Original scripts and failed artifacts are retained.
A new version corrected only that expectation, preserved all identity/correctness
checks, and ran a clean complete suite in 51137. No timing was discarded as an
outlier and no runtime/application change was used to obtain the passing audit.

## Next decision

C1 job 51180 uses the existing retained TP4 launcher, same e4b3 application/tapes/
measurement protocol, and six separately restarted residents in forward/reverse
order: guarded, admission24, placement24, placement24, admission24, guarded. Each
resident runs three prefetch-on and three prefetch-off requests. All 36 trial means
are retained, with six-worker identities/maps and actual controls audited.

Frozen prediction: placement24 improves prefetch-on by at least 2% versus admission24
in each block, while prefetch-off stays within +1% of both contemporary controls.
This is a held-out scheduling intervention prediction; the micro's exact percentage
is not assumed to transfer. No model result is available at report creation.
Production qualification, natural-output validation and a simplified implementation
restricted to qualified single-device graphs remain subsequent work.

Raw roots under stream-wait-calibration-20260918:
graph-tail-holdouts-j51114 (failed harness, preserved),
graph-tail-holdouts-v2-j51137, graph-tail-attention-j51137,
graph-tail-attention-j51165. Each successful root has a manifest and strict audit;
contrasts.json retains all cell medians and paired round changes.
