# Select native waits using actual unread kernel positions

The original unconditional native prewait removes about 2 ms of overhead from a
2,048-kernel pending-wait reproduction, but can delay short branch starts and
joins. Balanced 64-stage attention chains regressed roughly 77–89% with that
version. Keep ordinary AQL waits at short dependency boundaries and insert the
native prewait only while at least 256 actual producer kernels remain unread.

Each logical stream keeps a fixed ring containing queue indices of its latest 256
kernel packets. Intervening markers, dependencies and other streams' packets do
not count as kernels. They also do not erase earlier own kernels within an independent dispatch segment. A still-pending dependency on another physical queue, an engine switch, or an explicit stream-memory/IPC wait ends that segment. This prevents queued short fork/join stages from borrowing a long history that will have drained by the time their GPU wait executes. The batch path
checks the actual kernel-dispatch packet type. Recording is gated by native-wait
enablement, and changing the physical queue id clears the history.

Each retained signal generation carries the producer's numeric physical queue id
and the oldest index in that 256-kernel history. No producer or queue pointer is
stored in the signal. At the consumer, the policy excludes a shared physical
queue and rechecks current producer progress. Admission requires the current read
index to be at or before the recorded oldest index, proving all 256 recorded own
kernels are still unread. This does not count a packet span or reuse a stale
estimated backlog after the producer drains.

The producer queue lookup searches normal pools under their existing lifetime
lock with tryLock and a 64-entry bound. An unavailable queue, lock contention,
unsupported pool such as cooperative/CU-masked/cross-device, incomplete history,
or drained history falls back to the original AQL dependency. There is no new
host wait, model whitelist or threshold override.

Admission only chooses whether to insert the existing native prewait. The
original full-width AQL condition, fences and notification always follow it.
Native instruction lifetime, bounded pool rotation and nonblocking fallback are
unchanged. Signals retain generation ownership under the existing CLR lifecycle.

## Why the contiguous suffix was insufficient

The preceding v8 policy required 256 consecutive unread kernel packets. Retained
C1 prefetch-off decode fell from~15 ms to~17 ms because its important producer wait
reported only 7 consecutive kernels, while roughly 2,300 packets still preceded
producer completion. A matched diagnostic restored~15 ms by changing only native
admission. The position history recovers this opportunity while retaining the
256-kernel threshold, and its diagnostic build passed the existing attention
regression controls and retained about 96% of the original waiter benefit.

Final release qualification must identify exact packaged library hashes. A
source change or diagnostic result alone does not qualify another build.

## Scope and limits

A short prefix of very long kernels can still miss an opportunity. Forwarding an
event through another stream does not propagate the original producer's history;
that separate case can still lose the benefit. Queue churn, contention and
profiled/intercepted queues can also suppress admission. ROCr profiler proxy read
indices can describe frontend consumption rather than hardware completion, so
counter runs are not evidence of unprofiled admission or speedup.

The policy conservatively resets at compute/SDMA transitions, which can miss long-history opportunities across in-order copies. It also retains the native prewait's handoff cost on eligible long histories.
A component gap can increase even while producer and total latency improve; all
component and end-to-end measurements remain visible. A finite benchmark matrix
cannot establish universal neutrality or production readiness.

Run the [queued-work holdouts](benchmarks/queued_streams/README.md), the unchanged [regression matrix](benchmarks/native_wait_policy/README.md),
independent allocation replication, PyTorch/semantic checks and standard model
qualification on the exact packaged bytes before broad enablement. HiSparse C1
decode recovery does not substitute for standard GLM or the other serving cases.
The user-paused driver-gap investigation is not a prerequisite for this change.

Implementation remains in CLR/ROCm7.2.4, independent of SGLang and HiSparse. The
versioned overlay stays opt-in with stock as a third control. Restart workers
with GPU_NATIVE_EVENT_WAIT=0 to disable it; restore the stock image to remove the
overlay. No driver or firmware deployment is required.
