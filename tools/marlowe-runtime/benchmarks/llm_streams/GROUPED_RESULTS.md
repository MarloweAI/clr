# C1 prefetch investigation: grouped microbenchmarks

Current status: the 25-kernel variant reproduces the lost native-wait benefit
with prefetch and shows an ordering/admission interaction. Direct C1 testing
attributes 0.893 ms/token to admission; the remaining model gap is not yet
fully explained. All bypass packages remain diagnostic-only.

Status: the full-model discrepancy is confirmed and remains unresolved. These
microbenchmarks do not reproduce it. The isolated scheduling candidate is a
diagnostic build, not a production-qualified runtime.

## What the model controls establish

C1 with the retained application, same final-v9 runtime bytes, node 2, three
trials per cell. Values are medians of complete trial means; lower is better.
Every measured interval is retained.

| Native waits | Prefetch off, ms/token | Prefetch on, ms/token |
|---|---:|---:|
| Disabled | 17.196513 | 17.377537 |
| Enabled | 14.998473 | 17.336355 |

Native-wait enablement recovers 2.198040 ms without prefetch but only 0.041183 ms
with prefetch. The approximately 2 ms discrepancy is a missing benefit in the
prefetch path, not a demonstrated 2 ms regression caused by enabling native waits.
The historical c82 prefetch-on median was 14.909373 ms/token, but that runtime
also contains graph scheduling, marker, and wait-policy changes.

A separate contemporaneous C1 prefetch-on comparison isolates the historical
long-path segment ordering on top of final v9:

| Runtime | Three trial means, ms/token | Median |
|---|---|---:|
| Final v9 | 17.374663, 17.368962, 17.382749 | 17.374663 |
| V9 plus segment ordering | 16.976768, 16.952964, 16.960422 | 16.960422 |

The ordering change recovers 0.414241 ms/token (2.38%), not the complete gap.
Mapped HIP/HSA identities and timing arithmetic were independently checked.
These comparisons do not identify every contributing dependency or justify
adding deltas from historical cohorts.

## Grouped probe and negative reproduction result

The new `grouped_prefetch` case models four-layer anchor/follower groups:
GPU-produced shared indices, a synchronous anchor gather, three follower gathers
on a side stream, per-layer completion events, attention consuming those KV
records, and separate D2H backups. Records are 1,152 bytes. Shapes have 8/32/64
layers and 32 attention heads. Deterministic planning models dependency ordering,
not the cost of real top-k/LRU planning. There are four compute kernels per layer;
this differs from the model's larger kernel mix and dispatch density.

Depth 1 synchronizes after each replay. Depth 8 queues eight replays before
completion and reports per-replay time. Query feedback persists across replays;
CPU references include every replay, with final host backups checked against the
last replay. Allocation, reset, capture and reference computation are not timed.

| Captured graph, prefetch on | Stock | V9 disabled | V9 enabled | Historical c82 |
|---|---:|---:|---:|---:|
| 32 layers, depth 1 | 8929.6 | 8927.2 | 8926.2 | 9530.3 |
| 32 layers, depth 8 | 8941.9 | 8946.7 | 8946.7 | 9501.4 |
| 64 layers, depth 1 | 17875.6 | 17884.3 | 17893.2 | 19101.9 |
| 64 layers, depth 8 | 17888.5 | 17889.5 | 17894.8 | 19028.8 |

Units: microseconds per replay, medians of three fresh-process medians. These
are not token latencies. Full eager/graph and prefetch-off rows remain in the
artifacts. V9 tracks stock and disabled controls; c82 is slower in these shapes.
Queued replay does not reproduce the model difference either. Do not call this
a model performance qualification or claim that grouped dependencies alone
explain the production result.

Both depths passed: 24 fresh processes, 3,456 retained timing rows, independent
output checks and per-process mapped-library verification. Largest v9-on median
increase over stock across either matrix was 0.127%; over v9-off, 0.096%.

## Isolated segment-ordering microbenchmark screen

The candidate stable-sorts independent segments at each dependency level by
node count, retaining stable ties. It changes neither native-wait admission nor
marker behavior. The grouped/expert screen passed correctness across 30 fresh
processes and 11,520 timing rows. Grouped-prefetch timings stayed near v9.

One skewed batch-64 four-expert graph has a candidate median 3.0% above v9:
base round medians 154.765/155.025/152.745 us, candidate
152.946/163.325/159.405 us. The signs differ across rounds; this is retained as
an unresolved performance concern, not declared neutral. Node count is not a
measurement of critical-path duration or a guarantee of stable main-chain queue
assignment.

Separate diagnostic traces for the grouped case recorded 160 native prewait
packets and 190 admission checks in both v9 and the ordering candidate. These
traces are excluded from headline timings. They do not establish the model's
admission behavior.

## Provenance and next discrimination

Local artifact root:
`/home/sashawork/dev/amd-runtime-production/iterations/c1-prefetch-recovery-20260917`.
Remote root is the same suffix under `/workspace/home/sasha`.

- `grouped-depth1-j49308`, `grouped-depth8-j49308`: raw CSVs, identity receipts,
  manifests and analyses. Job 49308 completed on one GPU on node 2.
- `longpath-micros-j49321`, `longpath-trace-j49321`: isolated ordering screen and
  separate diagnostics. Job 49321 completed after 49308, on one GPU on node 2.
- `matched-runtime-grid-audit.json`, `longpath-model-audit.json`: independently
  checked model controls from jobs 49247 and 49608.
- `longpath-only.patch`, `fable-longpath-review.json`: candidate and performance
  review. This patch is outside the main PR runtime implementation.

Final v9 HIP SHA256:
`43104e17679d8700f1d3f5a66160b63ba3cbd26fba2f46cab5802a58d4bb2115`.
Ordering-candidate HIP:
`2494e0eb04e43b96b07f52b8a58a836a78717501596feb7960632bcb0abdbf74`.
Common HSA:
`b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
Candidate source is `cab5670` plus patch SHA256
`a864fbe2023edac3ed3fb2f47d254cfa1b4a8df9cc19dc905d74564314f25e5d`.

Next requested model control is the same c82 binary with native waits off/on
crossed with unused-marker mode 0/2, holding ordering/spare/side-queue policy
fixed. This separates older native-wait behavior from the marker optimization.
Results are pending; no recovery claim follows from the planned experiment.

## Same-binary c82 native-wait / marker control

Job 49656 completed 0:0 on node2. C1 prefetch on, TP4, same c82 library and
application in every cell. Three trials per cell, marker modes rotated within
native cohorts; native-on cohort ran before native-off. Medians of complete
trial means, no timing samples removed:

| Native waits | Unused markers retained (mode0) | Unused markers omitted (mode2) |
|---|---:|---:|
| Off | 16.977739 ms/token | 16.790055 ms/token |
| On | 15.098550 ms/token | 14.897670 ms/token |

Native waits save 1.879189 ms with markers retained and 1.892385 ms with unused
markers omitted. Marker omission saves 0.187683 ms native-off and 0.200880 ms
native-on. Thus native waits provide the larger contribution in c82; removing
unused markers alone cannot explain the c82-to-v9 prefetch difference.

All four rank receipts/cell and six distinct mapped-library identities/cohort
passed independent checks against c82 HIP SHA
`ad99498d98335d4a8b1f3bb2201fae09f7d39f333f43c7c347403bb50cab4fd2`
and HSA SHA
`b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
One native-off/mode0 trial was 39.612696 ms/token (maximum interval 4360.519758
ms); it remains in the three-trial median and raw data. No gap investigation
was performed. Sequential native cohorts leave a possible time-order effect;
this is not a randomized native-mode crossover.

These results isolate native enablement within c82, not the exact cause of v9's
loss of benefit. The v9 256-kernel history/admission guard remains a candidate
mechanism requiring a controlled test. Current grouped microbenchmarks still
fail to reproduce the model effect. Original measured grids used 32 blocks on a device reporting 256 CUs.
The 256-head extension is measured below; the 512-head option remains untested.

## Direct admission bypass microbenchmarks (49717)

Completed 0:0. Exact v9 cab5670 plus an optional admission-only diagnostic
bypass, HIP `d11003c9e6c81c6720fb475e973bf94db41dc55313909b7c505470d5542a2daa`.
Graph scheduling, original AQL dependencies and native encoding remain unchanged.
Guard-on/off grouped comparisons use identical diagnostic bytes.

All 15 wide-attention processes (2160 timing rows) and 36 queued/fanout processes
(5904 timing rows) passed correctness checks. Performance screen **failed**.

256-head captured-graph prefetch-on results, median of three process medians:

| Layers | Guard on, us | Guard bypassed, us | Change |
|---|---:|---:|---:|
| 8 | 1741.36 | 1850.94 | +6.29% |
| 32 | 8914.35 | 9529.69 | +6.90% |
| 64 | 17879.42 | 19068.88 | +6.65% |

Known queued-attention cases, 16 queued steps, ms per step. Here the control is
the exact released v9 library, and bypass uses the new diagnostic library:

| Balanced attention | Released v9 | Diagnostic bypass | Change |
|---|---:|---:|---:|
| 2 streams | 3.150 | 5.929 | +88.21% |
| 4 streams | 3.694 | 6.423 | +73.89% |

A separate trace-only pass verified compiled bypass0/1, identical mapped HIP
bytes, and 48 correctness rows per setting. It counted 160 native packets with
the guard and 6435 without it across the full 32-head diagnostic process. These
are perturbed diagnostic counts, not unbiased timing evidence or model counts.

The guard prevents real regressions. These microbenchmarks still do not reproduce
the model benefit from unrestricted native waits. The next C1 comparison must
establish whether the same guard also suppresses useful waits in the model.
This package is diagnostic-only and must not be deployed as a performance fix.

## C1 admission isolation (49757)

Job completed 0:0. Same retained C1 prefetch-on app and input fingerprints,
three trials/cohort; all 192 measured token intervals/trial retained. Exact
mapped HIP/HSA, native1/trace0, diagnostic bypass0/1 and four rank receipts
passed independent checks. Medians of complete trial means:

| Runtime | ms/token |
|---|---:|
| Released v9 | 17.400892 |
| Diagnostic v9, guard on | 17.370454 |
| Same diagnostic bytes, guard bypassed | 16.477809 |

The admission guard causes **0.892645 ms/token (5.14%)** of overhead for this
C1 prefetch workload. The diagnostic rebuild with guard on remains within
0.030439 ms of released v9. This is direct causal evidence for the whole
admission gate, not proof that the 256-kernel threshold alone is responsible.
Bypass removes the history, producer-queue and read-index admission checks;
it preserves the original AQL dependency and native-wait encoding.

This does **not** explain the full gap: bypass remains 1.580138 ms/token above
the c82 median14.897670 from49656. These runtime medians come from different
jobs. Ordering/marker effects cannot simply be added to the admission effect:
ordering's earlier0.414241ms benefit was measured with the guard on, and may
interact with which physical queue receives native waits. This motivated testing whether graph ordering changes the native-wait benefit;
the completed combined comparison is reported below. Unrestricted admission still fails the microbenchmarks and
is not a production fix.

Released-v9 trials were46.755106,17.361975,17.400892; guarded diagnostic trials
17.368503,17.389450,17.370454; bypass trials16.481228,16.460724,16.477809. The
slow released-v9 trial remains included; no gap investigation was performed.

## A microbenchmark reproduction and ordering interaction (49816)

The 25-kernel-per-layer variant now reproduces the qualitative C1 pattern:
native waits help without prefetch, that benefit almost disappears with
prefetch, and unrestricted admission plus ordering recovers it. This keeps
the same KV inputs and mathematical attention result as the four-kernel
variant, but adds real partial-summary traffic, reductions and launches. It
is a causal submission-granularity control, not a full model replica.

One GPU on node2, job 49816 completed 0:0. All 75 processes and 18000 timing
rows passed correctness checks; four separate trace passes verified compiled
ordering/bypass controls and mapped hashes. All four diagnostic combinations
use HIP `2aaca46adbab45c0e4d1e99a9ae359440f18fff2777a40cf40148402c85f86c8`.
HSA is unchanged. Runtime modes rotate within three process rounds; ordering
matrices run sequentially, so these are not randomized ordering crossovers.

For 64 layers, 32 heads, 25 compute kernels/layer, captured graph, ms/replay:

| Prefetch | Native off | Guard on, original ordering |
|---|---:|---:|
| Off | 22.977 | 21.929 |
| On | 23.592 | 23.587 |

Native enablement saves 1.048 ms without prefetch but only 0.005 ms with it.
For prefetch on, the same-library factorial is:

| Ordering | Guard on | Admission bypassed |
|---|---:|---:|
| Original | 23.587 | 22.929 |
| Longer segments first | 23.421 | 21.827 |

Ordering saves 0.166 ms with the guard and 1.102 ms without it: an additional
0.936 ms interaction, positive in all three paired rounds (0.903, 0.819,
0.960 ms). The 32-layer case also shows a positive interaction in each round
(0.440, 0.411, 0.294 ms). The combined 32-layer case is 10.916 ms versus c82
10.940 ms measured in that ordering matrix. This motivated the model factorial reported below; these microbenchmarks alone
do not establish the model's interaction.

This is still **not a general performance fix**. With four kernels/layer,
ordering enabled and prefetch on, bypass regresses the 32/64-layer graphs by
6.78%/6.83%. It also regresses four-stream balanced expert graphs by 27.03%
(batch16) and 44.96% (batch64), versus the same ordering-enabled library with
the guard. The useful admission policy remains unresolved.

Artifacts: `interaction-{s1,s22}-l{0,1}-j49816`,
`interaction-experts-j49816`, `interaction-controls-j49816`, and
`interaction-micro-audit.json` under the C1 prefetch investigation directory.
The exact runtime source patch and compiled-control audit are included in
`marlowe-hip-7.2.4-v9-interaction-diagnostic1`, explicitly unqualified.


## Model confirmation of the interaction (49875)

C1 with prefetch on, TP4 on node2, retained application `e4b3fe5`, inherited
CPU affinity, native wait enabled and trace disabled. All four cells use the
same diagnostic HIP bytes (`2aaca46a...`, full hash above) and unchanged HSA.
The order was L0B0, L0B1, L1B0, L1B1, with three retained trials per cell and
one allocation. This is a sequential factorial, not a randomized crossover.

| Ordering | Admission | Trials, ms/token | Median, ms/token |
|---|---|---|---:|
| Original | Guard retained | 17.398362, 17.389527, 17.420673 | 17.398362 |
| Original | Bypassed | 16.520939, 16.528382, 22.281806 | 16.528382 |
| Longer segments first | Guard retained | 16.997674, 17.003614, 17.002967 | 17.002967 |
| Longer segments first | Bypassed | 24.770733, 15.334502, 15.320906 | 15.334502 |

Ordering alone saves 0.395395 ms/token; admission bypass alone saves 0.869980.
Together they save **2.063860 ms/token (11.86%)**. Ordering saves 1.193881 ms
with admission bypassed, yielding a **0.798485 ms interaction** beyond the
standalone effects. This corroborates the grouped-prefetch microbenchmark:
the two runtime policies interact materially in the real C1 workload.

The 15.334502 ms combined median remains 0.436832 ms above the historical
c82 native-on/marker2 median of 14.897670. That residual is a cross-job
comparison and does not isolate remaining marker, queue-policy, or graph
implementation differences. Nor does this experiment isolate each component
of the admission gate or prove the precise per-wait mechanism. The main
performance discrepancy is substantially explained, but the residual and a
policy that preserves the regression controls remain unresolved. The
combined diagnostic is **not production-qualified**.

Job 49875 completed 0:0. Independent audit recomputed all 192 measured
intervals in each of 12 trials and verified application/input fingerprints,
rank receipts, six distinct startup identities per cohort, exact equality to
six post-timing worker-map PIDs, and mapped HIP/HSA hashes. Slow trials above
are retained; no multi-second-gap investigation was performed. The benchmark
agent independently confirmed the same complete audit and medians; its final
report is `c1-investigation/v9-interaction-20260918/RESULTS.md` in the combined
optimizations workspace.

Audit provenance: job 49839 stopped because its capture parser read only the
first identity record on each line. Two complete JSON records can share a
line. Its affected cohort lacks post-timing maps and remains provisional.
Before 49875 finalization, the post-timing parser was corrected to read all
marker-delimited records; strict identity and map checks were retained.
Before/after hashes are `ca87545e2900e9753fa2a815673e3f1a391968521fe453f388050dd70e95411b`
and `1bd4cf5b92c2ae887cdb4d15c373c78dc47e08a1503f410edb87e8aa7dc5076f`.
The startup manifest may record the earlier parser hash; this post-timing
change is documented separately, without rewriting manifests or changing
application/runtime bytes. In 49875 L1B0, six identity records occupy five
lines; all six match the captured worker maps. A redundant rerun, 49933,
was canceled at startup after this was verified.

Artifacts: `model-interaction-j49875-{l0b0,l0b1,l1b0,l1b1}`,
`model-interaction-j49875-audit.json`, `audit_interaction_model.py`, and
`model-interaction-parser-fix` under the C1 prefetch investigation directory.


## Isolated side-stream prewait selection (49954)

A new diagnostic adds a default-false `GPU_GRAPH_DIAGNOSTIC_SIDEWAIT` control
on top of the ordering/admission diagnostic. It suppresses optional native
prewaits on interior graph markers whose consumer is the launch stream.
Side-stream consumers and the final graph join retain prewaits. Original AQL
dependencies and completion markers remain. A separate marker allowance
preserves producer-history tracking. Classification uses logical streams,
not a measurement of distinct physical queues.

Job 49954 completed 0:0 on one GPU on node2. All 45 processes and 13,680
uninstrumented timing rows passed correctness, control and mapped-library
audits. Two separate trace passes each validated 48 correctness rows and
both consumer classes. Native packet counts over the full traced workload
were 6,160 with all prewaits and 5,487 with side selection; these are not
per-model or timing measurements. New HIP SHA-256:
`7485acfbe16290290b564ce175d4fd2d8db3b6d9f516633de66ff8e09e927486`.
HSA is unchanged. Each matrix rotates five modes over three process rounds:
stock, guarded new build, old combined diagnostic, new build with all waits,
and identical new bytes with side selection. Ordering remains enabled.

Captured expert graphs, median of three process medians, microseconds:

| Case | All prewaits, bypass | Side selection, bypass | Guard retained |
|---|---:|---:|---:|
| Balanced b16, four streams | 191.446 | 160.605 | 151.125 |
| Balanced b64, four streams | 139.105 | 105.663 | 95.383 |
| Skewed b64, four streams | 188.106 | 173.806 | 161.645 |

Side selection improves each of these cases in all three rounds, isolating
substantial cost from optional main-stream interior prewaits. Balanced b64
saves 33.00/33.08/33.68 us per round. However, the side-selected cases still
regress 6.27%/10.78%/7.52% against guarded admission respectively.

For 25-kernel grouped-prefetch graphs, side selection improves the 32/64-layer
medians by 0.79%/0.76% relative to all prewaits, but per-round savings have
mixed signs: 83.32/-37.38/208.25 us and -88.72/171.99/414.28 us. This is not
robust evidence of an additional C1 model gain. New-build versus old combined
baseline differences for those cases are -0.02%/-0.14%; the eight-layer case
has a larger -1.36% rebuild difference. Four-kernel grouped-prefetch graphs
still regress 6.62%/6.31% against guarded admission at 32/64 layers.

This policy reduces some regressions but does not eliminate them. It also
cannot repair non-graph queued-wait regressions by construction. A narrow C1
comparison was requested with old combined bytes, new bytes/selection off,
and identical new bytes/selection on to separate rebuild and policy effects.
No model result for this selection is claimed yet; the package remains
explicitly unqualified for production.

Artifacts: `side-policy-{s1,s22,experts,controls}-j49954`,
`side-policy-j49954-audit.json`, `audit_side_policy_micro.py`, and
`side-policy-diagnostic.patch` under the C1 prefetch investigation directory.
