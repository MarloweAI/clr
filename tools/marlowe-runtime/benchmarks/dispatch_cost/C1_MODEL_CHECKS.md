# Retained C1 model checks on the selected diagnostic bytes

Natural-generation job51320 completed Slurm0:0 on node2 with one TP4 allocation.
All12 long-context retrieval responses passed the existing expected-answer and
normal-stop checks. Both residents passed six-identity/control/mapped-library
validation (12 identities/maps total). A second audit of downloaded raw cohorts
reproduced the remote audit exactly. No performance measurements were taken.

| Exact-byte configuration | Prefetch on | Prefetch off |
|---|---:|---:|
| Strict admission24, baseline placement | 3/3 | 3/3 |
| Strict admission24, node-count placement | 3/3 | 3/3 |

These are the retained natural-generation probes at5%,50%,95% positions in a roughly
32K-token archive. The unchanged scorer checks the expected six-digit final answer
and finish_reason=stop. Ordinary chat request IDs bypass the retained application's
controlled-token hook; these responses use natural model samples. All full prompts,
helper source hashes, responses and receipts remain available. This small retrieval
screen is not comprehensive model equivalence or general quality qualification.

The runtime is the same immutable graph-tail-diagnostic1 package used for the
[C1 timing comparison](C1_PLACEMENT_RESULTS.md):
HIP d3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
Trace0, application e4b3fe5d, inherited CPU affinity. No runtime or application
changes were made for these checks. The package remains unqualified for production.

Local artifacts: iteration stream-wait-calibration-20260918/c1-natural-j51320,
including manifest.json, audit.json, mirror-audit.json and both raw cohorts.
Remote roots: /workspace/home/sasha/hisparse-runtime-combined-20260916/results/
c1-investigation-j51320-graph-natural-{threshold24,placement24}-natural.

## Executed-placement trace and its failed exact-graph gate

Job 51372 completed both trace residents, all four three-token replay requests,
and 12 worker identity/map captures. Its final auditor failed because it expected
PID fields in dump acknowledgements; the retained dump schema contains only
rank/action/complete. The corrected offline auditor retains the original PID-owned
fd2 logs, configuration receipts, mapped-library checks, topology and terminal-tail
checks. No GPU rerun was used to correct parsing.

The corrected audit then **failed the planned exact cross-resident graph match**.
All ranks observed the same differences: baseline prefetch-on had two 134-segment
structures (five and three launches), while placement had one 134-segment structure
(three launches). The later baseline and placement shapes differ by one node in the
final segment (23 versus 22); an earlier baseline shape also has shorter interior
segments. The trace does not establish why those captures differ. Subsequent C4
startup evidence exposed a harness readiness race: HTTP readiness could precede
the server's ordinary warmup completion. In these retained C1 trace artifacts,
response metadata places the baseline prefetch-on request before its parent's
warmup-complete marker (08:42:11–08:42:26 UTC); the candidate request begins after
its marker (08:46:11 versus 08:46:06). Consequently these traces describe observed
model activity, not exclusively request-owned work. This is compatible with startup
activity contributing to the baseline trace, but does not identify the ownership of
each extra launch or explain all topology differences. All records and
the failed gate remain preserved. Prefetch-off matches exactly: one 2,417-node
segment, three launches on each rank.

A narrower result does pass, independently reviewed by Codex xhigh: on every
candidate rank, all three observed graph launches contain 57 two-segment levels
with **physically distinct launch and side queues**. Enqueue position 0 has assignment
index 1 on the side queue; position 1 has index 0 on the launch queue. All 114 changed
assignment positions therefore change physical placement, not just sort labels.
Complete actual-tail records and successful responses accompany these mappings.

The source anchors stream slot 0 to the launch stream. Holding each candidate graph
and its observed stream pool fixed, baseline assignment-by-position would reverse
those 57 pairs. This is a **source-derived counterfactual**, not an observed matched
baseline. Baseline residents retain assignment-equals-position for both structures;
both prefetch-off paths have no reassignment. The narrower proof establishes that
the selected policy executes in HiSparse and is sufficient to proceed to the bounded
C4 screen. It does not establish equal captured work, explain the measured 9% gain,
or attribute latency to differences in aggregate native-wait emissions. Trace1
itself changes host work and queue progress; it supplies no trace0 timing evidence.

Artifacts: iteration c1-trace-j51372/{manifest.json,trace-evidence.json,audit.json},
original and corrected auditors, and both raw cohorts. The audit records
original_exact_graph_gate_passed=false separately from its narrower passed result.
A second offline audit of all downloaded raw traces reproduced the narrower
remote audit exactly. Slurm remains FAILED 1:0 from the original finalizer; no terminal status is relabeled.
C4 gate adjudication records this narrower acceptance before its launch.

