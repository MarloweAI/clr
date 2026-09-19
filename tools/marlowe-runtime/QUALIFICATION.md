# Release evidence and promotion status

## V9 RC2 — September 17, 2026

The committed runtime recovers retained-app C1 prefetch-off to **14.984 ms/token**
(median of three trial means). The matched diagnostic v8 policy was 17.217 ms/token;
changing admission alone in that diagnostic recovered 15.041 ms/token.
The application, model, token tape and retained feature settings are unchanged.

| Exact final package C1-off trial | Mean ms/token |
|---|---:|
| 1 | 14.978330 |
| 2 | 14.984131 |
| 3 | 42.320421 |

Trial 3 includes a 5.262-second token interval; all samples are retained. Per-trial
interval medians are 14.891, 14.896 and 14.898 ms. These do not replace the complete
trial means above. The long-gap investigation remains paused at the user's request;
no cause is attributed. This release does not claim to solve serving latency tails.

Implementation: `cab5670a350678f2b0a6feb388fcbbca56c426a1` in CLR. Recipe:
`96b27db2b25c1f1975cfd1dee8b7f51754be93cc`. The package was built from clean committed
CLR/HIP sources in the pinned image, with matching HSA bytes. HIP SHA-256:
`43104e17679d8700f1d3f5a66160b63ba3cbd26fba2f46cab5802a58d4bb2115`. HSA SHA-256:
`b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Archive SHA-256:
`0e372ee761f68a7e144e23d13fe40551ca88f08390cef5e8c32f27c81f0ca7eb`.

| Final-byte qualification | Result |
|---|---|
| Fixed native-wait matrix on two physical GPUs, same node2 | 2 × 54 fresh processes; 2 × 14,958 measured operations; both screens passed |
| Original pending-wait excess | 95.7–96.0% removed |
| Queued attention / fragmented producer fanout | 36 processes, 5,904 rows; GPU and host headline screen passed |
| LLM stream matrix | 60 processes, 40,320 timings, 88 complete workload cells; no repeatable >2% GPU or host total regression against any control |
| Shared physical queue dispatch | 9 processes, 3,744 rows; screen passed |
| PyTorch minimal/events/graphs, off/on and queue caps 1/4 | 8 processes, 1,280 rows passed |
| Semantic checks | 12 processes passed |
| Pool pressure, blocked callback, concurrent queue recycling | 3 checks passed with actual native admissions |
| C1-off retained model | Six mapped processes; library and four-rank feature receipts audited |

The declared screen flags a regression above 2% in every paired round, using three
fresh-process rounds and retaining all samples. Passing this finite matrix does
not establish equivalence, universal neutrality, model-answer quality or readiness
for broad production use. Stock, disabled and enabled controls separate overlay changes from native-wait enablement. Component tradeoffs remain visible: fanout handoff grows
while producer and total execution improve.

### What Fable found and what changed

Four read-only Claude Fable reviews covered correctness and performance. The
performance review found that host-time admission could approve short fork/join
waits queued far before GPU execution. The first history candidate recovered C1
but regressed 16 queued balanced two-stream attention steps from 3.174 to 5.941 ms/step.
That candidate was rejected. The [new holdout](benchmarks/queued_streams/README.md)
preserves this counterexample.

The final policy preserves 256 actual own-kernel indices across harmless packet
gaps, and ends the history at pending cross-queue dependencies, engine changes,
and explicit stream-memory/IPC waits. The final queued two-stream case is
3.159 ms off / 3.165 ms on;
four-stream is 3.839 ms off /
3.837 ms on. The separate queued trace has zero native
packets; fanout has 72. The follow-up review identified the explicit stream-memory
wait reset, which is included. Conservative SDMA resets can still miss opportunities.

Earlier shared-queue trials had a performance flag; closer interleaving across stock,
v8 and the initial history candidate showed similar variability in every runtime.
The failed run remains retained. No unsupported clock attribution is made. The
canonical package's complete shared-queue screen passes.

### Deployment and remaining scope

Release `marlowe-hip-7.2.4-native-wait-v9-rc2` stays opt-in and
`qualified_for_production=false`. Use the existing pinned SGLang ROCm 7.2.4/gfx950
image plus the versioned overlay and restart workers with `GPU_NATIVE_EVENT_WAIT=1`
under its `run` launcher. Flag 0 is the matched disabled control; the stock image is
the third control. Restart with 0 to disable the policy, or remove the overlay to
restore stock. There is no driver or firmware deployment.

C1-on, C4-off and C4-on are handed to Benchmark combined optimizations for the
unchanged four-case comparison. Standard GLM on these exact bytes, broader model
correctness and an operational canary remain promotion work. Event forwarding
through a third stream and short prefixes of very long kernels remain missed
opportunities. Serving-gap investigation stays paused.

Full raw runs, complete control tables, source/library hashes and review outputs
are retained in `iterations/c1-runtime-recovery-20260917` on GCP and the same
campaign directory on the cluster. [Compact exact-byte receipt](V9_RC2_RECEIPT.json)
records the final artifact identity and observed gates. Prototype measurements do
not substitute for the final-byte runs above.

## Historical selective v8 RC1 candidate — September 17, 2026

The [selective policy](NATIVE_WAIT_POLICY.md) is implemented at
`77c75b8fa248f0dfc228df9a386289f868a247c2`; recipe commit
`963befb0f20271aecb63793c3b9eea8ab07ee35e` built the tested package from that pin.
Archive SHA-256:
`91d22e46ba481abbfa737adc91c215e7d4c6bf1359978ee7e585c201d8cb088c`.
The package remains opt-in and `qualified_for_production=false`.

The exact package passed the [fixed regression suite](benchmarks/native_wait_policy/README.md)
on two independent single-GPU allocations on node2, using different physical GPUs.
Each suite contains 14,958 measured operations in 54 fresh processes. Another 3,744
shared-queue operations passed. Every sample is retained; stock/off/on mappings
are verified per process. Both full runs passed the declared regression screen
and removed at least half the original excess wait time in every paired round.
Observed excess wait-time removal was about 96%, or about 38% lower total latency.
This finite screen does not establish universal neutrality or equivalence.

| Allocation | PCI bus | Pending graph stock ms | Off ms | On ms |
| --- | --- | ---: | ---: | ---: |
| 45710 | 0000:05:00.0 | 5.2292 | 5.2325 | 3.2214 |
| 45957 | 0000:15:00.0 | 5.2313 | 5.2244 | 3.2529 |

Values are medians of three process medians; paired deltas are retained separately.
The first allocation's balanced64 two/four-stream on times are 3.1484/3.6947 ms,
versus stock 3.1531/3.7103 ms. The late384/four-tail case is approximately 0.618 ms
in all modes. The old large short-chain and late-wait regressions do not recur in
these cases. An occupied-case fluctuation received two focused repeats, including
original RC4-off: roughly 1% differences changed sign, and new-off matched old-off.
All 5,664 supplementary observations remain available; they are not a claimed win.

Exact-package PyTorch checks passed 960 operations (minimal pending wait
5.2317 ms stock versus 3.2144 ms on). Twelve semantic processes passed. Native pool
pressure exercised 2,048 admissions, a buffer rotation and 252 nonblocking
fallbacks with 2,300 pending waits and no watchdog. Blocked callbacks and concurrent
eight-stream creation/recycling passed with actual native admissions. Four
read-only Claude Fable reviews examined lifetime, queue accounting and coverage.

Diagnostic traces confirm that late waits find only 6–70 remaining packets and
skip the prewait, while the original pending case finds about 2,040 and admits it.
On eligible long prefixes, handoff gaps still increase about 15–35us, while total
latency decreases 35–38% because producer interference falls much more. Component
tradeoffs and pending fractions are reported explicitly, not hidden by an aggregate.

The launcher passed off/on verification; a relocated archive passed verification
and the second full suite. Both microbenchmark allocations are released. Raw CSVs,
manifests, source hashes, review text and the full report are retained under the
campaign's `iterations/native-wait-neutral-20260917` directory; these development
artifacts are not substituted for production evidence.

The unchanged standard GLM stock/off/on C1/C4/C16 matrix uses node2, one eight-GPU
job per arm and a 900-second measurement target. Four of nine arms have completed
and passed the exact-recipe, ordinary-gate and process-library audits:

| Concurrency | Runtime | Job | Requests | Output tok/s | ITL p50 ms | TTFT p50 ms |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | Stock | 45964 | 32 | 83.90 | 11.7871 | 131.05 |
| 1 | Candidate off | 46052 | 32 | 84.07 | 11.7628 | 130.57 |
| 1 | Candidate on | 46128 | 32 | 84.13 | 11.7533 | 131.87 |
| 4 | Stock | 46237 | 124 | 317.10 | 12.3606 | 250.97 |

All 220 requests completed without errors; all 40 process receipts match the
expected runtime libraries. At C1, on versus off changes throughput by +0.071%,
ITL p50 by -0.081%, and TTFT p50 by +0.996% (about 1.3 ms). On versus stock changes
throughput by +0.265%, ITL p50 by -0.287%, and TTFT p50 by +0.631%. This first
triplet is approximately neutral; one job per cell does not establish equivalence
or a systematic small regression. C1 TTFT wave spread is 13–19%, and ordinary
first-wave warmup notes are retained. The C4 stock gate reports steady decode
with prefill-related throughput/TTFT variability. Metrics use Marlowe's unchanged
reducer; these reported percentiles are not a separate global serving-tail study.

The table above is the historical four-cell checkpoint, not a current queue-status claim. Those v8 cells do not qualify a later runtime.
The collector for on C1 required a transport recovery: all 121 copied files matched
remote SHA-256 hashes before the stalled SSH child was released. The original GPU
run and benchmark outputs were preserved. No runtime or benchmark change resulted.

Full v8 qualification and an operational canary remain outstanding before broad
enablement. Historical RC4 results below do not qualify v8. Configured profiler
proxy queues can suppress admission, and those altered runs are not evidence for
the unprofiled speedup. Serving-gap investigation remains stopped at the user's
request.

## Historical RC4 candidate

### Partial overlap and two/four-stream continuation

The extension in `benchmarks/attention_stream_chains` adds genuine data-dependent
join → query update → next-stage chains, balanced and 7/8-uneven partitions, and a
control with 2,048 CTAs per branch. Each case compares two/four parallel streams
with matching serial and wide single-stream schedules. Useful KV token work stays
fixed across schedules and arities. Stage counts change the query-feedback
computation; comparisons below are within each configuration.

Job 45210, one MI355X on node2, three fresh-process rounds per runtime:

| Configuration | Partitions | RC4 off serial ms | RC4 off parallel ms | RC4 on parallel ms | RC4 off wide ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Balanced, one long stage | 2 | 2.8786 | 1.5439 | 1.6055 | 1.4434 |
| Balanced, one long stage | 4 | 2.8772 | 0.8423 | 0.8992 | 0.7813 |
| Balanced, 64 stages | 2 | 3.4268 | 3.1436 | 5.9513 | 1.8378 |
| Balanced, 64 stages | 4 | 3.8688 | 3.6973 | 6.5402 | 1.2520 |
| Uneven, 64 stages | 2 | 3.4572 | 3.4762 | 3.8242 | 2.9183 |
| Uneven, 64 stages | 4 | 3.8891 | 4.5321 | 6.3737 | 3.0050 |
| Occupied control | 2 | 1.0346 | 1.0326 | 1.0651 | 1.0201 |
| Occupied control | 4 | 1.0527 | 1.0375 | 1.0803 | 1.0172 |

Values are medians of three process medians, with 16 measured trials per cell and
runtime/schedule order rotated. Stock reproduces the off-arm behavior: uneven
64-stage two/four-stream times are 3.4772/4.5396 ms; balanced 64-stage times are
3.1417/3.6973 ms. Every sample is retained.

Partial overlap is insufficient when the main branch owns 7/8 of the work: the
ideal speedup is near 8/7 before synchronization. With 64 uneven stages, four
streams are 16.5% slower than matching serial with waits off and 30.4% slower than
two parallel streams for the same useful work. Aggregate join gaps increase
250 → 1,026 us with two → four streams, while branch windows barely change.
The occupied control also gains essentially nothing from stream concurrency.

Native waits add another failure mode. In balanced 64-stage two-stream chains,
each branch lasts about 24–25 us. All 64 stages have overlapping branch envelopes
with waits off; with waits on, 45/44/48 of 64 stages lose overlap entirely in the
three retained trial-0 timelines. Paired process regressions are 89.1–89.8%.
Aggregate enclosing branch windows increase 1.975 → 3.379 ms and join gaps
0.623 → 2.101 ms, explaining most of the 2.81 ms latency increase. The individual
branch spans do not grow. Four streams do not cure the repeated boundary cost.
For uneven 64-stage chains, native-on four-stream latency is 66.7% greater than
two-stream latency and regresses 38.3–40.9% versus off in every paired round.

The native prewait adds a vendor packet before the original AQL dependency.
A delay hidden by a long main branch can become exposed when branches are short
or more joins are added. The exact firmware source of the boundary latency is
not yet proven. A separate trace-enabled diagnostic records 10,404 native packets,
nine pool rotations and zero pool fallbacks; its timings are excluded. This is
not the previously fixed instruction-pool submission stall in that diagnostic.

All 6,048 measured operations pass independent double-precision CPU reference
(155,713,536 output elements; maximum absolute error 3.58e-7, tolerance 5e-5).
Every operation checks dependency ordering. The independent analyzer validates
35,208 retained trial-0 branch/join envelopes against the aggregate timing CSV.
All nine process library identities match the pinned stock or RC4 hashes. The
allocation completed and was released. These are synthetic FP32 attention-like
kernels in one allocation, not tuned attention or independent-job replication.
CTA envelopes do not establish actual CU utilization. Native waits remain opt-in;
this extension does not alter the separate standard GLM serving results.

Executed producer manifest:
`63506bd8c05ff8cda6e0b31b97491238b0ca625e532a4d4cdce08cdbb3b87bc0`.
Exact producer and `benchmarks/analyze_attention_stream_chains.py` are committed.
Full stock/off/on tables, paired process comparisons, CPU-reference hashes,
timelines and audit remain in `attention-stream-chains-45210-final`, with the pilot
and trace bundles retained separately outside Git.

### Large-kernel fork/join regression

The attention-like fork/join microbenchmark in `benchmarks/attention_fork_join`
adds a workload where each branch is one substantial kernel rather than a chain
of tiny dispatches. Query preparation feeds two independent key/value partitions;
a stable softmax merge joins their results. Serial, two-stream and wide
single-stream schedules perform the same arithmetic and memory work.

On one MI355X (job 45143), dimension 64 and 8,192 tokens per partition:

| Query CTAs per branch | RC4 off: serial (ms) | RC4 off: two streams (ms) | RC4 on: two streams (ms) | RC4 off: wide single-stream (ms) |
| --- | ---: | ---: | ---: | ---: |
| 64 | 2.8676 | 1.5510 | 1.6080 | 1.4461 |
| 128 | 2.8778 | 1.5481 | 1.6146 | 1.4471 |
| 256 | 2.8778 | 1.5695 | 1.6288 | 1.5441 |

Values are medians of three fresh-process medians, with runtime order rotated
and 24 schedule-rotated measured trials per shape in each process. Two streams
are approximately 1.83–1.86x faster than serial with native waits disabled.
Native waits regress the two-stream case by 3.5–4.5% in every paired round;
serial and wide timings change by less than 0.7%. The wider single-stream control
shows that exposing more work in one launch can outperform separate streams.

At 128 queries, native waits add about 31 microseconds before the second branch
starts and 33 microseconds between branch completion and the join starting.
Branch execution spans remain nearly unchanged. These dependency-boundary costs
account for most of the measured regression. With only two long branch kernels,
there is little repeated-dispatch interference for the prewait to remove. The
measurements do not identify the precise instruction or firmware source of the
extra boundary latency.

All 1,944 measured operations passed comparison with independent double-precision
CPU attention (18,579,456 output elements; maximum absolute error 2.29e-8).
All 648 parallel joins were pending at submission, and per-CTA timestamps confirm
kernel-envelope overlap. All nine process HIP/HSA mappings and hashes were
verified. The stock arm uses the pinned image's `/opt/rocm` libraries; off/on use
the same RC4 package. No newer graph-scheduling patch is included.

This is a simple FP32 attention-like kernel, not a tuned attention implementation
or evidence about every production workload. One allocation and repeated fresh
processes do not constitute independent job replication. The runtime remains
opt-in; the tiny-kernel microbenchmark win does not justify global enablement.

Executed producer manifest: `a515e9d4bc9cbac7f1e27cedb4b0dcfd8557ea763a266d1245140f8d2ede772f`.
The exact producer is committed alongside `benchmarks/analyze_attention_fork_join.py`.
Raw runs, full stock/off/on tables, CPU-reference hashes and the audit are retained
outside Git in the `attention-fork-join-45143-final` result bundle.

### Previous RC4 qualification

Three Claude Fable review passes identified and checked fixes for instruction-pool
host stalls, re-entrant barrier construction, missing preload-alias validation and
unpinned HSA bytes. The source lock now targets
`85b0432bde51e66f8f79615de1022697ad59c5cf`. Native storage acquisition falls back to
AQL when a chunk is busy; a local retirement packet preserves the caller's pending
barrier state. The launcher preserves inherited library search order.

Clean build 41146 produced `marlowe-hip-7.2.4-native-wait-v7-rc4`, archive SHA256
`728378b9e86f8318260c05ed6caa252633c51363a02143b1efa69c815b197c9d`.
Qualification 41156 passed 720 Python and 720 C++ measured trials with actual-process
library receipts, 400 PyTorch event/graph checks and 12 bounded semantic processes.
PyTorch removes 95.8–96.2% of the added wait latency. The pressure regression submits
2,300 pending waits in 12.1 ms enabled, with one pool rotation, 252 fallbacks and no
watchdog release. RC3 needed its two-second watchdog at the 2,049th submission.
Correct output alone was not counted as passing this progress check.

Files-only checks reject missing, broken, redirected and dereferenced preload
aliases. Assembly rejects different HSA bytes even with the expected filename and
requires the orchestrator's pinned build-image identity. This identity is a
provenance declaration, not an in-container attestation.

A full mapped-library capture after matmul and a one-rank RCCL collective records
HIP/HSA replacement, base-image DRM selection, and additional COMGR and profiler-
registration libraries. Common library paths and hashes remain unchanged, including
the math and collective libraries. Stock-versus-overlay comparisons include these
transitive dependency changes; they do not isolate native waits.

RC4 prefetch-off pair 41183 completed on the same correctness-only application and
model protocol described below. Disabled → enabled median time per output token
changed by -13.99% at concurrency 1 and -6.39% at concurrency 4; the three-wave
ranges do not overlap. Each arm passes 3/3 long-context answer checks. All six
processes per arm map exactly the expected RC4 HIP/HSA hashes, with no unavailable
library hashes. Common library paths retain identical hashes; temporary versus
cached TileLang JIT libraries differ between fresh server processes. The pair runs
disabled then enabled in one container, so compilation-cache/order effects and
independent job replication remain limitations.

The enabled arm contains one 611.8 ms measured token gap, included in these
results, with no overlapping GC or CPU page-fault delta. Four TP workers show
107, 317, 276 and 395 ms increases in their maximum per-device KFD eviction
accounting over a 1.017 s sampling bracket. Do not sum per-device values or infer
a reason from these counters. The disabled arm has no gap of 500 ms or more.
This new pause means the pressure-test fix does not eliminate all serving pauses.

RC4 prefetch-on pair 41186 completed in reverse order (enabled then disabled).
Median time per output token changes by -1.96% at concurrency 1, with overlapping
ranges, and -8.56% at concurrency 4, with non-overlapping ranges. Each arm passes
3/3 long-context answers and all six process identities. All mapped library files
are readable; common paths have identical hashes. Temporary/cached TileLang JIT
library differences remain visible in this pair too.

| RC4 disabled → enabled | C1 median TPOT | C4 median TPOT | Wave ranges overlap? |
| --- | ---: | ---: | --- |
| Prefetch off, 41183 | -13.99% | -6.39% | Neither |
| Prefetch on, 41186 | -1.96% | -8.56% | C1 only |

The prefetch-on disabled and enabled arms contain respective 1.545 s and 1.562 s
measured token gaps. These stay in the comparison. Both overlap increases in
KFD eviction accounting: maximum per-device deltas across the four TP workers
are 617–845 ms disabled and 717–773 ms enabled, across respective 2.035 s and
2.020 s sample brackets. Neither gap overlaps recorded GC; the disabled arm has
one minor CPU page fault per worker and zero major faults, while enabled has
zero CPU fault deltas. These counters do not identify the eviction reason.

All four RC4 arms completed successfully: 12/12 long-context retrieval answers,
24 actual-process HIP/HSA identity receipts, and all 24 measured waves. This is
scoped model qualification, not independent replication or a serving soak. There
is no clear concurrency-1 prefetch-on win; the remaining gains require canary
validation. The large pauses persist with the feature both off and on. Earlier
model results below retain their RC2/RC3 identity. Production promotion remains
open; the current bounded experimental campaign is complete.
Use one active serving worker per GPU without unrelated co-located GPU workloads;
cross-process native-wait scheduling/QoS is outside current qualification.

## Retained RC3 and RC2 evidence

The following measurements belong to RC3 unless explicitly labelled RC2. They are
retained for provenance and comparison, not silently transferred to RC4.

RC3 removes about 96% of the added wait cost in the original pattern using
ordinary PyTorch. Model results are promising but do not yet justify production
promotion. The feature remains disabled by default.

## Artifact and environment

- Release: `marlowe-hip-7.2.4-native-wait-v7-rc3`.
- Archive SHA256: `b26203a7b69473097a4ffc796b2be4b6b1820d0f18be5ef9e434aff0779d1da1`.
- Runtime implementation: CLR `341796212db05fea04db2c142a3e18d4026d510c`,
  on ROCm 7.2.4 base `fe5035afc8713dfc6adedd3c00c4306c93a160f8`.
- MI355X / gfx950, PyTorch 2.11.0, ROCm 7.2.4 image. Qualification checks the
  libraries actually mapped by each worker, since PyTorch bundles another HIP.
- Tested filesystem image SHA256:
  `43b9e7ae1e56863cd48be7af67958b8dd7ff833a907f13763883cd668a13ce06`.
  This is a SQSH file checksum, not an OCI manifest digest.

The source lock specifies matching HIP headers and the packaged HSA library.
Rebuilding a release creates a new artifact identity; these results qualify the
archive above, not arbitrary builds from a moving branch.

## Original wait pattern in PyTorch

The included reproducer uses the original producer of 2,048 dependent increment
kernels, with no additional consumer work. It compares producer alone, a pending
wait on another stream, and an already-ready wait. Three alternating off/on
process pairs check payloads and confirm that pending cases were pending.

| Plain PyTorch result | Native wait disabled | Native wait enabled |
| --- | ---: | ---: |
| Added producer latency, range of process medians | 2,086–2,099 us | 84–88 us |
| Added latency removed | — | 95.8–96.0% |

All 720 measured Python trials and 720 C++ trials passed. This is a reduction in
extra cost imposed on the producer, not a 96% model speedup or zero overhead.
Job 40764 repeated qualification on the cleanly built, relocated RC3 archive.

The same artifact passed 400 ordinary PyTorch event/graph checks and 12 bounded
semantic processes covering callbacks, cooperative launches, real uploads, valid
event recycling and threaded queue sharing (job 40811). A lifetime screen passed
8,192 pending waits and 32 graph lifetimes in each mode, with no host iteration
over 8 ms (job 40862). These are scoped checks, not a serving soak. Archive checks
cover relocation, symlinks, licenses, hashes and rejection of corrupted libraries
before application execution.

## Full-model comparisons

The application is correctness-only SGLang at
`d8640de3a5e4065475641f5e8968c9b9ab3d6341`, with subsequent HiSparse performance
changes disabled. GLM-5.2 FP8 / BF16 KV runs with TP4, 32,768 input tokens, natural
1,024-token output, concurrency 1 and 4, and graph replay. Each arm has three
measured waves after warmup. Prefetch selection is verified in all four rank logs.
All measured common decode windows exceed five seconds. Pauses remain included.

Negative numbers below mean lower median time per output token. The isolated
toggle comparison uses the same RC2 stack in both arms. The separate stock-versus-
RC3 comparison includes the impact of replacing the bundled libraries.

| Comparison | Prefetch | C1 latency change | C4 latency change | Wave ranges overlap? |
| --- | --- | ---: | ---: | --- |
| RC2 disabled → enabled (40712 / 40730) | Off | -7.10% | +8.61% | Both |
| RC2 disabled → enabled (40778 / 40774) | On | -8.88% | -4.95% | Both |
| Stock → RC3 enabled (40819 / 40820) | Off | -15.11% | -9.60% | Neither |
| Stock → RC3 enabled (40827 / 40823) | On | -7.46% | -1.98% | Neither |

These are one process per arm with repeated waves, not independent job replication
or a broad no-regression result. Initial RC2 runs have multi-second pauses, including
pauses in disabled controls. RC3 jobs 40820 and 40823 have no measured token gap
of 500 ms or more. This does not establish that earlier pauses cannot recur.

Stock 40819/40827 and RC3 40820/40823 each answer three 32K-context retrieval probes
correctly. GLM puts reasoning and the final answer in one content field; the initial
scorer incorrectly reports zero correct. Independent strict scoring of the exact
six-digit answer after the explicit reasoning boundary gives 3/3, requiring normal
generation termination. Original responses and scores are retained. These probes
are not a comprehensive model correctness evaluation. Natural outputs also vary
within each mode, so differing output text alone is not attributed to the patch.

Three existing GPT-OSS20B workload screens on RC2—balanced 1024/1024, prefill-stress
8192/1024 and decode-stress 1024/8192—show overlapping timing ranges, with median
changes of -0.12%, -0.08% and -1.11% (jobs 40718/40729). The first two have common
decode windows shorter than five seconds. These are short screens, not canonical
replicated serving benchmarks or RC3 qualification. Fifteen simple known answers
on RC2 pass in each mode
after correcting the baseline scorer to inspect the final-answer channel.

## Driver investigation and remaining gates

A 565 ms stock-runtime token gap overlaps 280–536 ms of KFD queue-eviction
accounting across TP workers, with no recorded long GC pause. This is a driver
lead, not the cause of all pauses. The installed driver exposes per-process
eviction reason events. A one-GPU subscription probe and a separate instrumented
model diagnostic passed. The model capture recorded two short startup USERPTR
eviction episodes, but no evictions in measured decode windows and no token gaps
of 500 ms or more. The earlier large pauses did not reproduce, so their cause
remains unresolved. Instrumented timings are excluded from the primary comparison.
No host driver, firmware or kernel policy was changed.

Upload ASan processes complete workload checks but fail during shutdown with
native waits both disabled and enabled. They are not counted as sanitizer passes.
The investigator continues to reduce and diagnose this failure.

Before promotion, complete independent replication,
explain serving pauses and the sanitizer shutdown failure, validate the derived
image and rehearse rollback. Run a representative multi-GPU serving soak and an
opt-in canary with restart, output-health, memory, TTFT and decode-tail checks.
Exact traffic gates and named owners belong in the deployment release record;
these outstanding gates are not represented as completed here.

The existing Slurm/Pyxis integration runs the verified overlay on the pinned SQSH
base; [deployment and rollback instructions](SLURM.md) describe this tested path.
An OCI image is an optional distribution path and has not been built or validated.
No production canary has been completed. Pin the base and archive identities and
deploy through the launcher. Disabling native waits requires worker restart; full
rollback restores the stock image and removes both replacement libraries.

The interim backport depends on the pinned ROCr internal signal ABI and vendor
packet encoding. Broad upstream support requires an AMD-owned supported boundary
and a separately validated forward port to `ROCm/rocm-systems`. An official AMD
package should replace the overlay after the same qualification suite passes.
