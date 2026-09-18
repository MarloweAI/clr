# Independent LONGPATH / SIDEWAIT attribution — job 50883

Node2, one GPU, root-owned standalone submission/wait/audit. Slurm 0:0;
60 timing processes / 12,800 correctness rows and 12 separate trace processes /
1,280 rows passed exact source, mapped-library, control, coverage and output
checks. Every factorial state occupies every factorial position once over four
orders; stock rotates separately. All samples retained.

Same HIP1db69b05 / HSA b8cdfe93, threshold24, unchanged workload source.
Microseconds, medians of four fresh-process medians:

| Workload | Stock | Neither | Coupled ordering | Side-policy only | Both |
|---|---:|---:|---:|---:|---:|
| Matrix + KV parallel graph | 217.767 | 215.207 | 219.267 | 215.027 | 217.228 |
| Grouped25,32 layers,prefetch on | 11581.966 | 11450.192 | 10940.485 | 11998.081 | 10994.120 |
| Grouped25,64 layers,prefetch on | 23200.030 | 22861.562 | 22017.849 | 24000.826 | 21793.972 |
| Grouped25,32 layers,prefetch off | 11547.015 | 10969.356 | 10882.184 | 11557.065 | 10938.898 |
| Four experts,b16 balanced,graph | 234.298 | 151.235 | 152.175 | 151.135 | 151.485 |

SIDEWAIT alone is rejected: every grouped25 graph row loses 4.7–5.7% versus
admission24 in all four rounds. Launch-stream role is not a sufficient reason
to suppress useful producer protection. Its mixed result is neutral in median.

Coupled ordering retains the useful grouped prefetch-on saving: 4.45% / 3.69%
at 32 / 64 layers. The combined state adds little consistently in this screen.
Mixed coupled-ordering is +1.886% in median, with rounds −0.940,+1.797,+1.218,+6.385%.
Combined is +0.939%, with −2.305,+2.369,−1.827,+2.652%. Thus this allocation does
not reproduce the earlier three-round 2.602% combined loss uniformly. It supports
ordering as the remaining suspect but does not settle its magnitude or a
universal causal mechanism. Preserve the independent 50851 result; do not erase
it using this noisier allocation.

Grouped trace emissions: neither 4472, coupled-ordering 4096, side-only 3108,
both 4094. Sorting also changes launch/side assignment and marker placement.
These aggregate traced counts do not measure packet costs or establish the
cause of untraced timings. Mixed emits zero native waits and has no interior
policy calls, while its ordering path executes in all relevant modes.

Next diagnostic: preserve the baseline segment-to-stream assignment while
changing only precomputed submission order. The current shared per-level sort
feeds both AssignStreamsToSegments and EnqueueSegmentedGraph; separate those
consumers before adding another ranking heuristic. Keep SIDEWAIT off initially.
Compare new/default, current coupled ordering and submission-only priority on
identical new bytes, with prior-byte bridges and unchanged mixed/grouped25/expert
controls. Verify segment/stream mappings separately from timing. Avoid allocating
or sorting new vectors on every hot graph launch. No benchmark-name whitelist.

The C1 bundle grid remains staged and unsubmitted. Exact-byte micro/PyTorch
compatibility passes do not qualify a runtime for production or establish a
model gain. No gap investigation or application changes were performed.
