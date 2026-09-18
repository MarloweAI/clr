# Minimal fused runtime: retained HiSparse C1 — job 52299

**The current corrected package stays within 0.48% of the earlier d3 package in both C1 prefetch states and both matched blocks.** It passes the frozen model screens: no more than 2% loss with prefetch on or 1% with prefetch off in each block. This is diagnostic package preservation, not production qualification. The [microbenchmark stock losses](../dispatch_cost/FUSED_RC1_PERFORMANCE.md), especially two-stream experts, remain unresolved.

| Block | Prefetch | d3 ms/token | Current ms/token | Current / d3 | Current / historical best |
|---|---|---:|---:|---:|---:|
| a | on | 15.073574 | 15.132294 | +0.390% | +1.575% |
| a | off | 14.966989 | 15.037987 | +0.474% | +0.033% |
| b | on | 15.083628 | 15.096305 | +0.084% | +1.333% |
| b | off | 14.985459 | 14.989466 | +0.027% | -0.290% |

The historical context is 14.897670 ms/token with prefetch on and 15.033 with it off. Those numbers are from separate cohorts; only the d3/current block comparisons above share this allocation. Prefetch-on is approximately 1.3–1.6% above the historical best. This comparison does not retest released v9 or installed stock, and cannot attribute the small remaining difference specifically to entry fusion.

## Exact packages and protocol

- Current: `marlowe-hip-7.2.4-fused-rc1`, HIP `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04`, native wait 1 and node-count placement 1. These are the exact bytes from the PyTorch/HIP correctness suite and broad microbenchmark runs; no model-specific runtime changes.
- Historical diagnostic: `marlowe-hip-7.2.4-graph-tail-diagnostic1`, HIP `d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3`, strict admission 24 and cached length placement. It lacks the later generic launch-entry repair and is not a correctness-qualified baseline.
- Shared HSA: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.

One root-owned node2 TP4 allocation, four independently restarted residents in d3-a/current-a/current-b/d3-b order. Each ran the unchanged alternating C1 prefetch-on/off cases three times, then three natural-output probes per state outside timing. All 24 timing trials and 24 natural responses are retained. Each timing uses all 192 measured token intervals after 64 warmup tokens, with the full 256-token raw response retained. Application e4b3fe5, fixed 32k tapes, client, application controls and inherited CPU affinity are unchanged. No kernel tuning, gap investigation or outlier exclusions.

All 24 distinct identity PIDs and mapped-library records pass, including stable four-rank application-control receipts within each resident. The process-start observer checks AMD_DIRECT_DISPATCH=1 through both Python and libc before importing the unchanged retained entrypoint; its six PIDs must match each resident's six runtime identities. Native tracing is off. The observer runs outside performance timing and changes no runtime flag or application logic.

## Audit corrections and retained failures

The initial attempt 52268 completed only d3-a timing/natural requests, then failed the added post-timing `/proc/PID/environ` check. The application changes process titles, which can overwrite that initial environment view. The new observer reads the actual Python/libc environment at startup instead and is validated before timing. All original artifacts are retained; no 52268 timing enters the table. The full ABBA grid was restarted as 52299 with unchanged runtime and application bytes.

52299 completed every resident and its six-process library capture. Its original final checker then expected GPU_ARCH/GPU_ARCH_LIST labels, although the frozen owner removes all inherited GPU_* keys and neither profile sets those two. Thus Slurm remains **FAILED 1:0 from post-run audit**, not a successful scheduler exit. Independent review verified that all 24 actual control dictionaries exactly match the launcher prescription, including the child pinned-transfer flag; only the two stale expected labels differ.

A separate offline verifier corrects exactly that expected dictionary. The frozen auditor/spec, original failure and all raw data remain unchanged. It does not relax native/graph controls, startup DD checks, six-PID coverage, mapped hashes, application/tape receipts, natural answers or timing validation. Both remote and local strict audits pass all 24 timings/responses/identities/maps, and the mirrored contrasts reproduce byte-for-byte. The correction records its source hashes and retains the original Slurm status. No additional GPU run was needed for this final checker correction.

C4 has not yet been tested on this exact package. The C1 result supports an unchanged C4 diagnostic extension. It does not waive the failed microbenchmark screens or promote the immutable unqualified package.

Local root: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/fused-model-j52299`, with all four raw cohorts under `cohorts/`. Remote top-level audit root has the same basename under `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918`; original cohort roots are under `/workspace/home/sasha/hisparse-runtime-combined-20260916/results/c1-investigation-j52299-fused-model-*`. Preserved failed-attempt and auditor snapshots are `fused-model-attempt1-52268` and `fused-model-audit-original-52299`.
