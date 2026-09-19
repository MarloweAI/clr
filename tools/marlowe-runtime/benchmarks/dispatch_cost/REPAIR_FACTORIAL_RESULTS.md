# Launch-entry and tail-repair attribution — job 52829

The launch-entry repair accounts for the substantial balanced-two-stream loss in this ordinary-marker diagnostic. The actual-tail repair has much smaller, mixed effects. This isolates source interventions; it does not establish whether barrier waiting, packet arrival, fences or host allocation is the underlying cost in the current fused implementation.

Job 52829 completed on node2/one GPU. Six Williams rounds, eight retained trials per process, six variants and 52 expert cells produced 14,976 timing rows. All mapped libraries, source inputs and controls passed audit. An independent reduction reproduced every median and contrast. Diagnostic HIP `8f3ef0a17e4f2c03fdf4d0f4d8561e2b134f7c608ec0ccf0be3b6fed1215095a` has only separately switchable launch-entry (E) and actual-tail (T) repairs on vanilla source. Native wait and placement are off. No kernel, workload or profiling changes.

Primary: balanced b64, two streams, total graph replay. Lower is better; values are microseconds.

| Configuration | GPU | Host | Submit |
| --- | ---: | ---: | ---: |
| Immutable vanilla | 111.053500 | 120.310000 | 9.860000 |
| Same bytes E0/T0 | 111.723497 | 120.822750 | 10.187500 |
| Same bytes E1/T0 | 115.523750 | 125.155000 | 10.615000 |
| Same bytes E0/T1 | 111.193249 | 120.645000 | 9.930000 |
| Same bytes E1/T1 | 116.334001 | 125.642500 | 10.457500 |
| Immutable repaired | 115.593752 | 125.125000 | 10.270000 |

| Intervention | GPU change | Host change |
| --- | ---: | ---: |
| Entry on at T0 | +3.800253 | +4.332250 |
| Entry on at T1 | +5.140751 | +4.997500 |
| Tail on at E0 | −0.530248 | −0.177750 |
| Tail on at E1 | +0.810250 | +0.487500 |

Both entry effects exceed 2% for GPU and host in all six rounds. Neither tail contrast has an aggregate absolute GPU/host effect above 2% anywhere in the 52 cells. GPU interaction, calculated from aggregate medians, is +1.340499 us; every paired round interaction is positive (median paired interaction +0.830001 us). Host interaction is +0.665250 us with mixed round signs. Effects are not additive fixed shares. Overlapping submission and GPU durations cannot be subtracted to infer pure GPU stalls.

Both predeclared primary endpoint bridges pass absolute ±2% GPU/host, aggregate and every round: E0/T0 versus vanilla is +0.6033% GPU/+0.4262% host; E1/T1 versus repaired is +0.6404%/+0.4136%. Preserve a secondary bridge exception: b16/two-stream graph E0/T0 versus vanilla host −2.2091%, with mixed rounds. Submission bridges are not uniformly neutral (E0/T0: six losses/three gains above 2%; E1/T1: eleven/two).

Correctness retains 1,008 rows from 36 processes across queue caps 1/4/8. The 24 expected asynchronous entry failures occur only with entry repair absent; all synchronized entry positives and all 864 terminal rows pass. The terminal fixture is regression coverage here: its historical negative required changed placement, absent from this isolation. Failed predecessor job52812 required that unsupported negative and stopped before observations or timings. All its artifacts remain preserved. V2 corrected the requirement before timing, without changing runtime bytes or workloads.

Each of four untimed proofs has 26 graph generations, 208 launches and 352 segment executions. The primary has 13 kernels (6 + 6 + merge) on two distinct physical queues, identical merge dependencies and the same singleton final side tail. Four-stream final-list order changes in non-E0/T0 variants and is part of the intervention. Source receipts demonstrate submission intent, not GPU waiting durations or profiler transparency. Stock already contains a final join.

Next action: focus on launch-entry critical-path cost while retaining its correctness. Tail removal is unsupported. Allocator cost remains an unmeasured hypothesis; this experiment does not justify removing entry ordering or claiming the remaining cost is unavoidable. Hassan's separately extracted workload is tested with stock/current only; the historical diagnostic controls in this experiment are not Hassan runtime retests.

Raw: `iterations/stream-wait-calibration-20260918/repair-factorial-v2-j52829`.
Spec SHA256 `1004f9cdddaeb638f382e4be5eb57632efafd41fb9f50efeed903a66feea201d`.
Manifest SHA256 `da4cb173ea048f04e81bd48550018e2902f902aac0ec495a121dca279fdf6cfc`.
No new runtime is qualified or promoted by these results.
