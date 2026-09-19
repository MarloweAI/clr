# Hassan Q/K architecture checkpoint after job 54925

The goal remains a substantial speedup from true parallel execution of the original Q/K workload, followed by regression checks on the other microbenchmarks. It is not achieved. Changing kernels or shapes, serializing logical streams, or weakening dependencies would not meet that goal. There is no newly qualified runtime and no full-model work is planned.

The best fully joined direct replay is about 9.64 µs/pair. Historical serial execution is about 8.75–8.87 µs/pair under its recorded HIP protocol; its timing boundary differs from direct replay. The latest mechanisms fail even against their contemporary direct-replay controls.

## Closed mechanisms

| Mechanism | Evidence | Decision |
|---|---|---|
| Concurrent siblings on one physical queue | Jobs 54716/54739: no overlap, including minimal-work and fence/order controls; identical code overlaps on two queues | Do not port |
| Extra GPU polling kernel | Job 54609: entry and internal joins regress; even a zero-budget helper costs too much | Reject |
| Split-graph GPU polling | Job 54181: helps matched split-event execution, but remains slower than unified graphs | Not a Q/K solution |
| Joint internal packet publication | Job 54404: cheaper CPU submission, neutral GPU time | Close |
| Native PM4 at short internal joins | Job 54847: 9.626 → 43.010 µs/pair | Reject |
| CPU readiness with retained ANDs | Job 54901: 26.25% slower than its CPU-observer control | Reject |
| CPU readiness omitting satisfied ANDs | Job 54925: 19.10% better than keeping them, but 6.76% slower than full prepublication | Close CPU-readiness architecture |

Do not run further CPU-readiness tuning or `ROC_CPU_WAIT_FOR_SIGNAL` model jobs. All retained results remain immutable. The independent long-producer polling result—90–93% of added waiter penalty removed—remains valid, but does not justify treating frequent short joins in the same way.

## What the direct path removes

In mode 0, both entire AQL lanes and their doorbells are published before the CPU entry gate opens. After release, the host skips all per-layer work and only actively observes the two final completion values. Four hundred unique IPC signals carry kernel completions, with no host retirement callback per kernel in this replay.

Normal internal joins therefore do not require ongoing HIP submission, Python launches, host graph retirement, per-join HSA host callbacks, or a Linux syscall handling each dependency. Queue creation, mappings, scheduling and power policy still come through ROCr/KFD/driver configuration and can affect device behavior. This does **not** establish that the driver cannot matter.

The frozen [replay source](ready_omit_probe/replay.cpp) creates IPC signals, publishes both complete mode-0 lanes, releases the gate, and bypasses the per-layer host loop. In the official ROCm 7.2.4 source at commit `97f5574fe2fdc7bef44fb01545347912ee9f1779`, [IPC selects DefaultSignal](https://github.com/ROCm/rocm-systems/blob/97f5574fe2fdc7bef44fb01545347912ee9f1779/projects/rocr-runtime/runtime/hsa-runtime/core/runtime/hsa_ext_amd.cpp#L543-L563). That signal [uses memory and atomic loads without an interrupt mailbox](https://github.com/ROCm/rocm-systems/blob/97f5574fe2fdc7bef44fb01545347912ee9f1779/projects/rocr-runtime/runtime/hsa-runtime/core/runtime/default_signal.cpp#L53-L119). The normal native [doorbell path writes mapped hardware memory](https://github.com/ROCm/rocm-systems/blob/97f5574fe2fdc7bef44fb01545347912ee9f1779/projects/rocr-runtime/runtime/hsa-runtime/core/runtime/amd_aql_queue.cpp#L471-L486).

The experiment mapped the copied HSA object with SHA-256 `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`, byte-identical to the recorded stock `libhsa-runtime64.so.1.18.70204`. The pinned official source explains the implementation consistent with that binary; it is not a proven source-to-binary build receipt. The newer local `rocm-systems` checkout is not deployed provenance.

The measured interval is **profiled dispatch end → next dispatch start**, not an independently measured signal-ready → consumer-start interval. HSA profiling exposes packet endpoints; it does not separately timestamp completion-value publication, barrier satisfaction, wakeup, or dispatch admission. CPU readiness receipts prove that a signal was zero when observed, but do not place that observation in the HSA clock domain. No subtraction between the two clocks is valid without calibration.

The unresolved interval can include producer release/cache work and completion publication, signal propagation, consumer command-processor recognition or queue arbitration, the next kernel's acquire operation, and dispatch admission. Existing results do not uniquely attribute it to firmware, hardware, or a driver-programmed policy. Bare prepublication demonstrates headroom for this implementation; it is not a proof of the best possible architecture.

## Next evidence required

Before another GPU performance variation, identify an observation that separates those boundaries. The next local work is read-only: inspect the installed, version-specific tracing capabilities and pinned ROCr/KFD/firmware interfaces, then write a measurement contract specifying the boundary observed, clock domain, resolution, and a control for instrumentation overhead.

Useful evidence would timestamp completion-signal visibility, barrier wakeup or queue eligibility, and dispatch admission. A tool that only repeats the existing dispatch start/end trace adds no information. Do not insert unreviewed vendor packets or assume clocks on different XCDs are directly comparable.

A controlled driver/firmware comparison with identical packets could also change the evidence, but needs compatible versions and a reserved node. Do not reboot or change drivers on a shared node. An instrumented AMD build may be necessary if public tools do not expose these boundaries. Prepare a concrete internal reproducer and request before seeking external action. This work has not sent anything to AMD.

A new runtime design needs an identified mechanism with enough predicted benefit to beat serial execution while preserving concurrency, memory visibility, and resource lifetime. Current evidence supports no new admission threshold, coalescing rule, native-wait policy, or helper budget. Other microbenchmark holdouts should run only after a candidate wins the original Hassan case.
