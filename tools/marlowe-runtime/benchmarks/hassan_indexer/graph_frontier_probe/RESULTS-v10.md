# Measured graph-frontier checkpoint — v10

Update: the broad gate and fixed repeat are complete. QUALIFICATION-v10.md reports the final checkpoint; this document retains the first cohort.

**V10 is the new measured Hassan best:** unchanged warm two-stream Q/K drops from matched v7 11.662377 µs to 10.207079 µs per pair, versus stock 14.272910 µs. That is 12.48 % faster than v7 and 28.49 % faster than stock. Same-byte central/distributed comparison isolates a 12.48 % improvement. Qualification remains incomplete because of the holdout caveats below and pending broader coverage.

| GPU µs/pair | Stock | Matched previous v7 | V10 central | V10 distributed | Distributed / stock |
|---|---:|---:|---:|---:|---:|
|serial-g1|13.443586|12.555456|12.646458|12.525052|-6.83 %|
|events-g1|14.272910|11.662377|11.662825|10.207079|-28.49 %|
|serial-g50|8.836786|8.796035|8.778549|8.794180|-0.48 %|
|events-g50|10.087479|7.343787|7.293135|7.208032|-28.54 %|

Job55788: node 2, one GPU, four rotated rounds, 64 timing processes, 12 separate proof processes, 512 timing samples and 11,628 numerical comparisons. Exact mapped HIP/HSA, workload/dispatch/source hashes, graph node counts, changed-input correctness and control receipts pass both cluster and downloaded local audits. Original benchmark.py, kernels, shapes, graph dependencies, scheduler and timing loops are unchanged. The grouped graph contains 50 pairs and is synthetic; g1 retains the original projection-pair size. This is a warm graph-only extraction, not full serving or model validation.

For g1 the same-byte GPU improvement repeats in all four rounds (10.44–13.97 %); versus stock the range is 26.40–29.38 %. Host elapsed is 10.286426 µs and submission 2.442639 µs per pair. G50 is 1.17 % faster than same-byte central and 1.85 % faster than matched v7; its GPU improvement repeats in every round. Both timestamp and runtime trace collection are disabled in these performance processes. Serial graphs use ordinary fallback; their small central/distributed differences are not evidence for this new graph path.

Separate dispatch intervals (job 55793, BOUNDARY-v10.md) reduce first-pair skew 3.24→1.04 µs and increase overlap while leaving later grouped pairs essentially unchanged. This supports the boundary-dependency hypothesis, with no firmware-bug attribution.

## Affected holdouts

Job55798: exact historical expert/KV binary and references, plus byte-identical original attention/waiter sources; four rotated rounds. Expert/KV:48 timing processes, 6 proof processes, 9,728 timing rows. Attention/waiter:32 timing processes,7,296 timing rows. Local/remote audits pass; all trials retained.

| Suite | Cells | Faster than stock | Largest stock slowdown | Largest slowdown versus matched v7 |
|---|---:|---:|---:|---:|
|Expert and small-transfer KV|76|65|0.989 %|2.826 %|
|Attention dispatch|42|29|2.201 %|2.234 %|

Expert/KV has no median regression over2 % versus stock or same-byte central. The batch64 balanced/four-stream graph improves 98.933→97.183 µs versus same-byte central, compared with stock 116.774 µs. It has not demonstrated parity with the historical feature-off result (~89.84 µs in another cohort); frontier-off is a different control from the central boundary. Do not silently treat central as feature-off. Grouped KV uses ordinary fallback, so its stock gains are not causal evidence for distributed boundaries.

The skewed four-stream expert graph is 154.645 µs versus matched v7 150.395 µs (+2.83 %), though same-byte central is155.395 µs. Its paired v7 contrasts are−0.17 %,−0.60 %,+5.51 %,+6.23 %; this is an unresolved comparison, not a proven distributed-toggle regression. All six eligible multi-stream expert graphs improve versus same-byte central at the median.

Attention eager/wide 256×1024 is 184.846 µs versus stock 180.866 µs (+2.20 %) and matched v7 180.806 µs (+2.23 %). Eager/serial at the same size is+2.12 % versus same-byte central but+0.97 % versus stock. These eager cases do not exercise graph-frontier lowering; that limits causal attribution, but does not erase the measured losses. The short parallel graph improves 71.552→70.061 µs versus central and71.852 µs versus v7.

| Original 2,048-kernel waiter, GPU µs | Stock | Matched v7 | V10 central | V10 distributed |
|---|---:|---:|---:|---:|
|alone|3164.719|3155.564|3160.760|3168.467|
|pending_wait|5248.670|3242.889|3244.228|3254.461|
|ready_wait|3165.028|3156.345|3161.194|3168.365|

Added waiter overhead is 2083.951 µs on stock and 85.994 µs on V10 distributed: **95.8735 % removal of the added overhead**, with total pending-wait time down 38.0 %. This native-event improvement is retained in both V10 modes; it is not caused by the new distributed graph flag.

## Qualification and next checkpoint

The V10 ordering fix and resource/lifetime suite pass; V8 remains disqualified. See BOUNDARY-v10.md and the retained negative-control output. No production claims follow from these tests.

The unchanged-suite follow-up completed the remaining 208-cell gate and repeated the expert/attention suites; see QUALIFICATION-v10.md. Earlier V7 expanded coverage found three pipeline and one mixed stock losses of 2.66–3.51 %, also present in matched v4; the new V10 coverage is reported in REMAINING-v10.md. Both cohorts are reported separately and retained.

Goal 1 still requires a final broad checkpoint. Goal 2 remains pending: recover/remeasure the best HiSparse runtime, validate GLM 5.2 resident e2e without HiSparse, and create a new clean minimal PR with a separate microbenchmark folder. No new full-model job has run.

## Reproduction identity

V10 HIP 857a3d8d714f057cb04bc5025434200eaa5a3c6a31ad8224d94e59d13cd241a2; HSA 2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12. Exact build/patch hashes are in BOUNDARY-v10.md. Hassan manifest bdcf32cc8fd8ba4435e5f032f2bb50402e2b452e7d7e4420ec4f210c434d22f9; attention/waiter manifest b82d56e62f0f9a7e1b908df50b1faf9e73b222487b431bb7ceb5238f57392d02.

Audit `python3 run_boundary.py --audit --out boundary-results-j55788`, `python3 holdouts-boundary/run.py --spec holdouts-boundary-spec.json --audit --out boundary-holdouts-j55798`, and `python3 attention-waiter-boundary/run.py --audit --out boundary-attention-j55798`. Full raw artifacts are retained locally and in the cluster mirror. V10-affected-cells.csv includes every holdout cell, not just selected wins.
