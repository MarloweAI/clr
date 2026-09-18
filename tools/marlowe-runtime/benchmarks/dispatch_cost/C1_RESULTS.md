# C1 admission calibration — job 50519

2026-09-18, node2, one TP4 allocation, owned and monitored by Streams Investigator's
standalone launcher. All 18 timing trials and three canonical six-process mapped-
library finalizers completed. The batch exited 1:0 solely in our additional audit:
it incorrectly required the parent's environment dictionary in the five children.
The unchanged, archive-verified SGLang platform hook sets GPU_PINNED_MIN_XFER_SIZE
=4194304 in those children in every cohort. The corrected offline audit requires
that exact role-dependent setting and passes all 18 trials/identities/maps. The
failed log and original auditor remain preserved; no timing, app or runtime rerun.

Same HIP `500e91ca76c0b4b6e80a0f7439b9624cf850a286a1763f53697781b9eab14d90`,
HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`, retained e4b3 app,
fixed client/token tapes, inherited CPU affinity, default graph ordering/markers.
Worker controls, helper hashes, all scheduling receipts and stable rank/PID links
are audited. All 192 measured intervals per trial remain. Framework qualification
and timing-tape compliance do not replace natural-output model correctness checks.

Milliseconds/token, lower is better; every retained trial:

| Mode | Prefetch | Trials | Median |
|---|---|---|---:|
| guarded | on | 18.044230, 17.970727, 17.945672 | 17.970727 |
| guarded | off | 15.062926, 15.041696, 15.038562 | 15.041696 |
| threshold24 | on | 16.760737, 16.758511, 16.746025 | 16.758511 |
| threshold24 | off | 15.063182, 15.046012, 15.053441 | 15.053441 |
| relaxed | on | 16.850610, 16.863126, 16.726632 | 16.850610 |
| relaxed | off | 15.105745, 15.097252, 15.111244 | 15.105745 |

Threshold24 improves prefetch-on by **1.212216 ms/token (6.75%)**
versus guarded. Prefetch-off moves **+0.011746 ms/token (0.08%)**,
a small difference with overlapping trial ranges. Threshold24 recovers
108.2% of the same-run eligibility-preserving relaxed median gain.
Its small median advantage over relaxed is not an established ranking: their
trial ranges overlap and each mode has only one resident.

This supports the preregistered prefetch-on direction from grouped25-kernel
microbenchmarks. It does not validate a general proxy or a ms/token scaling factor.
The micro prefetch-off saving did not transfer as a measurable saving here.
Three alternating request trials in a fixed guarded→24→relaxed resident order
are not independent startup replications. A reversed order in another allocation
is the next confirmation; threshold64 remains held out from model calibration.
Run that intervention on unchanged grouped micros before preregistering its model
prediction. No multi-second-gap analysis, dropped trial or application tuning.

The historical best prefetch-on remains 14.897670 ms/token in a different runtime/
cohort with separate graph optimizations. Current threshold24 is 16.758511,
12.49% above that target. Ordering/side-policy gains cannot be assumed additive.
This is a diagnostic candidate, not production qualification or goal completion.

Local iteration root: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918`.
Artifacts: c1-model-j50519/ contains the fetched raw roots, audit and failed batch
log. Remote raw roots are results/c1-investigation-j50519-admission24-{guarded,
threshold24,relaxed} under /workspace/home/sasha/hisparse-runtime-combined-20260916.
Audit correction and source proof: C1_AUDIT_PLATFORM_CORRECTION.json and
C1_PLATFORM_SOURCE_PROOF.json. C1_PREDICTIONS.md is the unchanged preregistration.
