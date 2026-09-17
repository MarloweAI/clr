# Select native waits only for substantial pending dispatch work

The original unconditional native prewait removes about2ms of overhead from the
2,048-kernel pending-wait reproduction, but can delay branch starts and joins.
Balanced64-stage attention chains regressed roughly77–89% with that version.
This revision keeps ordinary AQL waits at short dependency boundaries and uses
the native prewait only when substantial producer dispatch work remains.

Each retained signal generation carries numeric producer identity, physical queue
ID, and the producer's contiguous kernel-packet range as advisory metadata. A gap
in packet indices breaks the next kernel range, so other streams' packets and
interleaved markers cannot count as this stream's kernels. Idle/reacquired queues
clear the range. Metadata is recorded before the signal generation is published;
no producer object or queue pointer is stored in the signal.

At the consumer, the policy requires a cached hint of at least256 unread kernel
packets, excludes producer and consumer sharing one physical queue, and rechecks
current producer progress. The recheck searches the device's normal queue pools
under their existing lifetime lock using `tryLock`, with a64-entry scan limit.
The effective count is the smaller of the cached own-kernel count and the current
unread suffix ending at the recorded kernel index. A late wait therefore cannot
reuse an old large backlog estimate after its producer has drained.

If the queue is unavailable, the lock is contended, the queue is outside this
pool (for example a cooperative/CU-masked/cross-device producer), or the count is
below256, the original AQL dependency remains. There is no new host wait and no
application/model whitelist. The256 threshold is fixed in this candidate; the
experimental threshold override used during development is removed.

Admission only chooses whether to insert the existing native prewait. The original
full-width AQL condition, fences and notification always follow it. Native
instruction lifetime, bounded pool rotation and nonblocking fallback are unchanged.
Tracking is gated by feature enablement; ordinary off-path overhead is separately
compared with stock, not just with candidate-on.

## Measured handoff tradeoff

The selective policy retains the original prewait's handoff cost on eligible
long prefixes. In the first policy8 full suite, graph dispatch handoffs rose
from about17us to33–52us, while total latency fell about35–38% because producer
interference was removed. These component regressions are reported explicitly;
acceptance concerns useful producer time and end-to-end GPU/host performance,
not a claim that every internal timing component becomes smaller. Short/late
prefixes take ordinary AQL precisely because the same tradeoff can lose there.

## Scope and limits

This is a conservative policy, not a prediction of kernel duration. Long kernels
with short dispatch prefixes, markers between kernels, kernarg-pool retirement,
queue contention and profiled/intercepted queues can miss an opportunity to win.
ROCr profiler proxy read indices can describe frontend consumption rather than
hardware completion. In configured device-counter runs the observed result was
suppressed admission and stock-like timing; those runs are not used as evidence
of the unprofiled speedup. A finite benchmark matrix cannot guarantee that every
possible workload is neutral or faster.

The original RC4 standard GLM results do not qualify this revision. Complete the
[regression matrix](benchmarks/native_wait_policy/README.md), independent allocation
replication, PyTorch/semantic checks, and unchanged standard GLM qualification on
the exact packaged bytes before broad enablement. Keep this overlay opt-in and
preserve stock as a third control. Driver-gap investigation remains stopped at the
user's request; it is not a prerequisite invented for this microbenchmark policy.

The implementation remains in CLR/ROCm7.2.4, independent of SGLang and HiSparse.
Deployment uses the existing versioned overlay and launcher. A worker restart with
`GPU_NATIVE_EVENT_WAIT=0` disables the policy; restoring the stock image removes
the overlay. No driver or firmware deployment is required for this change.
