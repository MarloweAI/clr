# Selective spare allocation: enabled path and pool lifecycle acceptance

Job52715 completed0:0 on node2, one GPU, in3m38s. It closes the bounded enabled-path
and heterogeneous pool-history checks left by [52660](QUALIFIED_SPARE_RESULTS.md).
The same diagnostic HIPcab16eff bytes are used; this is not a rebuild. The original
stock performance screen still fails on balanced b64 two-stream experts, so no
package is promoted or qualified for production.

## Enabled-path performance

Native waits1, node-count placement1, direct dispatch1, queue cap4, dynamic queues0,
streamops0. Diagnostic legacy/qualified share identical bytes. Stock has native and
placement0; immutable fusedRC1 has both1. Timings have all tracing/logging/DOT off.
The unchanged expert, grouped_s1 and grouped_s22 binary/reference files cover
76 cells in four Williams orders, eight retained trials per process:48 processes,
9,728 timing rows. Each table entry is the median of four process medians, in GPU
microseconds. All samples and signed per-round effects are retained.

| Graph cell | Stock | Immutable RC1 on | Diagnostic legacy | Diagnostic qualified |
|---|---:|---:|---:|---:|
| Grouped s22 L32, prefetch on |11558.533|10966.203|10910.311|10974.933|
| Grouped s22 L64, prefetch on |23143.509|21958.682|21949.551|21944.509|
| Experts b16 balanced, four streams |231.498|158.945|157.955|159.075|
| Experts b64 balanced, four streams |116.684|100.154|100.274|100.023|
| Experts b64 skewed, four streams |195.276|165.896|165.245|163.455|
| Experts b64 balanced, two streams |111.183|114.934|115.244|115.364|

Grouped qualified/stock gains are5.049086%/5.180718%; qualified/legacy effects are
+0.592306%/-0.022969%. This establishes preservation of the enabled placement gain,
not a new enabled-path gain from the qualifier. Four-stream expert stock gains are
31.284140%,14.278521%,16.295379% in table order.

The remaining b64 two-stream loss is **3.760001% GPU (+4.180501us)** and
**3.184028% host (+3.8475us)**. GPU losses by round are3.142746%,3.578829%,4.211222%,
3.395539%; host also exceeds2% in every round. Submission is10.785us versus10.0325us.
The qualified/legacy GPU difference is only+0.104129%; the allocator/entry-cost
cause remains unproved.

| Comparison | GPU losses/gains >2% | Host losses/gains >2% | Submission losses/gains >2% |
|---|---:|---:|---:|
| Qualified / legacy |0 /0|0 /1|3 /20|
| Legacy / immutable RC1 on |0 /0|0 /0|13 /18|
| Qualified / stock |1 /15|1 /15|10 /40|

The lone qualified/legacy host gain is an isolated b16 merge/eager cell; graph
policy is inactive there, so it is not attributed to the qualifier. Against stock,
the15 GPU/host wins comprise the12 grouped_s22 cells and three four-stream expert
cells. The other60 cells stay within2% GPU/host in this cohort; this is a screening
bound, not a statistical equivalence claim.

## Correctness, pool history and mechanism evidence

All144 correctness processes /3,744 rows from52660 are bound by manifest, audit,
source/spec and unchanged library hashes and revalidated. They were not rerun.
New pool tests add24 processes /2,304 correct launches: native0/1 × placement0/1 ×
qualifier0/1 × hardware queue caps1/4/8. In each process three coexisting kernel/
mixed executables undergo staggered destruction/recreation across six generations,
with launch counts8/16/24/24/16/8 and three verified distinct logical application
launch streams. Physical aliases at low caps remain explicit. Generation addresses
can be reused; records are bound to generation and lifecycle rather than address
alone. Each launch synchronizes, so simultaneous in-flight graphs are not covered.

The mixed graph includes asynchronous launch-prefix initialization, pinned H2D and
D2H completion checks; kernel and mixed generations require the expected arithmetic
outputs. Runtime receipts establish actual CreateStreams counts, selected queues,
and9,216 executed segment receipts. The six qualified mixed/placement-off processes
have generation allocation counts4/2/4/2/4/2; the other18 have4/3/4/3/4/3.
Pre-allocation `spare_requested` is not substituted for actual allocation evidence.

Four separate enabled-path proofs add512 arithmetic rows excluded from all timing.
They verify graph topology, actual stream creation, cached eligibility and selected
logical/physical dispatch queues. Full expert proof coverage includes26 graph
generations per arm,44 segment generations,208 launches and352 executed segments.
These traces establish selected queues and bookkeeping, not physical completion
order or measured GPU stall durations.

Independent Codex review checked all40 frozen input hashes, the lifecycle and
launch-stream bindings, and recomputed every median/round/contrast from raw CSVs.
No application change, workload tuning, model run, gap investigation or exclusion.

## Identities and remaining work

- HIP:cab16effd6d3b4af9205437fb0e1249e68cf87cb4379d77c737d12786c7bd6ff.
- HSA:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Frozen spec:459bf8ac7589af5bebcd290d57c6cda74752a05721413620ce13319225ef9903.
- Manifest:0074223b4cf377bd6a1a855073be8dcf1302475d3d883b4a8dc808c0e53d3fee.
- Raw: `qualified-acceptance-j52715` under the20260918 calibration iteration.
- Reproduction: `run_qualified_acceptance.py`, `qualified_spare_pool.py`,
  `qualified_acceptance_observer.py`, `graph_pool_history.cpp`,
  `submit_qualified_acceptance.sh`, `qualified-acceptance-spec.json`.

The selective policy is still a diagnostic patch, not applied to the PR runtime.
Next: resolve the two-stream stock regression; then qualify changed bytes against
broader microbenchmarks (including the user-requested Hassan workload), PyTorch,
waiter and model gates. Existing fusedRC1 model/PyTorch/waiter results cannot be
assigned to these bytes. The separate heap-allocation hypothesis has host/source
review evidence only and has no GPU result yet.
