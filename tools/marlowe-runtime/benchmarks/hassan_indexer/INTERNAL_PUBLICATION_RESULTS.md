# Internal packet-publication result — 2026-09-19

**Decision: close this mechanism as GPU-neutral; do not promote it.** Joint publication reduced host submission time 11.46%, but grouped two-stream GPU elapsed changed only −0.06% (round effects −0.310%, +0.147%, +0.621%, −0.507%). It does not provide the requested parallel speedup. Prior final-kernel completion remains the reference candidate.

Original warm Hassan Q/K GEMMs, splitK, inputs and dependency DAG are unchanged. G50 captures 50 pairs; g1 captures one pair. Diagnostic arms retain two physical queues and force the same segmented scheduler. Stock uses its automatic scheduler, so it is an overall application reference; prepared versus joint is the causal publication contrast. All timings are untraced.

GPU µs per Q/K pair, lower is better; median of four process-round medians, eight retained trials per process:

| Case | Stock | Previous kernel-completion bytes | New ordinary | New prepared/separate | New joint |
|---|---:|---:|---:|---:|---:|
| One stream, g1 | 13.275335 | 12.444109 | 12.487710 | 12.252650 | 12.142199 |
| Two streams, g1 | 14.112115 | 16.687098 | 16.671945 | 16.707844 | 16.667296 |
| One stream, g50 | 8.787940 | 8.722085 | 8.707036 | 8.707636 | 8.714835 |
| Two streams, g50 | 10.062230 | 10.219835 | 10.233438 | 10.244239 | 10.238037 |

Grouped two-stream host submission µs/pair:

| Stock | Previous | New ordinary | New prepared/separate | New joint |
|---:|---:|---:|---:|---:|
| 5.434650 | 2.694476 | 2.726987 | 2.669425 | 2.363563 |

The same-byte joint GPU result is **1.75% slower than stock and 17.48% slower than its own serial control**. New ordinary versus immutable previous bytes differs +0.13% in grouped GPU elapsed; the rebuild bridge is effectively neutral in this run. The earlier job54286 result for the same previous binary was 10.245336 µs; its contemporaneous result here is 10.219835 µs. Do not label the new 10.238037 µs a new best by comparing across jobs.

## What this isolates

The default-off diagnostic collects only retained internal graph dependencies for a singleton terminal kernel; graph entry is unchanged. Mode0 keeps ordinary completion preparation/submission. Modes2 and1 prepare the identical terminal IRQ signal before reserving queue space. Mode2 publishes wait and kernel separately; mode1 atomically reserves two slots when capacity allows, publishes the kernel behind an invalid prefix, exposes the prefix last, and rings one doorbell. Insufficient capacity or CAS collision falls back without an unpublished hole. The original dependency handles, full-width Barrier-AND, packet scopes, native admission/history, kernel and callback ownership remain.

Thus mode1/mode2 measures physical publication, while mode1/mode0 also changes completion-preparation order. Fewer host operations were measurable; GPU elapsed did not improve. This closes internal co-publication for the target protocol. It does not establish a firmware bug or prove that every packet-submission pattern is neutral. Entry-only co-publication was already neutral in jobs52496/52519; this was a different internal/terminal site, not a repetition.

## Audit and scope

- Root-owned Slurm job54404, node2, one GPU, COMPLETED 0:0. Standalone monitor waited to terminal and validated COMPLETE; soft inspection deadlines did not restart/cancel anything.
- 74 semantic/failure fixture processes, 14 untimed path proofs, 80 timing processes  / 640 retained trials, 14,382 numerical output checks. One common verifier ran before timing and at finalization. Independent local audit and mirrored library hashes match.
- Two physical queue proof: each detailed g50 replay cohort has 400 terminal kernel completions, 392 internal imports, 4 final fusions. G1 has no internal treatment. Readiness filtering remains active; imported edges are not assumed to be pending waits.
- Stress fixture verified all 512 replay scores per control, immediate graph destruction, exact 2-root/3-node failure prefixes, and no duplicate retirement. Joint mode cap1: 194 joint pairs, 5 ring wraps, 2878 true capacity fallbacks; cap4: 1790 joint, 3 wraps, 1282 capacity fallbacks. CAS collision itself was source-reviewed, not separately stress-tested.
- Sparse proof summaries below avoid one printf per edge; each summary stops at the final completed 64-selection block. The unreported partial block is not extrapolated.

| Sparse cohort | Selected | Ready | Deferred | Joint | Separate |
|---|---:|---:|---:|---:|---:|
| off | 384 | 0 | 0 | 0 | 0 |
| on | 384 | 0 | 384 | 384 | 0 |
| prepared | 384 | 0 | 384 | 0 | 384 |

- Source and harness received an independent Codex xhigh review (Fable quota exhausted; authorized fallback). No correctness blocker. Tests cover the bounded diagnostic scope; this is not general ROCm or production qualification.
- No full-model/HiSparse run and no broad micro holdout triggered, because no useful Hassan parallel winner emerged. Stock/previous binary and PR1 main runtime defaults are unchanged.

## Provenance

- Diagnostic source content commit `81a7a9a680ef3269f519f1d223d2b68117f6bcdd` on `marlowe/graph-internal-publication-diagnostic-20260919`. The commit was made after the build; build identity remains frozen basecab5670 + full.patch, not a claim that a post-build commit regenerated the same binary.
- New HIP SHA256 `9c5475310e2b2e670170f76b395e452d6f6c53cd2e683a963f3e5fd6d259eb69`.
- HSA SHA256 `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`; exact library exports `hsa_queue_cas_write_index_screlease@@ROCR_1`.
- Previous HIP SHA256 `0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4`; stock HIP `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`.
- Full patch SHA256 `959f3fb9065399662e85a997e630494e29302fb3e22a9bdb0a6d19e974b9b38c`; manifest SHA256 `62be4a15738f73fffd5d9a93c60de10fba772de6147b0ea946b4cc3ac4fe3afb`.
- Frozen protocol, source hashes, build/launch scripts, common verifier, raw artifacts, library copies and local audit are under `/home/sashawork/dev/amd-runtime-production/iterations/hassan-internal-publication-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`.

Next discriminator: bounded compute polling with separate graph-entry/internal site controls, always retaining the original dependency barrier. Existing long-producer polling wins motivate it; their sparse helper count does not establish a gain for 98 short internal dependencies. This port is not yet implemented or launched.
