# Streams checkpoint — 2026-09-18, jobs53651/53652

The covered-tail diagnostic improves expert graphs and preserves about96% waiter-excess removal. It is neutral against the previous candidate on matched HiSparse C1. Hassan still needs a different execution plan: actual parallel execution is11.22% slower than stock; opt-in runtime coalescing preserves the earlier4% win against the stock event graph. No single tested setting wins across all workloads, and no package is production-qualified.

Both root-owned jobs completed and passed remote and independent local audits. Node2 only: one TP4 C1 allocation and one single-GPU micro allocation, using distinct Slurm GPUs. Model24timings,24natural retrieval checks,24worker identities/maps; broad micros176processes/46,912rows/313cells; Hassan50processes/800timings/1,000numerical checks. All trials are retained. No kernel, application, runtime binary or original benchmark protocol was changed for this checkpoint; no tracing, pinning, exclusions or gap investigation. Other tasks could use separate GPUs on the node.

## Immutable runtime identities

| Runtime | HIP SHA256 | Role |
|---|---|---|
| Installed stock | f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac | Baseline |
| Fused RC1 | 1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04 | Previous model-tested candidate; main PR1 runtime |
| Earlier coalesced | 862f3cd7eded1e9cd4f4f2037f83de0871a36c27afca3c880b9d658a5c895473 | Earlier Hassan winner |
| Covered-tail | 1f8cb274554d3437478ddee0eba00260d5d2a15a8462408127640f1984d41810 | New diagnostic, parallel and opt-in coalesced controls |

Shared HSA SHA256:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4. Exact loaded library/source/dispatch/reference/control identities are audited. Covered-tail source is the separately published diagnostic branch, not main PR1. Its package copies existing immutable bytes; there was no rebuild or deployment promotion. Block-sampling bytes are instrumentation and were not selected.

## Matched microbenchmarks

GPU microseconds, medians of process medians. Four balanced orders for original broad micros, ten balanced orders for original Hassan event graph. “Coalesced” changes runtime logical-stream placement and retirement only: the application DAG and kernels remain unchanged. It serializes execution and is not a parallel speedup.

| Benchmark | Stock | Previous RC1 | Covered parallel | Covered coalesced |
|---|---:|---:|---:|---:|
| Waiter excess: pending minus alone |2106.244|89.113|83.232|83.923|
| Waiter excess removed |—|95.769%|96.048%|96.016%|
| Expert b16 balanced,2 streams |230.417|229.748|226.068|411.394|
| Expert b16 balanced,4 streams |235.138|158.065|150.145|412.183|
| Expert b64 balanced,2 streams |114.333|117.104|110.093|168.975|
| Expert b64 balanced,4 streams |117.193|101.124|93.843|169.276|
| Expert b64 skewed,4 streams |193.027|164.146|155.725|308.540|
| KV gather parallel,h32/miss128 |701.252|708.801|702.051|752.763|
| 32-layer KV pipeline,2 streams |8602.128|8604.176|8605.715|8603.045|
| Matrix/KV parallel |217.737|218.527|219.587|263.599|
| Hassan original Q/K event graph |19.936594|22.105758|22.174016|19.144268|

Earlier exact862f coalesced bytes measure19.124619us in the same Hassan comparison; current coalesced differs+0.103%. That earlier result is preserved. The4% win is against stock's **event graph**. Historical matched52985 measured explicit stock serial19.2113us and stock events19.8384us; this is not a4% improvement over stock's best serial setting. The unchanged extraction includes two lazy initialization kernels; the separate [stock mechanism study](benchmarks/hassan_indexer/STOCK_MECHANISM_RESULTS.md) tests that artifact explicitly without rewriting these historical gates.

Across313aggregate primary cells, covered parallel has32wins beyond2%,270within2%,11losses beyond2%. All11losses occur in attention-fetch eager memcpy cases:5copy measurements lose6.06–7.85%;6total measurements lose2.03–3.44%. Signed per-round effects are mixed; no causal attribution or waiver is claimed. The graph-only covered-tail intervention is inactive in eager execution. Earlier76-cell expert/KV confirmation did not cover this full set. These losses need a bounded confirmation before a global neutral claim.

Unconditional coalescing loses44–79% on parallel expert rows, up to99% on dispatch rows, and21% on matrix/KV. It cannot be enabled globally. Complete family counts and every >2% loss are in [the full micro report](CHECKPOINT_20260918_MICROS.md); all913GPU/host/submit metric rows are retained in [CSV](CHECKPOINT_20260918_CELLS.csv). A2% screen is not statistical equivalence.

## Matched HiSparse GLM C1

Retained e4b3fe5 application,TP4,prefetch on/off,3trials per resident/state. ABBA residents previous-a/candidate-a/candidate-b/previous-b; all192measured intervals after64warmup tokens. Covered runs parallel, with coalescing and shared-retirement specialization disabled. These model numbers do not qualify the coalesced configuration.

| Block / prefetch | Previous RC1 ms/token | Covered parallel ms/token | Change |
|---|---:|---:|---:|
| a / on |15.276292|15.273703|-0.017%|
| a / off |15.052241|15.060291|+0.053%|
| b / on |15.256140|15.276318|+0.132%|
| b / off |15.047655|15.067823|+0.134%|

All frozen C1 screens pass (at most2% on and1% off loss in each block). The long27.086926ms/token previous-a/off trial is retained. Natural checks passed24/24 and are a limited retrieval screen, not exhaustive model correctness.

Historical best, from separate cohorts: C1on14.897670/off15.033; C4on17.800/off18.090ms/token. Earlier RC1 C1on15.096305–15.132294/off14.989466–15.037987; C4on17.917226–17.928416/off17.993069–18.003364. Fresh RC1 and covered C1on both run around15.26–15.28, so the current2.52–2.54% distance from historical best is not a covered-tail-specific regression. Cause is unassigned; historical cohorts are not interchangeable controls. Covered C4 has not run, and RC1 C4 evidence does not transfer to new bytes.

## Remaining gates

Keep the covered expert improvement and the immutable earlier Hassan winner. Explain stock's missing Q/K overlap benefit using the prewarmed extraction, then decide on a general runtime plan policy; no automatic selector exists. Confirm the eager-copy losses, complete exact-byte broader HIP/PyTorch and C4 qualification for a selected package, then canary with an explicit rollback. Main PR1 runtime and release defaults are unchanged by this report.

Local evidence root:`/home/sashawork/dev/amd-runtime-production/iterations/stream-checkpoint-20260918`; remote mirror:`/workspace/home/sasha/amd-runtime-production/iterations/stream-checkpoint-20260918`. Frozen specs:model-spec.json,micro-spec.json,hassan-spec.json; launcher:launch_checkpoint.py; raw:checkpoint-model-j53651,micro-j53652,hassan-j53652. Audit and manifest hashes, all trial values, source provenance and harness-only diff are retained there. No outstanding root-owned allocation from this checkpoint.
