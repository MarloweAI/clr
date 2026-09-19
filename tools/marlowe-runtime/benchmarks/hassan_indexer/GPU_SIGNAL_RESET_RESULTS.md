# GPU-reset total replay cost — job 55130

**GPU-local internal signals remain 24.37% faster than matched host-page signals after including GPU reset, its ordered waits, packet publication and host-visible completion.** This removes the expensive per-signal CPU preparation from the timed path of job55065. It establishes lower-layer feasibility, not a qualified HIP/PyTorch runtime or a matched win against serial execution.

Job55130 completed 0:0 on node2, one GPU. Remote and local strict audits pass all231 timing rows and3528 numerical checks. The main workload uses original Q/K packets,200 pairs, four rotated rounds and eight retained trials per cell; seven short-pilot rows are correctness/capability checks only. No production workload ran.

| Storage and reset | Total µs/pair, profiling off | Change vs matched host-page control |
|---|---:|---:|
| Normal pooled host signals, CPU reset |9.677203|—|
| Private host pages, GPU reset |9.721553|reference|
| Private GPU-local pages, same GPU reset |**7.352654**|**−24.367%**|

Local storage saves2.368899µs/pair against matched host pages, and24.021% against the normal pooled control. Each of the four rounds improves24.25–24.58%. Every32 local primary trials (7.332–7.385µs/pair) is faster than every matched host trial (9.679–9.791). All trials are retained. Table values are medians of the four round medians.

The matched comparison uses the same private signal implementation, GPU reset kernel, packet topology and lifecycle. Storage addresses/backing and the resulting memory path differ. The pooled row uses ordinary signals in the same rebuilt ROCr; it is not the installed stock binary and differs in reset method/packet count. The ordinary HIP reference is10.356690µs/pair with a different submission boundary; it is not the causal denominator. Historical serial numbers around8.8µs/pair are not a matched comparison.

## Timed path and verification

The CPU timer starts before ordinary control-signal resets and packet publication. Both lanes are published behind the common gate, which is immediately released; the old deliberate200µs hold is removed. Queue0 executes one GPU scatter reset, with SYSTEM acquire/release. Both lanes wait on its ordinary host-visible completion with ordered SYSTEM-acquire AND packets before original Q/K work begins. Timing ends after both ordinary host-visible final exits complete. Initial allocations/capture and post-drain numerical/guard inspection are outside replay timing.

The helper writes only existing real signal value/start/end timestamp fields, leaving ownership metadata intact. Eager and captured untimed poison/reset fixtures verify1/0/0 and guards. The immutable device pointer table, helper module, graph and kernargs stay alive. Both final exits and queue read indices retire before internal values are read, profiled, reused or destroyed. Every400 distinct completion values finishes at zero. Exact original kernels, shapes, data, arguments, ordered bits, AGENT fences and398 internal ANDs remain unchanged. GPU-reset lanes have403/402 packets; the pooled control has401/401. Queue wrap occurs39 times. Mapped HIP/HSA/helper identities and source/data hashes pass.

Separate profiling-on runs show the previous-pair-end to both-next-start interval remains5.16→2.56µs for matched host/local storage. All reset endpoints precede first Q/K dispatch endpoints. These are packet envelopes, not independent signal-ready timestamps or wave-occupancy proof. Profiling is excluded from primary numbers.

## Remaining limits and next decision

One reset is amortized over200 direct-replayed pairs. The ordinary HIP reference launches a50-pair captured graph four times, whereas this lower-layer test publishes one200-pair batch. Runtime integration must measure the real per-graph reset/submission boundary; the current result does not establish that cost. The two-pair pilot also shows visible fixed helper overhead: its single profiling-off local sample is25.605µs/pair versus14.635 pooled. Those seven pilot samples cannot estimate small-graph performance or justify a threshold, but prohibit claiming universal nonregression.

The next candidate must integrate a separate GraphExec-owned GPU dependency-token channel with a generation per in-flight launch. Generic HwQueueTracker signals cannot move: host wait/query, profiling, callbacks and retirement use them. Internal local handles must bypass ExternalSignal/WaitingSignal/native admission, which CPU-load signals, and feed narrow ordered AND emission directly. Preserve ordinary per-lane/final retirement, generation ownership through all joins, update/enable changes and partial-publication failure drainage. Captured packet templates must not be mutated across in-flight generations. No per-launch host synchronization, shape-specific eligibility or application change should hide these costs.

After integration, compare unchanged serial/two-stream HIP/PyTorch replay in one matched run, including short and grouped graphs. A useful runtime win is required before broader microbenchmark holdouts. This test supports that implementation step; it does not promote a runtime package.

## Provenance

- Frozen source manifest SHA256: `d4e12fe99e1464c8ac8568a2160c9af252cb64684c440d851a86e40d4a6a0a01`.
- Raw result manifest SHA256: `b97819bc947c4f454e5a8546ced66ba0a1eb67291efe4cb727447a76e53bb011`.
- Unchanged HIP: `0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4`.
- Unchanged private HSA from job55065: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.

Task directory `/home/sashawork/dev/amd-runtime-production/iterations/hassan-gpu-signal-reset-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Raw directory `results-j55130`; `python3 run.py --out results-j55130 --audit` revalidates. Frozen sources/receipts are in `gpu_signal_reset_probe/`; private ROCr patch/build provenance remains in `signal_locality_probe/`. `TOTAL_COST_CHECK.json` retains independent derived comparisons. Existing Codex xhigh prelaunch review found no correctness/lifetime/timing blocker; independent post-run raw/source audit also passes. Every matched primary trial favors local storage; the reviewer confirmed the different direct-batch versus HIP launch boundaries and the absence of tiny-graph qualification.
