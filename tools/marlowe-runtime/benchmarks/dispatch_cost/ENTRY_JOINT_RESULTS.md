# Joint entry publication: reject the diagnostic candidate

The joint-publication probe did not resolve the two-stream expert loss. Its target
is **0.209% slower than same-byte separate publication**, effectively tied with
immutable fusedRC1 (-0.044%), and **3.756% slower than stock**. The required >=2%
same-byte improvement fails. Do not promote this diagnostic, repeat its timing
matrix, or run a model comparison for it. Current fusedRC1 and its C1/C4 evidence
remain unchanged; production qualification is still false.

## Mechanism and review

The diagnostic reserves the required singleton entry AND and the first captured
kernel chunk together, holds the AND header invalid until kernels are ready, then
publishes the AND last and rings one doorbell. Separate mode publishes the same
AND and first chunk independently. It preserves ordinary native prewait/retirement
before reservation, uses W+1 for the existing chunk-size decision, shifts kernel
history indices past the prefix, and retains first-kernel SYSTEM scopes, actual
stream tails and dependency ownership. Only the existing qualified kernel-only
path with a fresh unprofiled accumulator can combine. Signal allocation/waiting
paths cannot run beneath an unpublished reservation.

The joint path also skips no-op ActiveSignal(false) cleanup for that fresh
accumulator. The comparison measures the implemented joint path, not a pure
measurement of one doorbell's cost. Independent Codex xhigh review found no
material source blocker and checked reservation capacity, ring wrap, fence state,
retained-event lifetime and both failure points. The implementation remains an
external diagnostic patch; it is not added to the production-shaped runtime.

## Correctness and proof before timing

Root directly submitted and monitored both jobs on one node2 GPU through the
standalone launcher. No benchmark agent submitted or watched these jobs.

Job 52496 built the diagnostic and passed 144 existing correctness processes
(3,744 rows), 24 injected-failure processes (192 rows), three 2,048-replay wrap
processes, and two untimed expert proofs. The matrix covers native/placement
combinations, separate/joint modes, queue caps 1/4/8, entry ordering, actual tails,
lifecycle, publication, host/device transfers and disabled roots. Faults occur
before reservation and immediately after publication; the fixture has exactly
one kernel per branch and verifies immediate graph destruction/kernarg churn.

Actual prefix-at-last-slot/kernel-at-slot0 observations numbered 105/51/5 at
caps 1/4/8. However, the four-kernel wrap fixture never exercised the near-capacity
reduction branch. The job correctly failed its pre-timing proof gate; **no timing
process ran**. This was a coverage failure, not an observed runtime error. Its
original raw files, spec, manifest and FAILED 1:0 status are preserved.

Job 52519 reused those exact runtime bytes and retained all 173 completed processes.
It added one untimed stable two-root graph: a short launch root plus 64 finite-delay
side kernels, repeated 2,048 times, queue 64/cap 1, placement disabled for this fixture.
All 2,048 entries used joint publication; 2,047 receipts prove actual capacity
reduction to chunk 1. The output is correct. This establishes capacity reduction
and forward progress, not time spent in the uninstrumented reservation wait loop.

Each expert proof has exactly 96 entry selections and 96 first-kernel receipts.
Ordered source-loop binding confirms all eight b64-balanced/two-stream frontiers
used the intended path in each arm, including all four retained proof trials.
Joint mode emits 71 joint entries overall; separate mode emits 72 ordinary ANDs;
the remaining frontiers were already complete. These untimed counts are not GPU
stall measurements. Runtime trace assertions verify the copied prefix remains
invalid until the kernel chunk is ready and preserves dependency/completion fields.

The continuation then ran the original timing matrix and completed Slurm 0:0 in
47 seconds. In-container mapped-library/control audits, a supplementary absolute
expert-coverage audit, and remote/local saved-artifact audits pass. Combined
coverage is 190 processes / 11,012 rows: 16 timing processes contribute 6,656 rows;
untimed proof outputs are never used as performance data.

## Unchanged expert-family timings

Same 52217 executable (`de0bc5d2fa4d589868a6ed43dd831c461eb54cca8706fad42c3d4003df50e83b`),
reference data, 52 cells and eight retained trials per process. Four Williams orders
compare stock, immutable fusedRC1, diagnostic separate, and diagnostic joint.
Timing uses AMD_DIRECT_DISPATCH=1, native/placement on except stock, queue cap 4,
all tracing/faults off. Within-process trial medians are followed by the median
of four process medians. All samples and signed per-round effects are retained;
no exclusions, pooling, application tuning or model runs.

B64-balanced / two streams / total / graph, microseconds (lower is better):

| Runtime | GPU | Host | Submission |
|---|---:|---:|---:|
| Stock |110.763749|120.380000|9.062500|
| Immutable fusedRC1 |114.973750|124.290000|9.717500|
| Diagnostic, separate |114.684001|123.800000|9.580000|
| Same diagnostic bytes, joint |114.923500|124.187500|9.645000|

| Target comparison | GPU | Host | Submission |
|---|---:|---:|---:|
| Joint / separate |+0.209%|+0.313%|+0.678%|
| Joint / fusedRC1 |-0.044%|-0.082%|-0.746%|
| Joint / stock |+3.756%|+3.163%|+6.428%|
| Separate / fusedRC1 |-0.252%|-0.394%|-1.415%|

Target joint/separate GPU effects by round: +0.575%, +1.454%, -0.332%, -0.418%.
Joint/stock: +3.442%, +4.984%, +2.771%, +3.885%. The stock penalty exceeds 2%
in every round.

Across all 52 cells, joint/separate has zero >2% GPU or host improvements and zero
>2% GPU or host losses. Submission has seven improvements and seven losses above 2%.
Against immutable fusedRC1, joint has one elapsed-time loss cell: b64-balanced /
four streams / total / eager, GPU+2.043%, host+2.125%. Its GPU round effects are
-2.418%, +2.731%, +0.594%, +3.122%. That eager path does not use joint graph entry;
the mixed-round difference cannot be causally attributed to this mechanism.
It remains in the failed aggregate screen. Separate/release has no >2% GPU/host
loss in any cell, so the build-control comparison is retained as well.

Other joint/stock losses above 2% are b16-balanced/two-stream total graph GPU+2.173%
and b64-skewed/isolated merge eager host+2.634%. The existing four-stream graph
wins remain, but no elapsed-time cell improves by >2% versus same-byte separate.
Full medians, submission effects and all signed rounds are in `contrasts.json`.

The frozen screen requires >=2% target GPU improvement versus separate, improvement
versus immutable release, and no new >2% GPU/host loss versus either across the
family. **It fails.** This closes the publication-boundary hypothesis for this
bounded implementation; it does not prove synchronization cost unavoidable.
Grouped-copy flags-off regressions remain a separate unresolved path. Correction
after job52568: those grouped captures have one root, so the launch-entry fork
is inactive. D2H ineligibility for kernel-only entry fusion does not imply an
entry fallback marker exists. See [grouped attribution](GROUPED_ATTRIBUTION_RESULTS.md).

## Reproduction and identities

Local iteration root:
`/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918`.
Remote mirror uses the same suffix under `/workspace/home/sasha/amd-runtime-production/iterations`.
Raw roots: `entry-joint-j52496` and `entry-joint-finish-j52519`. Both preserve all
CSV/logs, controls, mapped hashes, binaries and reference data. The continuation
explicitly binds its retained prefix to the unchanged 52496 manifest.

- Stock HIP: `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`.
- Immutable fusedRC1 HIP: `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04`.
- Diagnostic HIP, both modes: `111123f824ce7d121cff2f68cb631f82e238cd4b6742aecf3aa9b77616275c1f`.
- Shared HSA: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Build base: `cab5670a350678f2b0a6feb388fcbbca56c426a1`; full patch SHA256: `34a000b43ab1dc0fc19435fdf98cccea3fb0756d9dda2a8c4d8778fb48250d0b`.
- Original frozen spec: `d0eb793f98fb49cb431c1b7183af3e00e848ddb940cc1fe9704a3801de815d2a`.
- Continuation frozen spec: `d3f4746c8a502f51d9ad6d7d7d37e3bd2918cd8c941464bbf2a3a491b5ceb204`.

Sources and launchers: `entry-joint-port.patch`, `entry-joint-full.patch`,
`run_entry_joint.py`, `run_entry_joint_finish.py`, `verify_entry_joint_proof.py`,
`graph_entry_joint_failure.cpp`, `graph_entry_joint_wrap.cpp`,
`graph_entry_joint_pressure.cpp`, both submit scripts and frozen specs. The
supplementary completeness auditor was declared during the first job's build;
it does not alter either job's frozen inputs or failed/successful status.
