# Remaining-depth placement: rejected — jobs50961 and50969

Node2, one GPU at a time, root-owned standalone launch/wait/audit. Build50954:
HIP62b56ce9beabfc287514dc4013995cf7487ee1998950880e91a1264b26e1a04d,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
Basecab5670 plus patchcb6133748d31e0d66b696375c4226702febe1b03eaca5144d6e70534d6cead75.
This is a diagnostic, not a shipping runtime. No production-model job was run.

The structural rank is remaining successor-edge distance to a terminal segment,
computed once during scheduling. Stable ties retain baseline placement; a separate
assignment cache preserves baseline enqueue order. Admission24 and SIDEWAIT0 stay
fixed. Own node count does not break rank ties. Child-graph ranks remain local.

The initial scout50959 failed before GPU work at the benchmark's minimum4-trial
guard (launcher requested1). No guard was changed. Preserved original launcher/raw;
retry50961 used the standard minimum4 on identical runtime/workload bytes. Its9
untimed processes/960 correctness rows passed. The auditor independently rebuilt
ranks from all DAG edges and proved actual stable assignment and baseline enqueue
order: zero mixed/expert changes,160 grouped changes. Timings from this scout are
explicitly ineligible. Earlier writebacks form a chain; they are not all terminals.

Performance predictions were frozen before50969: at least1% prefetch-on improvement
at32/64 layers, with gains in at least5/6 paired rounds, and neutral controls.
Job50969 completed0:0 and passed90 timing processes/19,200 correctness rows,
9 separate trace processes/960 rows and240 original completion observations.
All six permutations of the three new-byte states ran; stock and priorHIP459949
baselines rotated separately. All samples were retained. Mapping/order matched
the frozen scout exactly. No gap investigation or benchmark-math tuning.

Microseconds, medians of six process medians:

| Workload | Stock | Prior admission24 | New baseline24 | Coupled length priority | Depth assignment |
|---|---:|---:|---:|---:|---:|
| Matrix + KV parallel graph | 219.977 | 220.237 | 221.738 | 219.167 | 220.788 |
| Grouped25,32 layers,prefetch on | 11582.469 | 11469.144 | 11463.585 | 10887.476 | 11506.257 |
| Grouped25,64 layers,prefetch on | 23156.431 | 22889.281 | 22862.534 | 21927.721 | 22963.264 |
| Grouped25,32 layers,prefetch off | 11560.218 | 10970.308 | 10979.260 | 10818.123 | 10972.530 |
| Four experts,b16 balanced,graph | 233.627 | 152.115 | 151.965 | 151.895 | 151.985 |

Depth fails the benefit prediction: prefetch-on is+0.372%/+0.441% versus new baseline,
slower in all six rounds at both sizes. Prefetch-off is−0.061%/+0.069%. Coupled
length priority retains−5.026%/−4.089% with all six rounds faster. Prior/new baseline
rebuild changes are small in these grouped cells (−0.048%/−0.117%).

No row loses>2% in every round. One unchanged-placement skewed64 four-expert graph
has a noisy+2.659% depth median (−2.918,+4.585,+0.831,−0.906,+3.751,+5.065% rounds).
This is not evidence of universal neutrality; the candidate is already rejected
for lack of benefit, so no extra confirmation allocation is justified for it.
Mixed coupled length priority is−1.159% this time. Preserve prior50851's repeatable
2.602% combined-policy loss and later noisy screens; this run does not erase them.

The scout shows fewer cross-stream edges at32/64 prefetch-on:84→72 and172→144.
Yet aggregate native emissions rise4474→4635 over the grouped suite (coupled4096).
A lower cross-stream edge count is therefore insufficient to select a faster
policy here. These traced counts are not packet costs or proof of the slowdown's
mechanism; signal readiness, producer history and resource overlap remain distinct.

Correctness scope: the original wide completion fixture passes, but every branch
has depth0, so this rule makes no assignment changes in that fixture. It does not
qualify changed-depth ordering. Any future retained assignment policy needs a
completion fixture exercising its actual changes and broader lifecycle/PyTorch
checks. Existing multi-device assignment can choose a foreign-device segment's
launch stream by global index; reordering can expose it. No general multi-device
qualification is claimed, and no speculative baseline repair was included.

Next discriminator: length-based placement with baseline enqueue order, completing
the assignment×enqueue factorial.50925 already tested baseline, enqueue-only and
coupled; only placement-only is missing. Use independent precomputed vectors,
verify exact maps/order, keep strict admission and interior waits fixed, and retain
stock/prior-byte controls. This can test whether placement alone retains the gain;
it cannot assume that node count estimates duration or solves the mixed tradeoff.
Do not advance depth or enqueue-only to a model experiment.

Full artifacts: graph-depth-j50969/{manifest.json,audit.json,contrasts.json},
graph-depth-terminal-j50969; scout graph-depth-topology-j50961/{audit.json,
edge-contrasts.json}; original failed scout graph-depth-topology-j50959.
