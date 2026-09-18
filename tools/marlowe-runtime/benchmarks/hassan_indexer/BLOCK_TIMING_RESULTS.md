# Actual-replay block timing calibration — job 53530

A default-off sampler can measure completed graph replay blocks without changing application kernels, duplicating launches, enabling global profiling, or waiting on the host. It is not free: on Hassan, continuous eight-replay sampling adds 2.27% GPU time to the parallel plan and 1.33% to one-stream/shared retirement. With sampling disabled, the new build remains within 0.36% of the immutable predecessor on Hassan. This supports testing bounded exploration followed by an uninstrumented chosen plan; automatic selection has not been implemented or qualified.

Job53530 ran on one GPU of marlowe-mi355x-2 and completed Slurm0:0 in11m12s. Remote and independent local audits pass. Main PR1 runtime remains fusedRC1; this is a separate diagnostic. No prior waiter/PyTorch/HiSparse qualification transfers to these bytes.

## Fixed-plan comparison

All six arms use the same original Hassan Q/K kernels, scheduler, I/O shapes, data seed, correctness checks and timing protocol. Six balanced Williams orders compare the immutable covered-tail parent, identical new bytes with sampling off, and identical new bytes with sampling on, separately for parallel-covered and one-stream/shared execution. The parent is the earlier improved diagnostic, not stock. There is no stock arm in this probe-bias experiment.

Graph GPU time, microseconds per replay; lower is better. Values are medians of six process-round medians, retaining all eight trials in each process.

| Fixed plan | Immutable parent | New, sampling off | New, sampling on | Off/parent | On/off |
| --- | ---: | ---: | ---: | ---: | ---: |
| Parallel, covered-tail omission | 22.156482 | 22.165381 | 22.668698 | +0.040% | +2.271% |
| One stream, shared retirement | 19.196685 | 19.264886 | 19.521096 | +0.355% | +1.330% |

The parallel probe adds0.503317us GPU,0.503450us total host, and0.198554us CPU submission per replay. The one-stream probe adds0.256210us GPU,0.259399us host, and0.111588us submission. CPU submission increases4.49% and4.64%, respectively. The single-stream GPU probe effect ranges from−0.08% to+5.27% across process rounds; the parallel effect ranges+1.86% to+2.63%. Do not claim every round is within2%.

Single-stream remains faster with and without probes. The experiment still uses two explicit plans, not one policy that passes the portfolio.

## Original expert and grouped-KV holdouts

The unchanged benchmark binary, independent CPU references, four warmups and eight measured trials were used for108 timing processes,21,888 rows and76 aggregate cells:38 graph and38 eager. There were also two separate untimed structural-proof processes.

Across all76 aggregate cells, no GPU or total-host regression exceeds2% for either disabled-probe/immutable-parent bridge or either same-plan probe-on/off comparison. Some individual rounds exceed2%; all remain included. Sampling-on CPU submission regresses by more than2% in25 of38 parallel graph cells and13 of38 one-stream graph cells, with maxima11.91% and5.83%. Bounded sampling must count this cost rather than treating profiling as free.

Representative original graph total timings, microseconds:

| Workload | Parallel off | Parallel on | One-stream off | One-stream on |
| --- | ---: | ---: | ---: | ---: |
| b64 balanced, two streams | 109.873749 | 109.943749 | 168.265749 | 168.475498 |
| b64 balanced, four streams | 93.722999 | 92.863001 | 168.735750 | 168.925501 |
| b16 balanced, four streams | 152.175002 | 152.624998 | 411.373496 | 412.163496 |

Parallel execution remains essential for these expert cases. Universal serialization is not a solution.

## What the internal timestamps establish

The sampler uses one start marker and timestamp profiling on the existing final graph-release callback marker per block. The latter can add a packet; the start marker also changes the graph's entry frontier. Callback registration explicitly uses `blocking=false`. Callbacks copy POD/atomic fields only, including generation and direct hardware-event backing; they do not allocate, log, acquire a monitor, call stream APIs or own a GraphExec. Missing hardware-backed timestamps invalidate a sample.

Every sampled Hassan process has the original1,844 requested graph launches:four single correctness checks,200 correctness-burst launches,40 warmups and8x200 timed launches. Each produced230 valid eight-launch records plus one partial record. All12 sampled processes passed this audit. Ten otherwise-valid blocks per process cross known benchmark phase boundaries; these include CPU correctness work or trial synchronization. All raw blocks are retained and labeled separately. Their spans must not be pooled with homogeneous queued replay blocks.

The first-predecessor observation is pending even for those mixed blocks. Application timing/events can themselves occupy the launch frontier, so this single readiness observation is insufficient to classify the internal cadence of a block. A generic selector cannot use benchmark phase names to fix that limitation.

For blocks wholly inside a timed trial, the median internal marker-end span is22.013219us/replay parallel and18.973125us/replay one-stream, compared with external full-loop GPU timings22.668698 and19.521096us. The internal span has narrower boundaries and omits some probe/boundary cost. It preserves the plan ranking here but is not an absolute end-to-end cost measure. Any near-tie decision needs a margin justified by calibration, and claimed gains need a subsequent uninstrumented end-to-end comparison.

The fixtures also show that GPU synchronization need not mean all CPU completion callbacks have published their samples. Consumers must wait logically for ready, current-generation records without blocking the submitting host or assigning a winner retroactively to queued work.

## Correctness, lifetime and scope

Eighteen fixture processes pass63 exact-output rows. The new fixture is [graph_block_timing.cpp](graph_block_timing.cpp), byte-identical to the tested v3 fixture. They check device spans against external joined events for deliberately slow independent tails, exact kernel execution counts, one/eight-launch blocks, parameter updates, failed setters, launch-stream changes, disabled roots, destruction before completion, partial blocks, bounded graph/record exhaustion, and the existing injected-prefix failure cleanup. Original Hassan and expert proofs show optimized paths remain active while sampling is enabled.

Invalidation is inserted before the first possible exec mutation, including partial graph-update failure. Completed blocks can survive executable destruction through independent mailbox lifetime; incomplete blocks are abandoned. The diagnostic uses permanent bounded storage for64 graph executables and256 records each. Exhaustion disables recording while retaining ordinary execution. This storage policy and the missing deterministic overlapping-Run fixture are not production qualification. Concurrent setter-versus-Run races are not repaired by this change.

## Provenance and retained failures

HIP SHA256: `d1e45b7dde0256b03fa2a899acf87500c47418e00de8cdf82cd8ee66459623ee`.

HSA SHA256: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.

Exact build: base `cab5670a350678f2b0a6feb388fcbbca56c426a1` plus `block-timing-v2-full.patch`, SHA256 `495561003c97b8d9c2dc24b017ff7d9584d1c06610d6a189c12be212a8ead5c3`. Source content is published separately at [806273d](https://github.com/MarloweAI/clr/commit/806273d) on `marlowe/graph-block-timing-diagnostic-20260918`. That commit was created after the build; rebuilding the committed tree can change embedded version metadata. Actual tested libraries are retained and independently hash-checked.

Job53508 failed runtime compilation before GPU execution because the sampler accessed private base-class fields; v2 adds a read-only GraphExec accessor. Job53515 built the runtime but failed fixture compilation from a macro/member naming collision. Job53523 ran an off fixture with correct outputs, then failed the harness because controls were read before HIP initialization. Job53530 fixes the fixture initialization order and uses exactly53515's library bytes. These failures and their artifacts are retained; no performance trials were excluded.

Local evidence root: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-qk-micro-20260918/block-timing-v4-j53530`. Remote root has the same suffix under `/workspace/home/sasha/amd-runtime-production/iterations/hassan-qk-micro-20260918`. Local `audit_block_timing.py` verifies frozen source/harness/library bytes, fixtures, all original timing/correctness rows, and phase-separated timestamp records. `local-final-audit.json` records the result.

Next: a generic completed-replay activation rule, bounded comparable exploration blocks, immutable per-launch plans, and measured first-use/exploration/decision-lag/amortization costs. Preserve short-lived graphs' parallel default and stop measuring after adoption. Exact chosen bytes must subsequently pass the broader microbenchmark/waiter/PyTorch suite and HiSparse C1 prefetch on/off, followed by C4. None of those final qualifications is claimed here.
