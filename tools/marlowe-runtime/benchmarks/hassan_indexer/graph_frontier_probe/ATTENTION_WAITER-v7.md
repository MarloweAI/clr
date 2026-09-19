# Original waiter and attention-dispatch checkpoint — v7, job 55712

The unchanged original 2,048-kernel waiter retains **95.875% removal of waiter-induced excess time**. The 42 existing attention-dispatch cells have no median slowdown over 2% versus stock or the matched previous v4 candidate. Three parallel graph cells remain slower than v7 feature-off; this is also present with v4.

Job 55712 completed 0:0 on node 2, one GPU. Remote and downloaded local audits pass: 32 timing processes, four rotated rounds, 7,296 retained timing rows. The attention_dispatch.cpp and minimal_wait.cpp sources were copied byte-for-byte from the historical frozen suite and checked against its hashes. No kernel, shape, schedule, loop count or CPU-reference logic was changed. The new wrapper only selects the four runtime modes and audits their receipts/results. Runtime tracing is disabled; the original attention workload's built-in span recording remains unchanged.

| Waiter case, GPU µs | Stock | Matched v4 on | v7 off | v7 on |
|---|---:|---:|---:|---:|
|alone|3170.798|3165.935|3158.526|3158.877|
|pending_wait|5247.245|3251.061|3244.289|3244.521|
|ready_wait|3170.689|3165.557|3158.939|3159.425|

Stock excess is 2076.447 µs; v7-on excess is 85.644 µs. Removal is `1 - (v7_pending - v7_alone)/(stock_pending - stock_alone)`. This is removal of the added waiter overhead, not a 95.875% reduction in total producer execution time. Total pending-wait time falls 38.17%. V7 off retains native event waits and disables only the graph-frontier/local-signal pair, so similar waiter performance in off/on is expected.

Attention-dispatch: 34/42 medians improve over stock; range −7.096% to +1.020%. Against matched v4, range −0.461% to +1.632%. These are median gates; individual rounds vary more (for example, an eager-wide cell has one +5.08% round versus stock). All rounds remain in the results.

| Parallel graph case | Stock µs | Matched v4 on | v7 off | v7 on | v7 on/off |
|---|---:|---:|---:|---:|---:|
|256/1024/1/graph/parallel|214.407|205.787|203.156|207.497|+2.14%|
|256/256/1/graph/parallel|77.512|72.122|67.482|72.012|+6.71%|
|256/256/4/graph/parallel|196.645|191.585|187.094|191.605|+2.41%|

The three regressions correspond to about 4.3–4.5 µs of extra graph time. The 16-launch short-attention case also shows approximately 4.0 µs (+0.64%). This near-constant difference across varying kernel work is a clue for a boundary cost, not proof of its mechanism. Current source publishes a private all-lane final join, then the ordinary observer bridge waits on that private join before issuing ordinary fenced completion. The distributed-tail design would let the bridge consume the full tail set directly, removing that intermediate private join. This offers a testable connection between Hassan's cross-launch entry skew and ordinary graph-observer overhead. Preserve full dependencies and release scopes; do not use a workload-specific threshold.

The benchmark suite does not prove every frontier path was exercised: this is a performance/numerical regression gate with exact mapped libraries and control receipts. Separate untimed structural proofs belong to the candidate experiment. Queued chains/fanout, attention-fetch, pipeline and mixed-workload gates remain pending. No model qualification is implied.

Identity: HIP e692e09467765565866387bd4918468b1cbb43459c7c2c3fd2b1242031713ff0; HSA 2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12. Manifest SHA256: 4ed2a020685260f1c13f790ba914345effeeb8785246e1280b59c18edd846841. Sources, modes and hashes are frozen in attention-waiter-v7/spec.json. Audit with `python3 attention-waiter-v7/run.py --audit --out attention-waiter-j55712`; full raw data are preserved in the local iteration directory and the corresponding cluster mirror. The archived summary includes every cell and every round median.
