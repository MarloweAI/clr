# Private graph-completion chaining — job 55418

**There is now useful original-sized architectural headroom: same-object GPU-local completion chaining reduces packet-replay time from 14.994 to 11.732 µs per pair (21.75%).** This is an uninterrupted-batch feasibility result, not a new HIP/PyTorch runtime or a production win.

Job 55418 completed 0:0 on node2 with one GPU. The frozen source passed independent review; strict remote/local audits pass all 576 timing trials and 4,590 numerical checks. All trials are retained. Original Q/K kernel code, shapes, arguments, resources, dependencies and each graph's full join are unchanged. Both arms use the previously reviewed fence placement and cached signal reset.

| Graph | Private host, explicit entry | Private host, chained | GPU local, explicit entry | GPU local, chained |
|---|---:|---:|---:|---:|
| Original-sized one pair |20.334929|17.240805|14.993754|**11.732014**|
| Synthetic 50 pairs |9.850878|9.804364|7.281854|**7.230813**|

Profile-off CPU wall µs per pair includes reset, publication, last host completion and both queue drains. Four rotated/reversed round medians, eight trials each, 200 pairs per trial. The original-sized local gain repeats in every paired round (21.68–21.85%). The grouped local change is −0.70%; the synthetic win is preserved at this lower layer. Host-storage short improves 15.22%.

## What changed and what it proves

Every nonlast graph still ends in an ordered AGENT-acquire/SYSTEM-release join of its actual Q and K completions. That join now completes the private entry token for the next graph. The main queue's next ordered kernel follows this join directly; the side queue waits that token before its next first kernel. The first graph keeps its initial entry. The last graph still has ordinary host-visible completion. Main queue packet count falls from 600 to 401 for g1 (404 to 401 for g50), while side stays 400. The same private tokens are used exactly once and the same host-final array is reset in both arms.

This combines removal of redundant entry packets, changed completion placement and deferred host retirement; it does not isolate one component. Both next branches still wait for the prior graph's join and SYSTEM release. All private tokens finish at zero. In the chained arm only the final ordinary host signal becomes zero; unused nonlast host finals remain one and are explicitly verified. Last-F completion plus both queue read indices covers every consumer before any reuse. Exact byte audit checks each dependency, header and completion handle, packet count and same-object arena identity.

The current experimental HIP reference in this job is 16.753099 GPU-event /16.792530 host µs per pair at g1 and 7.444845/7.482690 at g50. These use different submission and retirement boundaries. Earlier matched actual-HIP studies put short stock around 14.1 and serial around 13.5; those are historical context, not fresh controls. The new result provides enough headroom to design an actual runtime implementation, but no stock, serial or PyTorch win is yet established by this probe.

Profiled short Q/K dispatch intervals overlap by a median 1.84 µs in the local chained arm versus 1.56 in its explicit-entry control; the grouped interval overlap is about 4.36 µs. These are dispatch-interval intersections, not measurements of active waves or independent signal-ready timestamps. The short pair still starts asymmetrically, so this is not maximum hardware utilization. Primary performance results have profiling disabled.

## Runtime qualification boundary

The probe preserves execution and memory semantics for an uninterrupted batch with no intermediate public observation. It does not independently preserve each launch's observable retirement. A runtime port must retain a distinct private completion and owner lease per launch, and materialize an ordinary completion at the precise boundary required by queries/synchronization, events, callbacks, other stream work, cross-stream/agent/SDMA use, resource lifetime operations, capacity pressure or failure. Concurrent host calls must serialize with chain extension. No future-launch prediction or application modification is allowed.

[The integration design](GRAPH_FRONTIER_DESIGN.md) maps this to existing CLR command batching and lists the unresolved ownership/notification hooks and required fixtures. The current implementation still retires every logical lane and final marker, so simply enabling its short fallback or changing a flag cannot reproduce the new probe. No new runtime bytes were built or promoted here. Broader microbenchmarks and full-model tests wait for a real candidate.

## Provenance

HIP `69f3df4efac18f3429ddc5951bdeb2d0dd821f8f1489bb78fb90e2f6dc8da254`; private HSA `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`. Source manifest `3bd4fd993677ab63be36a8e9d8ea0e0cc84337852c5aa4dc2d5d737471dd403b`; raw manifest `f357ab57d703544c4f5b47d87a9163762031996414c60d84f528d3702f375ba0`.

Raw root `/home/sashawork/dev/amd-runtime-production/iterations/hassan-boundary-chain-20260919/results-j55418`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Frozen `run.py --audit` verifies manifest/source/helper/library hashes, exact packets and control values, changed-input/poison-output correctness, signal-state assertions, guards, queue wraps, profile uniqueness and all timing medians. `PERFORMANCE_CHECK.json` records paired-round contrasts and explicitly labeled dispatch-interval overlap. This remains `qualified=false`.
