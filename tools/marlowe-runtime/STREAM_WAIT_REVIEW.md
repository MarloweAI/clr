# Fable architecture review and our response

2026-09-18. User-requested `claude-fable-5-1`, effort `xhigh`, one tool-free
review of design commit 8827d6a, source excerpts, measurements and our hypotheses.
The response completed successfully in 466 seconds. Model usage confirms Fable
produced the substantive review; the CLI also records a small Haiku auxiliary call.
Full unedited response and invocation metadata are saved outside Git under
`/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-design-fable-20260918/`.
This document records our assessment, not new performance measurements.

## Feedback that changes the plan

**Measure the variable the admission rule is trying to predict before inventing
another classifier.** Fable argues that remaining blocking time at GPU arrival,
producer dispatch pressure and the number of unhelpful prewaits are more meaningful
than a graph-role label. We agree. The original priority for a graph-role exception
was premature; use role to partition observations first, not as a workload whitelist.

**Separate duration from dispatch granularity.** The existing 4/25-kernel comparison
changes reductions, traffic and segment formation together. Fable proposes swapping
producer duration between those shapes. We adopt the intent, but not the claim that
two modified attention cells are a clean fixed-work experiment. Start with a small
producer where the same arithmetic and memory operations can be partitioned across
few/many launches; vary total work in a separate dimension. Record actual isolated
time, because fixed useful work does not also guarantee fixed elapsed time.

**The cost of an extra prewait may depend on concurrency.** A poll interval, packet
handoff, retirement, shared queue scheduling or signal-line traffic could change
cost with the number of waiting consumers. This is a hypothesis, not a proven
firmware mechanism. Retain two-/four-consumer controls. Do not model all waits as
one fixed microsecond charge or use a CPU count of enqueued waits as the number
currently spinning on the GPU.

**Feedback from repeated graphs is worth a feasibility study.** Existing segment
completion may help estimate edge costs. First measure observation lag and sampling
overhead. CPU retirement times are not GPU wait-entry times, batching can obscure
them, and changing admission changes next-replay timing. Hysteresis alone does not
make feedback neutral or correct. Keep this a candidate, not a no-regression promise.
Marker omission removes some observations; retain the endpoints needed by any
specific telemetry plan, rather than declaring all omission incompatible with it.

## Claims we checked and corrected

| Reviewer claim or suggestion | Our assessment |
|---|---|
| Historical 25/41-kernel segments guarantee zero v9 admissions | Unsupported. Those segments came from a different runtime; graph segment boundaries are not necessarily history-reset boundaries. Count actual per-generation admission reasons. |
| Long GPU blocking time explains every measured sign flip | Useful hypothesis, not established. The existing large-kernel fork/join test regressed 3.5–4.5% under native waits, despite long pending branches. Duration alone is insufficient; distinguish dispatch interference from release/consumer cost. |
| Sidewait is measured beneficial with guarded admission | The isolated 0.177 ms C1 sidewait benefit was measured with bypass enabled. The guarded combined micro configuration does not isolate sidewait. Do not promote it on that claim. |
| Replay feedback harms no short edge “by construction” | False as a performance guarantee: noisy/stale observations, extra tracking, scheduling changes and control feedback can regress workloads. |
| Sweep offload/engine bits and remove the IB hop | Field existence is not proof of legal equivalent packet semantics. Confirm architecture/firmware support first. A verified poll-interval ablation can be separate; no arbitrary packet-bit experiments. |
| Shared-queue negative controls can use the existing bypass | Source audit confirms bypass also skips same-queue/unknown-producer exclusion and queue lookup. Do not run it as a shared-queue control or copy it into production admission. Preserve physical eligibility separately from cost heuristics. |
| Already-complete producer measures the fixed native-prewait cost | The host signal check can skip the prewait entirely. Need a separate case pending at host submission but ready when the GPU reaches it, and verify a native packet was actually emitted. |
| Host-deferred submission is a safe fallback | At most a bounded diagnostic with all producers already submitted. It changes host scheduling and can deadlock or delay future producers/collectives if inserted into the wrong thread. Not a general runtime fallback. |

The reviewer also inferred equal wait counts and per-wait costs from the bundled
micro table. Those counts were assumptions, and splitting may change graph
partitioning. We do not adopt the resulting per-wait cost estimates.

## Revised next experiment

First distinguish **dispatch-driven producer interference**, **time spent blocked**,
and **consumer handoff cost**:

- Two producer work budgets × few/many launches, same useful operations for each
  work budget; independent correctness oracle. Measure actual baseline duration.
- Stock, guarded and a diagnostic that relaxes only cost admission while preserving
  supported signal/physical-queue eligibility. Keep ordering and marker policy fixed.
- Eager and graph forms. Start on verified distinct queues; test shared queues only
  with paths whose mandatory eligibility fallback is preserved.
- An early consumer, then a small control with preceding consumer work so its wait
  is pending at CPU submission but ready at GPU arrival. An already-ready-at-CPU
  control separately verifies fallback. Verify packet emission in a separate trace.

Do not begin with a broad firmware sweep or model grid. If gain follows dispatch
count more than duration, retain dispatch-pressure information and inspect lost
history. If it follows duration at fixed count, test whether repeated-graph cost
estimates are usable. If neither explains the sign, inspect concurrency and engine
path. The existing large-kernel regression is a required holdout, not an exception.

Then run our direct-versus-relayed completion test to examine metadata provenance.
This order combines Fable's better separating variable with our topology concern.
The reduced tests explain a possible mechanism; a bounded production metadata
capture is still needed to establish that the model encounters it.

## Round 2: bounded implementation decision

A second tool-free Fable `xhigh` review completed in 343 seconds. It recommends a
launch-count sweep in the existing attention producer, an untimed model admission
census, and a configurable count threshold before a role-based policy. We adopt
those changes. Splitting attention along output heads keeps each query's complete
reduction, FLOPs, input bytes and output buffer unchanged. Launch boundaries and
occupancy change, so elapsed time is measured, not held constant.

The first implementation is deliberately smaller than the reviewer's proposed
full topology × arrival × fanout grid:

- Existing attention producer: 256 heads, 256/1,024 tokens per partition; split
  each branch into 1/4/16/256 disjoint head launches, eager and full captured DAG.
  Serial, parallel and unsplit-wide controls. Preserve the original 64-head,
  8,192-token long-kernel case as a holdout with its independent CPU reference.
- Stock; released v9; new bytes off/guarded/threshold32/threshold8/cost-relaxed.
  Three rotated process rounds, eight retained timings per cell; trace separately.
  Default scheduling and marker behavior stay fixed.
- Native cost relaxation retains known distinct physical queues, queue lookup,
  compute-engine/signal eligibility and the original AQL dependency. Count threshold
  defaults to 256; supported diagnostic thresholds are 1..256. A generation-local
  trace records count, engine, producer/consumer queues and rejection reason.
- Next: controlled readiness and fanout using the existing waiter fixture, then
  grouped prefetch and the key queued/expert holdouts. A bounded untimed C1 census
  determines whether model waits fail cost checks or structural eligibility.

Further reviewer claims require correction: a 256-launch producer need not have
256 kernels still unread when the consumer is submitted; admission must be observed.
Shared-queue fallback need not equal stock timing because runtime changes outside
admission remain; require no native packet on that dependency and correct ordering,
then compare the same candidate with native disabled. Threshold 1024 is not known
harmful and exceeds the existing history capacity; it is not in this diagnostic.
Earlier same-byte admission micro studies held marker policy fixed, so the marker
confound applies to the latest bundled table, not to every prior admission result.
Likewise, the unchanged old shape is a holdout, not a requirement to manufacture a
particular regression in a new runtime. Timing runs cannot carry unbiased admission
counts by turning tracing on; diagnostic counts are separate observations.

For prediction, use runtime interventions, not just workload-size correlation.
Start with the admission family: record micro predictions for threshold and
cost-relaxation effects before matched C1 prefetch-on/off runs. Calibrate on two
interventions and reserve another threshold plus unseen shape as holdouts. Compare
fractional effects and uncertainty separately in each timing scope; do not assume a
unit scale or fit through a null effect. Reject a proxy for this intervention family
if a repeatable sign reverses, if it is neutral while C1 moves materially (>2%), or
if clearly separated predicted effects invert. A single successful sign match is
insufficient. Scheduling and marker-removal need their own calibration; a universal
single slope across those mechanisms is not justified. All long trials remain.


## New evidence and Codex xhigh review

Fable round3 export of the new results/patch was rejected by automatic approval
review despite the continuing review request. The user separately authorized
Codex xhigh review; a local reviewer assessed the evidence and the actual duplicate
suppression patch. No jobs or experiments were delegated.

Job 50308 passed 7,056 timing rows and reproduced the old large-attention regression.
Threshold 8 loses6.12% on a captured16-launch holdout; threshold 32 has no repeated
>2% loss in this42-cell screen. A separate trace shows duplicate native packets for
the same signal generation and physical consumer queue. The reviewer requires
identity across signal-object destruction, timing with tracking active in both
controls, cache updates after packet publication, physical/virtual queue traces,
and native-off plus churn bridges. These are incorporated in the diagnostic.

Job 50349 passed 10,752 timing rows. One early native wait with no initial fork still
increases handoff by about 31us. In a 16-launch producer case it also recovers about
15us of actual producer CTA span, yet total is worse. Thus a speedup of the producer
does not establish a speedup of the dependency chain. Already-ready-at-CPU is neutral.

An initial interpretation of the delayed control was too strong and was corrected:
about 3.5us extra *exposed after its prefix* is not a demonstrated ready-at-entry
packet cost. A native vendor packet with barrier bit clear may begin before the
prefix completes, and the producer's in-kernel stamp precedes signal completion.
AMD's [packet-header definition](https://rocm.docs.amd.com/projects/ROCR-Runtime/en/latest/api-reference/api.html)
(and pinned7.2.4 `hsa.h`) distinguishes ordered packet launch from kernel timestamps.
A supported ordering-bit ablation or a lifetime-stable already-zero native target,
with original AQL still using the real dependency, can separate these cases.

Historical screen02 already rejected a broad ACE-offload/interval sweep. Do not
repeat it as new evidence. A narrow non-offloaded1/4/16 comparison would test a
previously unmeasured field range; no claim about interval units or firmware cause
is justified by the field definition. Duplicate suppression cannot by itself remove
the demonstrated single-admission penalty. Its remaining benefit must be measured.


## Duplicate result and packet-control review

Job 50391 confirms a same-instance/generation duplicate on the same virtual and
physical consumer. The bounded cache suppresses it, yet threshold 8 plus dedup
still loses 5.63% on the 16-launch graph holdout. The source/off/guarded bridges
show no >2% loss repeated in all rounds of that screen; allocation-churn overhead
is not qualified. Detailed retained results are in
[the dedup report](benchmarks/dispatch_cost/DEDUP_RESULTS.md).

The Codex xhigh reviewer found no blocking bounds, lifetime or encoding issue in
the next bounded packet diagnostic. Its stable zero word is the eighth DWORD in
a retained 32-byte allocation, outside the seven executed instruction DWORDs.
64-byte allocation alignment preserves pool geometry. Original AQL dependencies
and retirement remain unchanged. The four interval4 combinations of real/zero
target and ordered/unordered header are necessary matched controls; unordered
real-target intervals1/16 add two previously untested settings. Every mode stores
the zero word and uses the same bytes, with the previous cost build bridged.

The zero target resides in instruction memory, not in a real completion signal;
it has different memory/coherence traffic. It moves any real pending wait back
to AQL and may restore producer interference, so its total-time difference is
not a pure packet-cost subtraction. Ordered launch applies to all preceding
physical-queue work, including other virtual streams; a favorable result would
not establish that global ordering is universally beneficial. No job execution
or monitoring was delegated to the reviewer.


## Packet result and third evidence review

Job 50424 passed 27,120 timing rows and 1,624 separate trace rows. Non-offloaded
intervals1/4/16 and ordered packets leave the principal early handoff penalty.
Stable-zero restores both ordinary handoff and ordinary producer interference.
The original waiter still removes 95.9% of added overhead with guarded admission.
The Codex xhigh review identified a real-attention positive control: at 256 graph
launches, early-minus-alone producer span falls279.28→6.16 µs, while at 16 launches
producer savings are smaller than added handoff. See [the complete interpretation
and retained results](benchmarks/dispatch_cost/PACKET_RESULTS.md).

The next step remains falsifiable admission and workload holdouts, not another
broad packet sweep. Model history must be distinguished from actually unread
kernel positions; bounded buffered census observations are preferred to printing
during replay. If beneficial C1 edges lack sufficient eligible work, a threshold
alone cannot recover them. Completion provenance then takes priority.

The reviewer refined the ordering concern after examining all call paths: every
current native-admitting route keeps a following original AQL packet with its
barrier bit set. For contiguous packets, moving the prefix drain before native
waiting adds no final dependency after that original. A different virtual stream
can still insert an any-order packet between their separate reservations on a
shared physical queue; ordering may remove its overlap. An earlier conditional
inter-kernel-spin deadlock example assumes progress HIP itself does not guarantee
and is not treated as an evidenced correctness blocker.

A possible later mechanism test uses a pending relay word in the same allocation
class as the stable-zero control, cleared by a common terminal producer operation
in every arm, while preserving the real AQL wait. This could separate storage/
completion traffic from pending state. It remains an idea; no relay experiment or
runtime implementation has been run or qualified.

## First model calibration and next comparison

Codex xhigh reviewed job50519's retained evidence. Threshold24 is the leading
candidate: every prefetch-on trial beats every guarded trial, off is effectively
unchanged, and earlier short-join micro losses under unrestricted relaxation are
avoided. The on-minus-off difference falls2.9290→1.7051 ms/token, consistent with
a prefetch-related effect but not proof that the remaining difference is wait cost.
The fixed resident order remains a confound; token intervals are not independent
replicas of the runtime intervention.

First reverse/rotate the runtime order in a fresh allocation. Run the reserved64
intervention on the unchanged grouped micros, then freeze its model prediction
relative to contemporary guarded and24 controls, including a numerical resolution
band. A model64 result that matches24 when the proxy predicts guarded-like behavior
would reject that explanation of model admission opportunities. No universal
micro-to-ms/token multiplier is fitted from the first two interventions.

Only afterward combine graph changes in a same-byte2×2: guarded/24 × default/
fixed ordering+side-policy bundle, with a default rebuild bridge. Measure the
interaction in ms/token; scheduling changes arrival, backlog and queue placement,
so separate implementation changes need not have additive benefits. That grid
attributes the bundle, not its individual ordering and side-policy components.
