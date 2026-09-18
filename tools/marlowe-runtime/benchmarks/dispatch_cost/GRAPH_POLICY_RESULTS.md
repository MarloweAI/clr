# Admission and graph policy: unchanged microbenchmarks

2026-09-18, node2, one GPU at a time. Timing job50764 completed all 126 timing
processes and 23,100 correctness rows. Its trace-stage assertion incorrectly
required segmented-graph policy receipts from the short-graph fallback case.
The failed job and raw artifacts remain unchanged. Job 50796 completed only the
missing untimed diagnostics on the exact measured executables. The derived
combined collection passed the independent audit, including 36 trace processes
and 3,264 rows. No timing was repeated or discarded to recover the audit.

HIP500e91ca is the prior admission diagnostic; HIP1db69b05 is the new diagnostic
with separately controlled node-count ordering and launch-stream interior marker
policy. All use exact HSA b8cdfe93. The four new-byte cells are guarded256/24
crossed with default/bundle. Bundle sets LONGPATH=1 and SIDEWAIT=1; it retains the
original AQL dependencies, strict physical eligibility and final-join prewaits.
There is no marker omission or unrestricted bypass. These bytes are not a release.

Selected medians of three process medians, milliseconds:

| Case | Stock | New guarded | New24 | Bundle guarded | Bundle24 |
|---|---:|---:|---:|---:|---:|
| Grouped25,32 layers,prefetch on | 11.5802 | 11.8078 | 11.4316 | 11.7045 | 10.8360 |
| Grouped25,64 layers,prefetch on | 23.1651 | 23.6596 | 22.8009 | 23.4559 | 21.9431 |
| Grouped4,32 layers,prefetch on | 8.9527 | 8.9445 | 8.9452 | 8.9443 | 8.9544 |
| Four experts,b16 balanced,graph | 0.2339 | 0.1514 | 0.1513 | 0.1522 | 0.1524 |
| Queued attention,4 streams,depth16 | 3.6852 | 3.6939 | 3.6832 | 3.6877 | 3.6913 |
| Pending fanout,3 consumers,cap4 | 10.0479 | 3.5729 | 3.5778 | 3.5701 | 3.5790 |

The bundle24 prefetch-on gain is 8.23%/7.25% versus new guarded, and5.21%/3.76%
versus admission24 alone at 32/64 layers. Prior-byte bridges are small in these
cells. Interaction in microseconds is negative in every round:32 layers
−499/−361/−503;64 layers−603/−577/−980. This supports a matched model experiment;
it does not predict an exact model percentage.

No comparison in the full screen loses more than 2% in all three rounds. That
screening rule is not a claim of no regressions: bundle_guarded's skewed64
four-stream graph has+2.37/−0.03/+4.35% versus new guarded. All process contrasts,
including eager/isolated cases and noisy movements, remain in contrasts.json.

The earlier rotation changed stock/prior positions but kept the four factorial
cells in the same relative order. This limits attribution. The next unchanged
transfer/pipeline/mixed and attention/waiter screens explicitly reverse and
permute the factorial cells. Matched C1 must also reverse or balance actual
resident interventions, with incremental bundle24/new24 predictions frozen first.

Compiled receipts show that the policy is active on grouped25. Its new24→bundle24
native emissions change4451→4078, side-interior permissions1112→1824, and
launch-interior calls1360→672. Sorting changes assignment and marker placement;
aggregate trace counts are not per-wait costs or a causal explanation of saving.
Experts execute the graph policy but emit no native waits; grouped4 and queued
show no graph-policy receipts; fanout emits but has no interior policy calls.
The next attention screen must cover both active graph policy and native emission.

The source-review concern about equal-level final endpoints remains unconfirmed:
all 528 graph completion observations in50724 passed. No speculative repair was
mixed into the performance comparison. Exact-byte framework qualification and
C1/C4 evaluation of the combined candidate remain pending.

Full derived report and raw origins live outside Git under the iteration root:
graph-factorial-combined-j50764-t50796/RESULTS.md, contrasts.json and audit.json;
original roots graph-factorial-j50764 and graph-factorial-traces-j50796.


## Additional holdouts and the remaining tradeoff

Job 50814 completed the unchanged attention-fetch, small-KV pipeline and mixed
compute/bandwidth suite: 63 timing processes, 28,896 correctness rows, 18 separate
traces and 4,128 trace rows. Explicit factorial orders reverse and permute the
interventions. Total bundle24 timings stayed within 0.8% of guarded. Some mixed
comparisons were about 2% slower than new24, motivating a new allocation.

Job 50829 completed unchanged fixed-work attention and the original waiter:
42 timing processes/9,576 rows and 12 traces/972 rows. No row lost more than 2%
in every round against guard,new24 or stock. Bundle24's waiter excess is 80.704 us,
versus stock 2061.005 us: **96.084% excess reduction**. Attention traces execute
interior policy and emit native waits (new24 ten,bundle24 eight); no packet-cost
attribution follows from those aggregate counts.

Job 50851 passed all 65 lifecycle/framework checks and 3,200 PyTorch correctness
rows on exact HIP1db69/HSA b8cd. Coverage includes native off, guarded, threshold24,
bundle off and bundle24, with queue caps1/4 where applicable. Event reuse,
threaded queue reuse, callbacks, transfers, cooperative work, queue churn and
pool rotation/fallback retain their existing outputs and dependency checks.
The opt-in package is `marlowe-hip-7.2.4-graph-admission-diagnostic1`; production
qualification remains false.

The same allocation independently repeated mixed work with stock/new24/bundle24,
each occupying every position once. Its 9 timing processes/1,152 rows and 2 traces/
128 rows all passed. Earlier serial/KV-KV movements did not repeat, but a different
specific loss did:

| Parallel matrix + KV graph | Stock | Admission24 | Bundle24 |
|---|---:|---:|---:|
| Median microseconds | 214.747 | 211.387 | 216.887 |

Bundle24 loses **2.602% versus admission24** in all three rounds
(+2.196%,+3.217%,+2.555%); it is+0.996% versus stock. Therefore do not call the
combined candidate neutral across the tested configurations. Framework correctness
and the 96% waiter result do not erase this tradeoff.

The staged C1 bundle grid is deferred. Completed job50883 separately enabled
LONGPATH and SIDEWAIT in four balanced factorial orders. SIDEWAIT alone loses
4.7–5.7% on every grouped25 graph row in all four rounds, so suppressing waits by
launch-stream role is rejected. LONGPATH retains useful grouped prefetch gains;
its mixed result is noisy and does not uniformly repeat the earlier 2.6% loss.
LONGPATH changes both assignment and submission order. The next diagnostic
separates those effects while holding SIDEWAIT off; no new ranking heuristic is
introduced. See [the split results](GRAPH_POLICY_SPLIT_RESULTS.md).
