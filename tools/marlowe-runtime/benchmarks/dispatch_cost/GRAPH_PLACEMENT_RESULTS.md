# Independent placement/order factorial with corrected completion

Node2, one GPU at a time; root owns standalone submission, waiting and audits.
All samples retained. No application or workload source/math changed, no timing-gap
investigation. Runtime diagnostics remain outside shipping source/package controls.

## Correctness gate and source correction

Initial placement job 51007 stopped before timing. Placement-only failed 4/48 wide
completion observations, identically trace 0/1, while all other controls passed.
The original endpoint reconstruction chose greatest dependency level, which cannot
identify the latest submission among independent equal-level segments. Old bytes
failed again with native waiting off, guarded256 and threshold24 in 51020.

Generic actual-enqueue tail tracking preserves per-segment ownership and original
AQL dependencies. Corrected bytes passed 768 completion observations across caps 1/4/8,
plus 720 last-submission receipt checks. Job 51046 passed 75 framework/lifecycle
processes, 3,200 PyTorch rows and 480 clone/update/replay/child parameter observations.
Child execution is internally single-stream; this is not nested cross-stream proof.
The generic source fix and fixtures are pushed in PR1 commit b36e37b. Release lock
and production package remain unchanged. See [completion coverage](../graph_completion/README.md).

All subsequent factorial/confirmation timings use HIP d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4,
base cab5670 plus patch 38a91fb038a72604057955a7ab7b140d808c5b8543d6d5aa31a88a88648e6dfc.
Package marlowe-hip-7.2.4-graph-tail-diagnostic1 remains unqualified. Its immutable
qualification metadata predates the external framework report; those checks do
not make it a production release.

## First factorial 51026

84 timing processes/17,920 correctness rows, 15 separate traces/1,600 rows and 336
fresh completion observations passed strict audits. Four balanced orders cover
each assignment/order state in each position and each predecessor pair once.
Stock, old-byte default admission 24 and same-byte legacy LONGPATH rotate separately.

The four states independently change length-based assignment and enqueue priority.
Vectors are prepared at scheduling, with stable baseline ties. Traces verify:

- enqueue-only preserves baseline logical/physical placement;
- placement-only preserves baseline submission order;
- BOTH and legacy have identical assignment, submission and queue-equivalence maps.

Microseconds, medians of four process medians:

| Workload | Stock | New admission 24 | Enqueue only | Placement only | BOTH | Legacy coupled |
|---|---:|---:|---:|---:|---:|---:|
| Matrix + KV parallel graph | 215.017 | 218.057 | 216.628 | 213.437 | 220.528 | 217.507 |
| Grouped25,32 layers,prefetch on | 11562.580 | 11406.584 | 11385.893 | 10817.985 | 10877.967 | 10877.347 |
| Grouped25,64 layers,prefetch on | 23128.875 | 22706.188 | 22718.800 | 21647.635 | 21896.872 | 21649.687 |
| Four experts,b16 balanced,graph | 234.448 | 150.705 | 151.155 | 150.745 | 150.915 | 150.675 |

Placement-only saves 5.16%/4.66% at 32/64 prefetch-on, winning all four rounds and
retaining 111%/131% of the same-run BOTH saving (frozen gate ≥75%). Enqueue-only
remains near neutral. The actual-enqueue correction/new-build default bridge is
−0.071%/−0.282% in those grouped cells. This supports placement as sufficient for
the gain in this fixture, without reordering submission.

No row loses >2% in all rounds, but skewed 64 four-expert graph has a noisy +3.07%
placement median (+1.301, +4.915, +8.391, −6.879%). BOTH versus legacy differs 1.14%
on 64 prefetch-on despite equal mappings, exceeding its frozen <1% bridge band.
These required an independent allocation; neither was filtered away.

## Independent confirmation 51063

60 timing processes/12,800 rows and 12 separate traces/1,280 rows passed. Same bytes
and sources, four balanced orders of admission 24/placement/BOTH/legacy, stock
separately rotated. Existing exact-byte completion gates were reused.

| Workload | Stock | Admission24 | Placement only | BOTH | Legacy coupled |
|---|---:|---:|---:|---:|---:|
| Matrix + KV parallel graph | 216.707 | 216.877 | 215.697 | 222.068 | 214.767 |
| Grouped25,32 layers,prefetch on | 11603.881 | 11447.499 | 10939.622 | 10940.473 | 10880.909 |
| Grouped25,64 layers,prefetch on | 23201.523 | 22817.139 | 21912.225 | 21781.036 | 21780.794 |
| Four experts,b16 balanced,graph | 233.468 | 155.365 | 152.396 | 154.545 | 152.785 |
| Four experts,b64 skewed,graph | 193.327 | 162.506 | 163.905 | 156.865 | 158.515 |

Placement-only confirms 4.44%/3.97% prefetch-on gains, faster in all four rounds.
Prefetch-off changes −0.81%/−0.42%. Mixed changes −0.54%; skewed 64 expert changes +0.86%
with rounds −5.545, +1.971, −1.560, +2.398%. No placement row has >2% aggregate loss, and
none loses >2% in every round versus admission 24 or stock. Earlier expert loss did
not repeat at its original magnitude; retain both allocations and their variability.

The original grouped BOTH/legacy bridge is now 0.55%/0.001% at 32/64 prefetch-on,
within its frozen band. Structural equivalence still does not mean timing equality:
BOTH's mixed result is +2.39% versus admission 24 and 3.40% versus legacy. BOTH performs
two extra cache lookups per graph level; an execution-time cause for this difference
has not been established. Do not assert performance equivalence or universal
neutrality from equal mappings. Placement-only is the candidate advancing; neither
this unused BOTH behavior nor the earlier 50851 loss is erased from the evidence.

Aggregate grouped native emissions in 51026 were 4472 baseline, 4473 enqueue-only,
4099 placement-only, 4097 BOTH, 4099 legacy. These are traced/setup aggregates, not
per-wait costs and not a causal packet explanation of saving.

## Next gate

Test corrected placement24 on unchanged fixed-work attention, original waiter,
queued chains/fanout with shared-queue caps, grouped4, small KV attention-fetch and
H2D/D2H pipeline holdouts. Require the existing ~96% waiter-excess reduction and
neutral/positive key rows; independently confirm material noisy losses. Only then
freeze a matched C1 prefetch-on/off prediction and run the existing retained TP4
launcher. HiSparse results are unchanged by these microbenchmark experiments.

A production implementation must be restricted to qualified single-device graph
placement and remove diagnostic machinery; the known preexisting multi-device
assignment limitation must not be exposed by a new default policy. No workload-name
whitelist, timing-based training or marker omission was added.

Raw roots: graph-tail-j51026, graph-tail-confirm-j51063, graph-tail-gate-j51020,
graph-tail-checks-j51046 under stream-wait-calibration-20260918. Every manifest,
control/source/library audit, timing row, trace and failed-gate artifact is retained.
