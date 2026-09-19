# Distributed graph completion boundary — v10

This is a default-off architecture experiment for unchanged parallel kernel graphs. V10 improves the unchanged Hassan warm two-stream case to 10.207 µs/pair versus stock 14.273 µs and matched v7 11.662 µs. Affected holdouts mostly preserve performance, with two variable regressions requiring confirmation; see RESULTS-v10.md. No serving, HiSparse or GLM qualification is implied.

## Architecture and tradeoff

V7 represents a completed graph with a private all-lane join on the launch queue. A succeeding graph's side queues wait for that join; an ordinary observer also waits for it before publishing normal fenced completion. This preserves ordering but adds a dependency hop at each graph boundary.

V10 represents the boundary as the final signal on each physical queue that actually received work. On each queue's first use, a compatible successor waits on every foreign predecessor tail and relies on packet order for its own tail. The ordinary public completion bridge consumes the complete tail set and then publishes the existing SYSTEM-fenced completion. Original kernels, dependencies, graph structure, logical streams and queue placement are unchanged. Every previous leaf must still precede every succeeding root; no cross-replay work is allowed to escape stream ordering.

For two queues, this removes the intermediate join hop without reducing the number of wait packets. With more queues, the all-to-all dependency set can cost more, which makes the four-stream expert workload a required check. The tail descriptor is immutable and owned by the deferred command. Strong predecessor/generation/kernel leases, bounded arena capacity, prepublication preparation, exact partial-prefix sealing, and ordinary fallback remain in force. Producer completion has at least AGENT release; public observers retain SYSTEM visibility. This is not polling in application kernels or graph splitting.

## Correctness review and regression fixture

V8 was rejected despite passing its initial nine preflight, six ownership and nine capacity cases. Independent review found that an ordinary captured single-root graph could publish raw AQL before `Command::enqueue` bridged a distributed predecessor. V7's central join had masked that ordering dependency.

V9 factors predecessor materialization into a shared method and calls its distributed-only form under the exact raw-publication execution lock, before publishing ordinary captured packets. Private compatible publication skips that hook. V10 additionally removes construction of an unused central-tail vector in distributed mode. The prebuilt empty-prefix boundary is deliberately retained for failure safety; neither edit changes kernel code or the user's graph.

The new delayed-side-producer -> ordinary-single-root-consumer test exposes V8: `[17,19,51]` instead of `[17,19,146]`. The consumer used the side value before it was written. V8 central mode passes; V9 and V10 distributed mode pass for both choices of delayed branch, with immediate and deferred ordinary kernel retirement. The defective V8 result remains a required negative control, not a passing candidate.

V9 job 55779 and V10 job 55788 pass ten transition processes, nine preflight processes, six ownership processes and nine capacity processes. Local downloaded audits agree with cluster audits. Structural audits additionally verify exact published-prefix tail sets, release scopes, balanced retirement and public bridges: 3,918 launches across 14 V10 logs. The first attempt55775 failed before execution because a fixture macro shadowed the graph-exec variable; its source and compiler log remain preserved. Fatal asynchronous device failure is still source-reviewed, not newly injected here.

## Separate dispatch-interval evidence

Job55793 completed on node 2 with exact V10 bytes, original Hassan Q/K kernels and separate central/distributed processes. Four processes provide 14,808 dispatch records and 612 numerical checks; local/remote audits pass. Kernel pairing follows the verified publication order and frozen graph DOT, not segment storage IDs.

| Diagnostic interval, µs | Central g1 | Distributed g1 | Central g50 | Distributed g50 |
|---|---:|---:|---:|---:|
|First-pair start skew|3.240|1.040|3.280|1.040|
|First-pair combined span|7.841|6.560|7.861|6.681|
|Median overlap, all post-warmup pairs|1.760|5.080|4.280|4.280|
|Between-launch gap, within a timed burst|3.400|3.200|4.021|3.181|
|Later-pair start skew|—|—|-0.120|-0.120|

All 1,600 post-warmup pairs in each case overlap. In g1, median Q/K dispatch durations increase from 5.00/4.60 to 6.16/5.521 µs as overlap increases, while their combined span shrinks. This is consistent with overlap exposing shared-resource contention; it is not a resource-counter attribution. Later pairs in the grouped graph are essentially unchanged, localizing the observed scheduling improvement to the boundary. Packet placement and scheduling also change, so the numbers do not isolate a single firmware instruction or prove a firmware defect.

These are profiling dispatch intervals, not active-wave occupancy or pure firmware wait time. Timestamp collection is disabled in all performance runs; none of these instrumented latency values qualifies a candidate.

## Identity and reproduction

V10 HIP SHA256: `857a3d8d714f057cb04bc5025434200eaa5a3c6a31ad8224d94e59d13cd241a2`.
HSA SHA256: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
Candidate patch: `40c710a9d0e8a3f79a1be54032a73974059fa5ff7f25d568146d8d9326bca5de`.
Full patch: `18c329c857e2c01048d1fb627abe77f9a06aebc933f4b5d834c9d9246a07f94e`.
Source manifest: `1135a217619ad639ffaf0800bcdbf34d12046b1f67c6e6d0994c0d652ba5e0ca`.
Timestamp manifest: `b99712460fae4cef1318eabb00ed149bd3b3820a046cacdfa8068245829e12ce`.

Use `boundary_transition_v10.py`, `preflight_boundary_v8.py`, `ownership_boundary_v8.py`, `capacity_boundary_v8.py` with `--audit --out` for their job 55788 roots. Use `timestamps_boundary.py --audit --out timestamps-j55793` for the interval evidence. Build/source manifests and complete raw artifacts are preserved locally in this iteration directory and its `/workspace/home/sasha` cluster mirror. PR1 archives the experiment separately from its main runtime implementation.
