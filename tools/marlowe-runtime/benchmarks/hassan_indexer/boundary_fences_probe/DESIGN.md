# Graph boundary fence placement

The second targeted follow-up after the deadline checkpoint. Job55382 proves that cached value-pointer reset removes more than99% of GPU-local preparation, but the original-sized graph still takes17.458us/pair versus actual HIP host16.595. Reset alone does not justify a runtime port. This test asks whether required visibility can be established with fewer expensive boundary fences.

All modes retain the identical ordered packet topology, signals, original Q/K code/resources/arguments, both graph-entry gates, final actual side dependency, host-visible completion and cached reset. Modes0/1 are conservative privatehost/local. Modes2/3 reuse their respective exact Signal objects with the following scope changes only:

| Packet | Conservative acquire/release | Candidate acquire/release |
|---|---|---|
| Main entry | SYSTEM/SYSTEM | NONE/NONE |
| Side entry wait | SYSTEM/NONE | NONE/NONE |
| First kernel of each lane | AGENT/AGENT | SYSTEM/AGENT |
| Remaining kernels | AGENT/AGENT | AGENT/AGENT |
| Final join | SYSTEM/SYSTEM | AGENT/SYSTEM |

Proof is bounded to this audited same-agent compute-only graph. Both first kernels remain ordered after the resolved entry; they import prior SYSTEM releases themselves. The final join is ordered behind Q and waits actual K completion, after both original AGENT release operations. Its AGENT acquisition imports both branches, then its unchanged SYSTEM release makes prior same-agent dispatch stores visible before ordinary host completion. Next graph cannot start before this join; same token dependency and ordering remain. Pinned hsa.h2850–2910 states acquire-before-active and release-after-active-before-completion across all queues of the same kernel agent. This does not authorize weakening SDMA, cross-agent, host-node or unresolved predecessor paths. No application changes; modified kernel packet scope is a runtime-lowering change, not changed kernel code.

Primary profile-off total includes all reset, publication, final completion and both-queue drainage. Profiling is separate. g1 andg50 each200pairs, four reversed/rotated rounds, eight trials, ninecells:576timings and4590numerical checks. Exact byte audit permits only the listed header bits and existing completion handles, verifies identical same-storage token addresses, original dependencies/arguments, both queue wrap and exact completion/guards. Changed-input/poison-output checks are mandatory. HIP reference has different submission boundaries; it indicates headroom rather than a causal denominator. Any positive result still requires actual HIP integration and asynchronous visibility/lifetime fixtures.

Root owns one node2 GPU job and standalone monitor. Soft120s startup/stall,300s run/queue observation windows; inspect same job, do not duplicate. Source freeze follows independent review. If no useful original-sized headroom remains, checkpoint this architecture instead of continuing reset/countdown tuning solely for the synthetic graph.
