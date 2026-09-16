# Release evidence and promotion status

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

Three existing GPT-OSS20B workload screens—balanced 1024/1024, prefill-stress
8192/1024 and decode-stress 1024/8192—show overlapping timing ranges, with median
changes of -0.12%, -0.08% and -1.11% (jobs 40718/40729). The first two have common
decode windows shorter than five seconds. These are short screens, not canonical
replicated serving benchmarks. Fifteen simple known answers pass in each mode
after correcting the baseline scorer to inspect the final-answer channel.

## Driver investigation and remaining gates

A 565 ms stock-runtime token gap overlaps 280–536 ms of KFD queue-eviction
accounting across TP workers, with no recorded long GC pause. This is a driver
lead, not the cause of all pauses. The installed driver exposes per-process
eviction reason events. A one-GPU subscription probe passed; a separate instrumented
model diagnostic is queued. Its timings will not be mixed into the primary
comparison. No host driver, firmware or kernel policy was changed.

Upload ASan processes complete workload checks but fail during shutdown with
native waits both disabled and enabled. They are not counted as sanitizer passes.
The investigator continues to reduce and diagnose this failure.

Before promotion, complete independent replication,
explain serving pauses and the sanitizer shutdown failure, validate the derived
image and rehearse rollback. Run a representative multi-GPU serving soak and an
opt-in canary with restart, output-health, memory, TTFT and decode-tail checks.
Exact traffic gates and named owners belong in the deployment release record;
these outstanding gates are not represented as completed here.

The container recipe provides an integration path, but no OCI image or production
canary has been validated. Pin the registry base by digest and deploy the verified
archive via the launcher. Disabling native waits requires worker restart; full
rollback restores the stock image and removes both replacement libraries.

The interim backport depends on the pinned ROCr internal signal ABI and vendor
packet encoding. Broad upstream support requires an AMD-owned supported boundary
and a separately validated forward port to `ROCm/rocm-systems`. An official AMD
package should replace the overlay after the same qualification suite passes.
