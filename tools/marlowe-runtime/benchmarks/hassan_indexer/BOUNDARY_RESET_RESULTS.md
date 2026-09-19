# Graph boundary and signal-reset checkpoint — jobs 55349/55382

**GPU-local signal reset was expensive because the public API read GPU-resident metadata. Caching the value pointer removes over99% of that preparation cost, but the original-sized graph is still too slow.** This is a lower-layer packet result, not a new deployable runtime.

Both jobs completed0:0 on node2 with one GPU each. Job55349 passed448timings and3570numerical checks. Job55382 passed704timings and5610numerical checks, with independent source review and strict remote/local audits. All trials are retained. Original Q/K kernels, resources, arguments and graph dependencies are preserved; unlike older flattened replay, every graph has an explicit entry fork and one ordinary host-visible final completion.

## Matched reset comparison (55382)

CPU wall microseconds per pair, including preparation, publication, final wait and both queue drains; median of four round medians, eight trials each. API/direct arms share the exact signal objects and packet buffers. Private host and GPU-local signals have identical dedicated-page allocation semantics.

| Graph | Signal storage/reset | Preparation | Total |
|---|---|---:|---:|
| Original-sized one pair | Private host / API |0.028025|26.249055|
| Original-sized one pair | Private host / cached pointer |0.035087|26.264855|
| Original-sized one pair | GPU local / API |7.173915|24.575919|
| Original-sized one pair | GPU local / cached pointer |**0.040288**|**17.457743**|
| Synthetic50pairs | Private host / API |0.007125|9.923515|
| Synthetic50pairs | Private host / cached pointer |0.012700|9.942290|
| Synthetic50pairs | GPU local / API |4.804776|12.112201|
| Synthetic50pairs | GPU local / cached pointer |**0.014650**|**7.334365**|

GPU-local preparation falls99.44%/99.70%; total falls28.96%/39.45%, improving every paired round. Post-publication latency changes only+0.13%/+0.11%, while host-storage total changes+0.06%/+0.19%. This isolates reset lookup overhead rather than faster kernel execution. The host direct-reset path adds about6–7ns/pair of preparation, insignificant compared with its total; no host-reset speedup is claimed.

The actual HIP/PyTorch reference in this job is16.549699/7.410746 GPU-event us/pair and16.594579/7.449026 host us/pair for g1/g50. Submission boundaries differ, so these are headroom context, not a causal denominator. The short packet candidate at17.457743 still does not beat even the current experimental HIP reference; that HIP version already regresses short graphs versus stock. The grouped7.334365 does not establish an original-application win. No actual runtime was modified or promoted by these probes.

## Correction to55349

The predecessor measured pooledhost/privatehost/privatelocal totals26.162093/26.253245/24.512044 atg1 and9.973039/9.946164/12.122051 atg50. GPU-local preparation was7.135665/4.748325. Its frozen comment/design incorrectly described preparation as store-only with no internal reads. Although explicit guard/value reads were moved outside timing, hsa_signal_store_relaxed calls Signal::Convert, which reads SharedSignal validity/IPC/core_signal metadata from GPU memory before BusyWaitSignal::StoreRelaxed. These were not plain-store cost floors. [ERRATA.md](boundary_tokens_probe/ERRATA.md) preserves that correction without editing frozen source or raw results.

55382 obtains a volatile hsa_signal_value_t pointer once, outside timing, through hsa_amd_signal_value_pointer. Its aligned64-bit store is statically verified lock free. Previous work is fully drained before reset; the signal owner lives through all uses. SFENCE and ordinary ROCr packet publication follow reset. Internal timestamp clearing is matched and specific to the pinned diagnostic ABI. No live reset, host RMW or changing signal address is allowed. Changed-input/poison-output tests, exact completion/guard checks, packet byte equality, mapping/library hashes and queue-wrap checks pass.

## Next decision

The remaining short-graph cost is after publication. A reviewed same-agent compute-only fence-placement probe will move system acquisition to the first kernels and retain AGENT-acquire/SYSTEM-release at the final join. It preserves both branch dependencies and host-visible completion. This is a bounded architectural question, not a generic fence weakening. A lower-layer win would still require actual HIP/PyTorch integration and asynchronous visibility/lifetime validation. No wider microbenchmarks or full model run is warranted yet.

## Provenance

Both jobs use HIP69f3df4efac18f3429ddc5951bdeb2d0dd821f8f1489bb78fb90e2f6dc8da254 and private HSA2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12, unchanged from55216. Helpers are rebuilt and hashed per job.

- 55349 source manifest b6e458cfecfafedc38a5ce5ddafb1bec8323345d2bfd459a2b060411da93f760; raw manifest8ab2d5374a75eb26319e9a1e27235882637d2b3fd1ba9b75f9e7cb8fab89a29c.
- 55382 source manifest0f00cc3c51dbdd1184ae00c93005b6f1bb56e313090313ee1aa16bc7034760c7; raw manifestc0e61aac2f6f7e16a1472b54439a26e1a987dec39be50d2b3b98d5c2492c7185.

Full raw roots are iterations/hassan-boundary-tokens-20260919/results-j55349 and iterations/hassan-boundary-reset-20260919/results-j55382 under /home/sashawork/dev/amd-runtime-production and /workspace/home/sasha/amd-runtime-production. Each frozen run.py --audit revalidates hashes, controls, numerics, byte-level topology and timing medians. Dispatch profiling is separate from primary timing and timestamps dispatch endpoints only, not independent signal-ready events or wave occupancy. Both experiments remain unqualified.
