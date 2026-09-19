# Graph boundary fence placement — job 55399

**Moving required fences reduces the original-sized graph's packet-replay time by 13.92%, from 17.460 to 15.029 µs per pair with GPU-local signals. It is still not a qualified runtime or a demonstrated stock win.** The synthetic grouped case improves 0.75%.

Job55399 completed0:0 on node2, one GPU. Independent source review passed before freeze; strict remote/local audits pass all576 timing trials and4590 numerical rows. All planned trials are retained. The comparison uses exact same-object private host/local signals, cached-pointer reset in all arms, the original Q/K code/resources/arguments and the same dependency and packet topology.

| Graph | Private host, conservative | Private host, moved fences | GPU local, conservative | GPU local, moved fences |
|---|---:|---:|---:|---:|
| Original-sized one pair |26.423794|20.382254|17.459579|**15.029113**|
| Synthetic50pairs |9.905389|9.774678|7.312151|**7.257040**|

Profile-off CPU wall µs/pair includes resets, publication, final completion and both queue drains. Four round medians of eight trials,200pairs per trial. The local short improvement repeats in every round. Host-storage short improves22.86%. The repeated short-graph fork/final boundaries are therefore a measurable cost; reducing them helps without changing computation.

The separate actual HIP reference is16.725692/7.419439 GPU-event µs/pair and16.769330/7.457288 host µs/pair for g1/g50. The packet prototype beats this experimental short HIP reference, but its submission, retirement and timing boundaries differ. Previous matched actual-HIP experiments put stock near14.1 and serial near13.5 for g1. They are historical context, not a fresh matched denominator. This probe therefore does not prove a stock or serial win and does not justify simply porting its changes.

## Scope and correctness

Both entry packets change to NONE/NONE; each lane's first kernel changes from AGENT acquire to SYSTEM acquire and retains AGENT release. The final join changes only its acquisition from SYSTEM to AGENT, retaining SYSTEM release and ordinary host completion. All packet barrier bits, counts, actual dependency signals, final side join and later kernels are unchanged. Exact64-byte audit checks each permissible header difference, every dependency and completion handle, and CSV equality proves paired arms share the same signal objects.

This proof applies to the audited same-agent compute-only DAG with resolved launch predecessor and ordered first kernels. First kernels import prior SYSTEM releases; the final join waits both branches' original AGENT releases and publishes their stores to SYSTEM before host completion. It is not a generic weakening for SDMA, cross-device or host nodes. See [review](boundary_fences_probe/REVIEW.md) and [design](boundary_fences_probe/DESIGN.md).

Changed/restored inputs, poisoned outputs, exact private-token and final-signal completions, guard words, unchanged kernargs, queue wrap, mapped libraries and source/helper hashes pass. Primary timings have profiling disabled. Profiled dispatch-end to next-start intervals shrink for g1, but do not independently measure signal readiness or CP wakeup; no firmware mechanism is uniquely identified.

## Decision and provenance

Keep this as an explained partial improvement. The final bounded architecture question is whether using a graph's GPU-local final token directly as the next graph's entry, with deferred CPU retirement, can remove the remaining repeated boundary work. That requires a dependency/visibility proof before a packet test and an actual HIP lifetime/query/callback design before any port. No new full-model job or production package was created.

HIP69f3df4efac18f3429ddc5951bdeb2d0dd821f8f1489bb78fb90e2f6dc8da254; private HSA2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12. Source manifest66967ed0faacd247a0936c86026bb14221cec574357059f9eb0056e1f5a68cdb. Raw manifestd3b200fc521906ef06453841e7fffdcd3423fdfc3ccc5dd3e76db8435c95c7ba.

Full raw root /home/sashawork/dev/amd-runtime-production/iterations/hassan-boundary-fences-20260919/results-j55399; remote mirror replaces /home/sashawork/dev with /workspace/home/sasha. Frozen run.py --audit revalidates raw hashes, controls, packets, numerics, profile-record uniqueness and all medians. PERFORMANCE_CHECK.json records paired-round contrasts. Independent review was prelaunch source review; root performed post-run raw audit, not an independent reviewer. Diagnostic only; qualified=false.
