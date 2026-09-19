# Actual HIP graph-local signals — job 55216

**The frozen 50-pair Q/K microbenchmark now wins in actual HIP/PyTorch replay: 7.477 µs/pair versus stock two-stream 10.065 and matched serial 8.841.** This synthetic grouped graph uses Hassan’s unchanged kernels and scheduler; it is not his unchanged serving application/graph. The original-sized one-pair graph still regresses 17.04% against stock, so this diagnostic is not qualified and Goal 1 remains incomplete. No full model or broader microbenchmark suite ran.

Job 55216 completed 0:0 on node2 with one GPU. Remote and local frozen audits pass: 9 lifecycle/failure fixture processes, 12 path-proof processes, 64 timing processes, 512 retained timing trials, and 11,628 numerical comparison rows. Four rotated rounds contain eight fixed trials per cell. Values below are medians of round medians; every trial is retained.

| Microbenchmark graph | Stock | Same new binary, path off | New path, host-page signals | New path, GPU-local signals | Local vs stock |
|---|---:|---:|---:|---:|---:|
| Serial, one pair/graph | 13.658990 | 12.375849 | 12.650959 | 12.638310 | −7.47% |
| Two streams, one pair/graph | 14.226412 | 16.722443 | 16.688490 | 16.650690 | **+17.04%** |
| Serial, 50 pairs/graph | 8.888589 | 8.868487 | 8.872739 | 8.840636 | −0.54% |
| Two streams, 50 pairs/graph | 10.064526 | 10.284181 | 9.880071 | **7.477191** | **−25.71%** |

All times are GPU-event elapsed µs per Q/K pair, including runtime-induced device idle intervals. Each trial replays 200 pairs: 200 launches for the one-pair graph or four launches for the 50-pair graph. These are real launch boundaries, unlike the earlier direct 200-pair publication experiment.

## What is established

The matched host/local comparison uses identical HIP/HSA binaries, packet lowering, graph lifetime, reset, benchmark program and kernels; only private signal storage differs. Grouped elapsed time falls **24.32%**, with all four paired rounds improving 24.31–25.47%. Every local trial (7.434–8.990 µs/pair) beats every host-page trial (9.842–10.214). This reproduces the lower-layer placement effect inside actual HIP graph replay.

The grouped local path is **15.42% faster than its own serial control**, and 15.88% faster than stock serial. It preserves distinct physical queues and original dependency edges; no logical-stream coalescing or splitting of these captured benchmark graphs is used. Grouping 50 pairs is part of the synthetic test protocol, not a proposed application modification. Timings establish a useful two-stream execution win. The untimed packet receipts establish the lowering and queue structure, not independent wave-occupancy or completion-ready timestamps.

Host end-to-end elapsed agrees: grouped stock 10.111428, new host-page 9.919914, and GPU-local 7.513650 µs/pair. CPU submission is respectively 5.660766, 1.239938 and 1.268737 µs/pair. Moving signals locally does not improve CPU submission; its large matched benefit is in execution. Stock-to-candidate CPU and total differences also include the inherited graph engine/settings and cannot all be attributed to storage placement.

The one-pair graph has no internal cross-physical dependency to consume these tokens, so it structurally falls back. Its regression already exists with the new path off (16.722443 vs stock 14.226412). That narrows the next work to the inherited runtime/graph settings, rather than establishing a regression caused by local token placement. The enabling flag still has an eligibility-check cost: serial one-pair is about 2.1% slower than same-byte off, while remaining faster than stock. Neither observation permits a universal nonregression claim.

## Correctness and mechanism checks

The extracted scheduler, AITER/FlyDSL kernels, shapes, arguments, seeded data and numerical screens are unchanged from the frozen predecessor. `benchmark.py` is byte-identical to the preceding warm kernel-completion campaign. Compared with the canonical reproducer, this harness prewarms the capture stream, measures graph-only replay, and adds a synthetic 50-pair graph (100 kernel nodes). The original-sized one-pair graph has two kernel nodes. Do not transfer the grouped win to Hassan’s unchanged serving graph or E2E application. Maps before/after execution, external source hashes, frozen harness/build/patch manifests, original graph node counts, changed/restored input checks and all fixed timings are verified. Timing has no runtime trace/profiler enabled.

Each host/local grouped proof executes four actual launches, 400 original kernel packets and 392 cross-queue dependencies. The new path does not execute in serial or one-pair proofs. Path execution in timed processes is inferred from matched untimed proof processes with the same controls except trace enablement; there is no packet trace inside performance runs. Reset packets are ordered SYSTEM/SYSTEM; original producer/consumer packets retain at least AGENT release/acquire. The new runtime helper only resets graph-owned signal values/timestamps. Original Q/K kernels are untouched.

Separate fixtures cover a single physical queue fallback, parameter updates, disabled nodes, alternating launch streams, destruction before synchronization, and a partial-publication failure with joined side work. Host/local burst fixtures each queue 64 launches with 448 updates and checked outputs; receipts require multiple simultaneous generations and prohibit recycling one before its completion. Ordinary per-logical-stream retirement and final joins remain host-visible. These are bounded screens, not full production qualification.

Prior job 55209 stopped before timing because a fixture's multi-call output interleaved with a complete callback receipt. The old line-start parser missed that receipt. `HARNESS_CHANGE.md` documents the marker-based parsing fix, which recovers the unchanged failed log; old harness/raw artifacts remain intact. Runtime bytes did not change for the retry.

## Next decision and limits

Preserve this measured grouped win. Test source-grounded same-byte controls for the inherited short-graph regression, keeping the original application and kernels. Do not add shape, kernel-name or timing thresholds. Once a candidate keeps both short and grouped behavior acceptable, run the broader microbenchmark holdouts. This result does not establish HiSparse or GLM E2E performance.

This diagnostic requires a private ROCr build and default-off HIP flags; it is not a release package. The strict positive result is the matched storage-placement effect and grouped runtime win. The exact firmware/hardware step responsible for the storage sensitivity remains unidentified. The Goal 1 cutoff remains 2026-09-20 09:00 UTC; stop earlier if evidence no longer supports a concrete next step.

## Provenance

- HIP SHA256: `69f3df4efac18f3429ddc5951bdeb2d0dd821f8f1489bb78fb90e2f6dc8da254`.
- Private HSA SHA256: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- Source manifest: `9a208150aef0a181a7aeda414da398418c978095ee809449849daa6aa657df83`.
- Candidate patch against diagnostic parent `d4d8e825919b177f1dab9ed3c298878bd054c2b3`: `aa2d1eecff3a368f0b9e2a22ec917f4a91f17f18b0b39e87e99b5a5536c7eb6e`.
- Full patch against `cab5670a350678f2b0a6feb388fcbbca56c426a1`: `3f241a94a6e867ee1cf6650d8a61345350b4ef4fbbaaf5f2ae50ab3b8776e030`.
- Raw manifest: `6b1bde1deccfba6a3c16a89a183fd9f61a46ec6b7f2ae25add73c83887072ff4`.

Task directory `/home/sashawork/dev/amd-runtime-production/iterations/hassan-graph-local-tokens-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Raw `results-j55216`; `python3 run.py --out results-j55216 --audit` revalidates. `PERFORMANCE_CHECK.json` retains derived comparisons. Prelaunch xhigh source review passed. Independent post-run review reproduces all hashes, medians and complete fixed timing matrix, and specifically identifies the grouped-versus-original-sized graph boundary above. Frozen HIP source/build/harness receipts are archived with the report; private HSA source/build provenance remains in the earlier signal-locality checkpoint.
