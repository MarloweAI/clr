# Reverse-order C1 confirmation and held-out threshold64 — job50613

2026-09-18, node2, one TP4 allocation. Slurm0:0; the batch and standalone watcher
both completed strict artifact validation. All24 timing trials,24 process identities,
24 mapped-worker records and scheduling/control/helper receipts passed. Every192-
interval trial is retained, and raw means/medians were independently recomputed
from the fetched timing files. The repaired future-job owner completed all four
resident lifecycles; no experiment execution or monitoring was delegated.

Same HIP `500e91ca76c0b4b6e80a0f7439b9624cf850a286a1763f53697781b9eab14d90`,
HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`, e4b3 app,
fixed tapes/client, inherited CPU affinity and default graph scheduling/markers.
Runtime order relaxed→24→64→guarded reverses the original three-mode relative order.
Three alternating on/off requests per resident; resident is the intervention unit.

Milliseconds/token, lower is better; all retained trials:

| Mode | Prefetch | Trials | Median |
|---|---|---|---:|
| relaxed | on | 17.092317, 16.786397, 16.761268 | 16.786397 |
| relaxed | off | 15.079592, 15.084814, 15.083042 | 15.083042 |
| threshold24 | on | 16.821900, 16.766149, 16.746151 | 16.766149 |
| threshold24 | off | 15.090711, 15.085801, 15.087508 | 15.087508 |
| threshold64 | on | 17.947957, 17.980001, 18.017917 | 17.980001 |
| threshold64 | off | 15.065935, 15.061796, 15.078098 | 15.065935 |
| guarded | on | 18.034738, 18.014038, 18.037304 | 18.034738 |
| guarded | off | 15.081796, 15.075031, 15.073327 | 15.075031 |

Threshold24 prefetch-on improves **1.268589 ms/token (7.03%)**;
prefetch-off moves **+0.012478 ms/token (+0.08%)**.
This repeats the first allocation's6.75%on gain and0.08%off movement under reversed
relative order. Keep per-job contrasts separate rather than pooling token intervals.
The small24/relaxed ranking remains unresolved; relaxed still loses key micro cases.

Before submission, micro job50589 predicted64 near guarded and materially worse
than24 on prefetch-on. The frozen practical bands all pass:

- 24 beats guarded by at least2%: observed7.03%.
- 64 lies within +/-1% of guarded: observed-0.30%.
- 64 is at least2% slower than24: observed7.24%.
- Prefetch-off24/64 remain within +/-1% of guarded: observed
 +0.08%/-0.06%.

This is a successful held-out intervention prediction for the grouped prefetch
proxy, after its first calibration and an independent allocation. It does not
establish universal workload coverage, predict exact ms/token, or transfer the
micro's prefetch-off saving. These screening bands are not confidence intervals.
All within-resident requests and their intervals remain correlated observations.

The current16.766149ms/token remains12.54% above historical
14.897670 in a separate graph-optimized runtime/cohort. Do not call that difference
an attributable graph cost. Next compare guarded/24 × default/(ordering+side-policy)
on identical new bytes, after a rebuild bridge and unchanged micro holdouts. Measure
interaction, not added percentages. No marker omission or application tuning.
No production qualification, new natural-output model check, or C4 result yet.

Local rawroot: c1-model-j50613 in the stream-wait-calibration-20260918 iteration.
Remote model roots: /workspace/home/sasha/hisparse-runtime-combined-20260916/results/
c1-investigation-j50613-admission24-{relaxed,threshold24,threshold64,guarded}.
C1_CONFIRM_PREDICTIONS.md remains unchanged, SHA256
`d5845e9aff01eff0341ec7de1c68dc266e26957b82e4bd5f829d2aca1657d387`.
