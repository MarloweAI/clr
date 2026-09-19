# Graph-entry native prewait — job 51906

**Reject this policy.** Adding the existing native prewait to short pending graph-entry dependencies makes the affected microbenchmarks slower. The same-byte comparison has 14 aggregate losses above 2%; the fresh switch-off build has none against immutable RC2. No production change is selected.

One node2 GPU, root standalone launch/monitoring, Slurm 0:0. All 120 correctness processes, 8 separate untimed admission proofs and 144 timing processes passed. All 62,784 timing rows and 229 cells are retained, with six balanced orders and a locally re-audited raw/library mirror. HIP d4275ae9d672dde716779239ed6562b8a092534b6a8197bff0014e6b186a008a; HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.

The default-off diagnostic marks only graph-entry markers and matches their exact retained frontier signal. It admits a Compute producer without min24 history while preserving distinct physical queues, nonblocking registry lookup, signal/ABI checks, instruction retirement and the following ordinary full-system AQL barrier. Joins and all other dependencies retain min24. Dispatch/copy/barrier profiling, Agent events, non-DD and CPU waits preserve ordinary behavior. Source review corrected the operation-specific profiling guard before build.

| Preselected graph target | Switch off us | Switch on us | Original GPU change | Completed-start host change |
|---|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | 709.573 | 728.083 | +2.609% | -0.359% |
| b16-balanced, 4_streams | 160.825 | 173.296 | +7.754% | -0.327% |
| b64-balanced, 2_streams | 116.034 | 118.434 | +2.069% | -0.268% |
| b64-balanced, 4_streams | 105.123 | 105.484 | +0.343% | -0.081% |
| b64-skewed, 4_streams | 164.696 | 171.436 | +4.093% | -1.687% |

The b16-balanced/two-stream expert cell also regresses 15.911%, in every round. Completed-start controls have no aggregate >2% launch-host loss across all 172 cells. Actual entry prewait emissions were independently verified: 76 of 96 expert entry targets and all 80 KV targets in the untimed original-start proof; none in completed-start controls. One additional expert attempt observed completion before admission. The remaining targets had no pending match. Those trace frequencies are not asserted to equal untraced timing frequencies.

Waiter pending-minus-alone excess remains 95.799% removed with the switch on (87.560 us versus 2084.187 us on stock). This preserves the original long-wait benefit but does not compensate for short-entry losses.

| Every >2% same-byte original loss | Change | Rounds slower |
|---|---:|---:|
| attention_fetch, h128-miss128-r1152, gather-parallel, total, graph | +2.646% | 6/6 |
| attention_fetch, h128-miss128-r1152, memcpy-parallel, total, graph | +4.713% | 6/6 |
| attention_fetch, h32-miss128-r1152, gather-parallel, total, graph | +2.096% | 6/6 |
| attention_fetch, h32-miss128-r1152, memcpy-parallel, total, graph | +5.235% | 6/6 |
| attention_fetch, h32-miss128-r584, gather-parallel, total, graph | +3.854% | 6/6 |
| attention_fetch, h32-miss128-r584, memcpy-parallel, total, graph | +5.622% | 6/6 |
| attention_fetch, h32-miss256-r1152, gather-parallel, total, graph | +2.609% | 6/6 |
| attention_fetch, h32-miss32-r1152, gather-parallel, total, graph | +4.973% | 6/6 |
| attention_fetch, h32-miss32-r1152, memcpy-parallel, total, graph | +4.970% | 6/6 |
| dispatch, 256, 256, 1, graph, wide | +2.085% | 4/6 |
| experts, b16-balanced, 2_streams, total, graph | +15.911% | 6/6 |
| experts, b16-balanced, 4_streams, total, graph | +7.754% | 6/6 |
| experts, b64-balanced, 2_streams, total, graph | +2.069% | 6/6 |
| experts, b64-skewed, 4_streams, total, graph | +4.093% | 5/6 |

The extra native wait is causally harmful under the original pending-start setup; the unchanged completed-start controls support that interpretation. This does not identify a firmware implementation or prove the source of the original RC2 loss. The result strengthens the reason to retain cost admission for short waits. A pending dependency is not itself sufficient justification for native prewaiting.

The next architecture review concerns representing the entry dependency in the first captured batch while preserving SYSTEM acquire and lifetime through partial submission. The original dependency cannot be discarded. Timestamp, CPU-retirement, release-deferral and native-prewait changes have each failed to resolve the residual cost. The final fresh-byte HiSparse bridge remains held.

Raw root /workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-native-j51906; local mirror /home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-native-j51906. All metrics, per-round contrasts, rebuild controls and admission proofs are in contrasts.json.
