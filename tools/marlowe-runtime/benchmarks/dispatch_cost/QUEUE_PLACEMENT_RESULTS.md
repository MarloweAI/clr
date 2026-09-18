# Spare allocation and placement interact

Job52635 tests the existing placement switch against spare allocation on identical
job52606 diagnostic bytes, native admission disabled throughout. Placement with
the spare retained improves long grouped-prefetch GPU time by1.315%/1.071%, with
zero >2% GPU or host regressions across76 cells in that comparison. It retains
the four-stream expert benefit from extra physical parallelism. This supports
considering allocation and placement jointly, but does not solve the two-stream
expert stock loss or qualify a production package.

## Full four-cell comparison

S is optional spare allocation and P is cached stable node-count placement.
GPU microseconds, lower is better; median of four process medians:

| Graph cell | S0P0 | S1P0 | S0P1 | S1P1 |
|---|---:|---:|---:|---:|
|Grouped s22 L32, prefetch on|11563.051|11801.599|11593.872|11646.444|
|Grouped s22 L64, prefetch on|23046.314|23632.184|23290.640|23379.095|
|Experts b16 balanced, 4 streams|241.188|159.775|238.638|159.175|
|Experts b64 balanced, 4 streams|120.774|99.693|121.904|99.994|
|Experts b64 skewed, 4 streams|199.566|162.755|197.656|164.465|
|Experts b64 balanced, 2 streams|115.364|114.694|115.403|115.024|

With S1, placement reduces L32 GPU/host by1.314692%/1.314330%, or
155.155/155.235us, and L64 by1.070950%/1.070285%, or253.089/253.033us.
Every round improves. L8 prefetch-on also improves2.567125% GPU/2.535277% host.
The L64 submission metric **regresses5.591891%** (+16.43275us), all four rounds
positive. L32 submission is -0.219801%. Across76cells, placement/S1 has eight
submission improvements and seven losses above2%; zero GPU/host losses above2%.

With S0, placement is slightly slower on long grouped GPU (+0.266554% L32,
+1.060155% L64). There are no absolute GPU/host changes above2% anywhere in this
comparison, but nine submission improvements and six losses above2% remain.
Thus allocation and placement are not independent effects.

Define interaction as (S1P1-S1P0)-(S0P1-S0P0). Grouped L32 GPU interaction is
-185.976505us, rounds -246.907235/-181.606293/-179.585457/-194.686889us;
L64 -497.415542us, rounds -478.255271/-382.510185/-497.256279/-559.318542us.
Host interactions agree (-184.832500/-497.290000us). These signed interactions
are calculated in the frozen runner, not inferred from separate cohorts.

With P1, the grouped spare penalty shrinks to0.453444% at L32 and0.379785% at
L64, versus2.063022%/2.542141% with P0. At the same time S1P1/S0P1 retains
four-stream expert GPU gains of33.298449%,17.973568%,16.792411%. Two-stream
experts remain close across all four controls; this mechanism does not recover
the separately established two-stream stock deficit.

Retained side effect: S1P1/S0P1 has one >2% GPU/host loss cell, skewed four-stream
**eager**: GPU+2.154393%, host+2.034407%. GPU rounds are -2.558082,+2.068156,
+3.330027,+1.638442%. Eager execution does not use the graph policies, so these
mixed-round values cannot be assigned to their direct execution path. They are
not excluded. This contrast has11 submission improvements and5 losses above2%.
There is no stock or immutable-release arm in this interaction job; prior52606
is kept separate, never pooled, and cannot serve as a contemporaneous stock claim.

## Queue evidence and protocol

Eight untimed proofs show that changing placement does not change the used
physical-queue counts: grouped-on still uses2 with S0 or3 with S1, and four-stream
experts use3 or4 respectively. Placement changes segment assignment, not the
number of available queues. These receipts establish selected dispatch queues,
not GPU stall durations, SDMA identity or cache-transfer cost.

Root directly launched and monitored node2, one GPU; Slurm0:0. The standalone
monitor's final remote validation and local saved-artifact audit pass. Same
HIP75b840... and HSA b8cd..., existing benchmark/reference bytes; no rebuild,
application changes, full-model run, gap investigation or sample exclusions.
AMD_DIRECT_DISPATCH1, native0, queue cap4, dynamic queues0, streamops0; all timing
traces/logging/DOT output off. Four Williams orders cover unchanged grouped_s1,
grouped_s22 and experts:48 timing processes,9,728 rows,76 cells.

Job52606's144 correctness processes/3,744 rows are explicitly retained, with
its manifest/audit/spec and exact library hashes bound and revalidated. Those
checks already cover all native/placement/spare combinations and queue caps1/4/8;
repeating them without a binary or semantics change is unnecessary. Eight new
untimed proofs contribute1,024 arithmetic rows, never timings. All four grouped
proofs pass exact six-DAG and selected-pair coverage. All four expert proofs run
the independent complete26-generation/44-segment/352-receipt verifier before
timing. Every timing/proof process verifies actual mapped library identities.

## Artifacts and next decision

Local root: /home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918;
remote uses the same suffix under /workspace/home/sasha/amd-runtime-production/iterations.
Raw:queue-placement-j52635; runner:run_queue_placement.py;
observer:queue_placement_observer.py; retained-check binding:queue_placement_retained.py;
submit:submit_queue_placement.sh; spec:queue-placement-spec.json.
Full signed cell, submission, per-round and interaction values remain in contrasts.json.

- HIP:75b840f48b0414fbb6724a1283aa7d94574955130f82a029e33d7e630d0f9e0f.
- HSA:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Frozen spec:5537286fd07bdcd7593844bf0fc3acd8e555dc2e5c905a99efae646a89041bee.
- Manifest:60072ca780ae6d0c7379d82889b5b68a94b7297ed35a1d9a88c3612766b7693f.

Global spare removal remains rejected. A conservative next candidate is a
qualified spare policy: keep it for flat single-device captured-kernel graphs
(where independent compute queues help), and for mixed graphs only when the
existing qualified placement policy is enabled; otherwise retain required-count
stock allocation. This is a proposed eligibility boundary, not a proven fix or
permission to waive any stock screen. It needs source review and full-family
comparison before promotion, and leaves the two-stream expert issue open.
