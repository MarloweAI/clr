# Graph-entry wait selection at consumption — job 52074

**Entry-containing GPU dependency barriers are usually submitted in original-start observations.** Experts select185of192 retained entry dependencies; KV selects80of80. Completed-start controls select none of272. All recorded producer and consumer physical queues are distinct; CPU signal waiting is disabled. This establishes packet selection/submission, not GPU stall duration or a performance benefit from CPU polling.

One root-owned node2 GPU, standalone launch/wait/audit, Slurm0:0. Two unchanged correctness probes and eight untimed observation processes passed. Exact544 imported entries, mapped hashes, controls, source/binary/reference bindings and correctness rows pass the local mirror audit. No latency column is accepted or summarized as a performance result.

HIP `b117b6bda30606011970b3a356b74f3bf53f59291ad23520d93bf14ebf50f6e6`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. The observer starts from fused51980 source; it changes no dependency filtering, native admission, fence scope, ownership, submission order or retirement rule.

The exact retained ProfilingSignal identity is passed to the ordinary wait helper. After its existing WaitingSignal call, the observer records membership in the selected wait vector, CPU-wait policy, the signal’s recorded producer queue ID and the locked consumer queue ID. It counts entry-containing AQL barrier calls after submission, separately from unrelated packets. Small scalars remain on the owning accumulator and are printed after full graph submission and final side-tail join. Native tracing is off; a separate observation flag controls this output. No new HSA status reads, timestamps, polls or sleeps are introduced.

| Workload and start state | Imports | Selected pending | Elided by filter | Entry barriers submitted |
|---|---:|---:|---:|---:|
| attention_fetch, original | 80 | 80 | 0 | 80 |
| attention_fetch, completed | 80 | 0 | 80 | 0 |
| experts, original | 192 | 185 | 7 | 185 |
| experts, completed | 192 | 0 | 192 | 0 |

The two original expert repeats select93/96 and92/96 entries; the two KV repeats each select40/40. All272 completed-start entries are elided. Every selected entry appears in exactly one actually submitted dependency barrier; no unrelated barriers occur at these sampled entry calls. Selection can precede signal completion before GPU execution, so the counts must not be described as measured GPU stalls.

This updates the earlier capture-point observer: a dependency can still be selected at the later consumption point, and it usually is here. It rules out a redundant ready check as the remedy. A short bounded CPU wait is now an experimentally relevant possibility, but these observations do not establish that the remaining wait is short, that CPU time is available cheaply, or that such a policy improves end-to-end latency. The next diagnostic must bound its CPU cost, preserve normal GPU fallback and report host elapsed time, rather than assume a benefit from the emission count.

Scalar instrumentation and output after each graph can affect later replay scheduling. The exact frequencies are observations of this diagnostic build, not estimates of uninstrumented production rates. The eight processes use the unchanged51845 binary, four retained trials plus four warmups, and original/completed/completed/original block order.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-consume-j52074`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-consume-j52074`. `observations.json` retains every process and group; raw receipts and all control/hash bindings are preserved.
