# Minimal fused RC1 performance: broad52217 and confirmation52255

**The minimal fused package removes95.772% of waiter excess, but is not neutral everywhere and remains unqualified.** In the broad run, five candidate-on cells and six candidate-off cells lose more than2% to stock. Two candidate-on cells also lose more than2% to prior fused51980; neither aggregate loss repeats above2% in one unchanged confirmation. The two-stream expert stock loss persists across both allocations. Both runs remain reported separately, with no pooling or exclusions.

The tested package is `marlowe-hip-7.2.4-fused-rc1`, HIP `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04`, HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Its source/correctness evidence is in [FUSED_RC1_CHECKS](../graph_completion/FUSED_RC1_CHECKS.md); both jobs use those exact immutable bytes.

## Broad run52217

One node2 GPU,176 timing processes,46,912 retained rows,313 cells. Unchanged grouped classic/segmented, queued, fanout4/8, small KV attention-fetch, transfer pipeline, mixed kernels, experts, attention dispatch and original waiter workloads. Four Williams orders compare installed stock, candidate native/placement flags off, prior fused51980 mode2, and candidate flags on. AMD_DIRECT_DISPATCH=1, trace=0 and exact mapped HIP/HSA are audited in every process. Prior mode2 is explicitly set; unsupported old heuristics remain absent. Candidate automatic entry fusion still applies when its two optimization flags are off.

Stock HIP is `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`; prior fused HIP is `bf7ab37233fce87f88e00020c3538791d02ed549081d54274921487a654659e1`. All map the same HSA. Within-process trial medians are followed by the median across four process medians. All raw samples, signed effects and round values are retained.

| Waiter metric | Stock | Prior fused | Minimal fused on |
|---|---:|---:|---:|
| Pending-minus-alone excess, µs | 2096.306 | 86.980 | 88.624 |
| Excess removed | — | 95.851% | 95.772% |

All original >2% GPU elapsed-time stock losses follow. Positive values mean slower. The primary metric is GPU event elapsed time (queued/fanout/dispatch call it `total_us`).

| Mode | Cell | Stock loss | Rounds above2% |
|---|---|---:|---:|
| on | dispatch: 256 / 256 / 1 / eager / wide | +2.429% | 1/4 |
| on | dispatch: 256 / 256 / 1 / graph / wide | +2.601% | 1/4 |
| on | dispatch: 256 / 256 / 4 / eager / parallel | +2.536% | 2/4 |
| on | experts: b16-balanced / 2_streams / total / graph | +2.660% | 3/4 |
| on | experts: b64-balanced / 2_streams / total / graph | +3.602% | 4/4 |
| off | experts: b16-balanced / 2_streams / total / graph | +2.273% | 3/4 |
| off | experts: b64-balanced / 2_streams / total / graph | +4.482% | 4/4 |
| off | fanout_q4: 2 / 0 | +2.622% | 2/4 |
| off | fanout_q4: 3 / 0 | +2.513% | 2/4 |
| off | grouped_s22: h32-l32-miss128-depth1-planus0-backupside-splits22 / prefetch_on / total / graph | +2.254% | 4/4 |
| off | grouped_s22: h32-l64-miss128-depth1-planus0-backupside-splits22 / prefetch_on / total / graph | +2.420% | 4/4 |

The >=95% waiter screen passes; candidate-on and flags-off stock screens fail. Prior-fused comparisons also fail in two aggregate cells, listed below. Historical d3 and HiSparse are not tested in this broad run.

## One unchanged confirmation52255

32 processes,12,032 rows,94 cells: both entire expert and dispatch families, unchanged52217 executable bytes, references, trials and runtime arms, with the four Williams blocks reversed. The two primary cells and calculation were frozen before launch. No runtime rebuild, workload tuning, extra correctness suite, tracing or gap investigation. Exact library/control/source/binary/reference receipts and all row checks pass.

| New versus prior fused | Broad52217 GPU | Confirmation52255 GPU | Confirmation host | Confirmation submit |
|---|---:|---:|---:|---:|
| dispatch: 256 / 256 / 1 / eager / wide | +2.645% | -0.293% | -0.328% | +0.000% |
| experts: b64-skewed / 4_streams / total / graph | +2.241% | +1.018% | +1.003% | +0.934% |

Confirmation per-round GPU effects:

- dispatch: +0.042%, -0.582%, -0.667%, +0.000%.
- experts: +1.362%, -4.903%, +2.357%, +1.579%.

There are no aggregate >2% candidate-on/prior-fused GPU losses among these94 cells in52255. This is mixed evidence on the two new-port differences, not proof of equality or permission to replace52217. Eager dispatch does not use fused graph entry, so its first-run loss cannot be causally assigned to fusion.

The b64-balanced two-stream total graph case remains3.293% slower than stock with flags on and2.764% slower with flags off; all four rounds exceed2% for each. The other repeated stock-loss cells are below2% in this allocation. Earlier [clean repaired-stock evidence](ENTRY_BASELINE_RESULTS.md) localizes much of the two-stream penalty to required graph synchronization, without proving it unavoidable or waiving the stock target.

52255 completed Slurm0:0 in97seconds and passed its in-container live-library audit. The first offline checker compared integer round keys in memory to JSON string keys and stopped. A separate verifier normalizes only that serialization representation; the frozen runner, original manifests, audits, raw results and hashes remain unchanged. Remote and local saved-artifact audits then pass. No GPU rerun occurred for this checker defect.

## Decision

Do not add another micro heuristic or repeat this confirmation again. Preserve both failed stock screens and the exact candidate package. A diagnostic C1 on/off ABBA comparison against historical d3 is the next information needed to test whether this corrected package preserves the earlier model gain. It cannot isolate fusion alone: d3 differs in other code and lacks the generic launch-entry repair. It also cannot promote this package or waive the failed microbenchmarks. C4 follows only if C1 is promising.

Raw roots under `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918`: `fused-bridge-broad-j52217`, `fused-bridge-attention-j52217`, `fused-confirmation-j52255`. Remote mirrors use the same names under `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918`. Frozen specs, original audits, all raw contrasts and the independent artifact checks are retained alongside them.
