# Minimal fused runtime: retained HiSparse C4 — job 52373

**The same corrected package passes the C4 preservation screens in both matched blocks.** Prefetch-on is 0.08–0.35% faster than d3; prefetch-off ranges from 0.23% faster to 0.04% slower. Together with the [C1 result](FUSED_C1_RESULTS.md), this meets the planned diagnostic model comparisons. It does not waive the [remaining stock microbenchmark losses](../dispatch_cost/FUSED_RC1_PERFORMANCE.md) or qualify production deployment.

| Block | Prefetch | d3 ms/token | Current ms/token | Current / d3 | Current / historical best |
|---|---|---:|---:|---:|---:|
| a | on | 17.942887 | 17.928416 | -0.081% | +0.721% |
| a | off | 17.995946 | 18.003364 | +0.041% | -0.479% |
| b | on | 17.981007 | 17.917226 | -0.355% | +0.659% |
| b | off | 18.034204 | 17.993069 | -0.228% | -0.536% |

Historical context is 17.800 ms/token on and 18.090 off, from separate cohorts. Current prefetch-on is within 0.66–0.72% of that historical best, and off is 0.48–0.54% faster. Only the d3/current contrasts share this allocation; the historical comparisons are not causal.

One root-owned TP4 allocation on node2, four independently restarted residents in d3-a/current-a/current-b/d3-b order. Each uses the unchanged six alternating C4 on/off cases, three trials per state. All 24 trials and 96 timed requests are retained. Each trial is the mean of its four request means, each computed from all 192 token intervals after 64 warmup tokens; all 256 output tokens per request are checked against the retained tapes. No CPU pinning, application changes, gap investigation, tracing or exclusions.

The runtime packages are exactly those tested in C1, with no rebuild:

- Current `marlowe-hip-7.2.4-fused-rc1`: HIP `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04`; native wait 1, node-count placement 1.
- Historical d3 diagnostic: HIP `d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3`; admission 24, cached length placement. It lacks the later generic launch-entry repair.
- Shared HSA: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.

The e4b3fe5 application, input tapes, client, inherited affinity, graph batches and complete application-control receipts are unchanged. The startup observer checks AMD_DIRECT_DISPATCH=1 through Python and libc for the same six PIDs later audited against their mapped libraries. Corrected control expectations are frozen before launch; no audit modification was needed for this job.

All 24 timing trials, 24 distinct runtime identities, 24 mapping sets and startup control receipts pass. The 24 untimed natural responses also pass; those are the unchanged C1 natural probes, while each C4 timing trial separately checks all four forced-token outputs. Slurm completed 0:0. The local raw mirror passes the strict audit, and recomputed contrasts match the remote file byte-for-byte.

The frozen C4 bounds are <=2% prefetch-on loss and <=1% prefetch-off loss versus d3 in each block. Both pass. Two restarted residents per package do not establish universal equivalence or deployment qualification. This is a package comparison, not a same-byte attribution of entry fusion.

No further full-model rerun is needed for this candidate without a new runtime or distinct unresolved concern. The remaining performance work is on the stock microbenchmark screens, especially the persistent two-stream graph cost and flags-off grouped cases. Keep the current exact package and model evidence intact while investigating a separate candidate.

Local root: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/fused-c4-j52373`, with all four cohorts under `cohorts/`. Remote audit root has the same basename under `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918`; original cohort roots are under `/workspace/home/sasha/hisparse-runtime-combined-20260916/results/c1-investigation-j52373-fused-c4-*`.
