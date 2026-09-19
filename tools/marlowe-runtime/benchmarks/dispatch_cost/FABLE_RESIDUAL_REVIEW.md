# Fresh Fable review: localize the two-stream critical path before another optimization

A user-requested Claude Fable5.1 xhigh review completed on2026-09-18 in269.691s,
with tools disabled. The substantive model was claude-fable-5-1; a small Haiku
auxiliary call is separately recorded. It received the current measurements,
repair-source description, rejected experiments, allocator proposal and Hassan's
reproducer context. Full request, response and usage remain under
`iterations/stream-wait-fable-refresh-20260918/`. The previous successful review
was around03:10 UTC, roughly14hours earlier; this review includes new evidence.

## Decision changed by review

Hold the unbuilt allocator experiment. The repair-only comparison combines two
changes: ordering side roots after application launch-stream predecessors, and
joining the actual last submitted command on each stream. First split those
factors and distinguish side-root start delay, kernel stretch under overlap and
post-merge completion time. Preserve unprofiled stock comparisons, complete raw
samples and correctness-negative controls. No correctness repair is dropped from
a shipping candidate merely because the uncorrected comparator is faster.

The first-principles hypothesis is an exposed entry dependency on a balanced
critical path. A side-root start delay can propagate almost fully to the merge
when branch lengths are balanced. Conversely, greater actual overlap can slow
individual bandwidth/compute-bound kernels. Either can explain GPU/host elapsed
cost larger than the submission-time difference. Neither has been established
for the current target. Native prewait is not required for the repair-only loss.

For a two-branch fork/join, compare the observed spans of the launch branch and
side branch, their start skew, dependency handoff and final completion. Subtracting
whole-run totals cannot distinguish these terms. A three-segment graph is not a
three-kernel graph: the target contains13 kernels, six in each root and one merge.
All relevant dispatches, stream/physical-queue identities and phase boundaries
must be matched before interpreting traces.

## Corrections and limits of the review

- Stock already emits a final side-tail join. The review's suggestion that the
  repair introduces that join is incorrect. The repair changes which actual tail
  command is selected and when the bookkeeping runs. Verify selected owners and
  ordered final dependencies; do not invent an extra marker from elapsed time.
- Five small allocations costing tenths of a microsecond was the reviewer's
  estimate, not a measurement. Holding the arena is a prioritization decision,
  not experimental rejection of all CPU bookkeeping or allocator effects.
- Host-total versus GPU-total time does not alone rule out host starvation. The
  proposed dependency-latency explanation is not a demonstrated firmware wake cost.
  Same-queue ordering is not universally free; packet launch and kernel completion
  are distinct. Avoid assigning a fixed per-edge cost without observations.
- Current first-batch entry integration explicitly declines queue profiling and
  dispatch/copy/barrier activity profiling. Therefore a naive profiler run can
  disable the path whose timing regresses. Establish the observed execution path
  and scope traces accordingly; never substitute profiled latency for normal timing.
- Removing a covered final tail requires actual command dependency coverage,
  including per-stream order, later overwrites, reference lifetime and failure
  prefixes. DAG reachability alone does not establish command-level coverage.
- A CPU observation of completion does not by itself supply the GPU acquire/cache
  visibility a removed barrier would provide. Pure-marker bypass can also violate
  timestamp or callback observability. These elisions remain unimplemented proposals.
- The review's proposed relaxed acceptance of halving the gap does not replace
  the user's neutral-or-positive stock requirement.

## Hassan requirement

Pinned input repository: `MarloweAI/native-runtime-four-arm-reproducer`, commit
b8a96bb4d842f628142e417ebb6753d4492bcaff. Its packaged primary endpoint is TP8 L10
serving cadence, not an isolated attention-kernel timer. Q/K dispatch contracts
and ordinary-event scheduling source are included. A standalone microbenchmark
has not been located in that tree; the user was asked for its path. Do not call a
new synthetic extraction Hassan's unchanged benchmark or run the full serving
campaign in place of the requested microbenchmark.

The user explicitly requests stock/current-candidate comparisons and no older
runtime reruns for this workload. The review's suggestion to repeat old runtimes
is rejected. Archived v7 numbers provide context only. The event-versus-serial
serving difference can include changed routed work; neither the whole loss nor
the native-on/off slice is established as a pure runtime cost. Assertions that
such kernels must lose with events on every runtime are unsupported.

When the supplied benchmark is available, retain its kernels, dimensions, data,
dispatch choices, event edges and measurement scope. Add exact runtime/control
identity checks and separate untimed mechanism observations without tuning its
workload. A current-runtime regression there remains a required unresolved gate,
even if the existing expert and grouped families pass.

## Follow-up after repair isolation and Hassan results

A fresh Fable xhigh review completed in356.661s after52829, followed by a386.414s correction round after the new Hassan data. Both returned successfully. Raw prompts/responses live in `iterations/stream-wait-fable-factorial-20260918`.

The first response incorrectly explained the expert loss by overlap between successive replays. Source `llm_streams/common.hpp::time_once` synchronizes the device before every measured sample, launches one graph and synchronizes its end event. That premise is incompatible with the experiment. The correction round explicitly withdrew it. We also reject its suggestion to accept the loss as a correctness price; the user's goal remains neutral/positive while correct.

The surviving hypotheses are a pending-frontier handoff delay, producer notification/publication delay, and kernel stretch under changed arrival/overlap. They are hypotheses, not observed GPU stalls. Similar host/GPU deltas or small total submission changes cannot exclude host-induced packet-arrival effects. The existing52028 result rejects the extra first-kernel release as a useful optimization; it did not test every possible acquire/fence effect.

Hassan's captured graph is now structurally observed in52935: four kernel nodes, main segment containing two small PyTorch integer-fill kernels followed by Q, side segment containing K; distinct physical queues, flat-kernel eligibility. There is no measured physical-overlap result yet. The failed52906 observation exported no DOT because the original graph was not retained;52935 explicitly retains it and calls HIP's graph export API, with no performance claim from either observation.

Next, measure device execution intervals in diagnostic copies of the same kernels and qualify instrumentation against the unchanged performance gate. Track per-block spans, start skew, overlap, initialization work and the residual boundary/completion interval. Preserve the original benchmark/data/runtime identities and check register/LDS/resource changes before treating instrumentation as transparent. External profilers are also interventions: qualifying path and packet behavior is required before using their results to explain the unprofiled fast path. Profiling a different path can supply structural evidence, not a confirmed cause for production latency.
