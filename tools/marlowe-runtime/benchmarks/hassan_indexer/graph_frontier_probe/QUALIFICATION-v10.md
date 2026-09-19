# V10 checkpoint after broad coverage and one fixed repeat

V10 is the new measured best for the unchanged warm Hassan projection graph: **10.207µs per two-stream pair versus stock 14.273µs and matched v7 11.662µs**. The grouped case is **7.208µs versus stock 10.087µs and matched v7 7.344µs**. These gains are from the real HIP runtime with the original kernels, dependencies and streams. Separate dispatch timestamps show greater overlap and lower first-pair skew. No graph splitting or application polling is involved.

The architecture experiment is now checkpointed. It provides a substantial Hassan gain and retains approximately 96% removal of added waiter overhead. It does **not** establish universal microbenchmark neutrality, optimal performance on every graph, or production readiness. The next phase is the requested HiSparse and GLM end-to-end qualification and clean minimal PR, keeping this result available without assuming its serving behavior.

## Completed evidence

All root jobs are terminal. Build 55780, correctness/performance 55788, separate dispatch 55793, affected holdouts 55798, and broader/repeat 55818 completed with their required audits. Full artifacts were downloaded and independently audited locally. Across the uninstrumented performance suites there are 320 timing processes and 64,448 retained timing rows, plus separate structural/numerical correctness checks. The original kernels, workload binaries, shapes, references, schedules and timing loops were unchanged.

Job 55818 repeated exactly the existing four-round expert/KV and attention/waiter protocols once, after the first cohort flagged marginal regressions. The repeat was fixed before results were known. No trial was removed, and the first cohort is not replaced by the repeat.

| Flagged comparison | First cohort 55798 | Repeat 55818 |
|---|---:|---:|
|Skewed batch 64/four-stream expert, versus matched v7|+2.83%|+1.32%|
|Attention eager/wide 256×1024, versus stock|+2.20%|+0.77%|
|Same attention case, versus matched v7|+2.23%|−0.38%|
|Attention eager/serial 256×1024, versus same-byte central|+2.12%|−0.61%|
|Added waiter overhead removed|95.87%|96.05%|

The repeat has no median regression above 2% in its 76 expert/KV or 42 attention cells versus stock, same-byte central, or matched v7. That does not erase the first-cohort losses or justify calling them impossible. The expert case retains a positive median difference versus v7, with variable magnitude; the eager attention cases do not exercise graph-frontier lowering, limiting causal attribution to this policy.

## Remaining tradeoffs

The broader 208-cell gate has no median slowdown above 2% versus same-byte central. It retains three repeatable pipeline losses of 2.61%, 2.95%, 3.44% versus stock, also present with matched v7. One mixed parallel graph is +2.19% versus stock and +0.08% versus v7. Four other mixed cases are 2.24–2.49% slower than v7 but between −0.31% and +0.66% of stock. Their cause is unresolved. See REMAINING-v10.md and the all-cell CSV; no gap investigation or workload tuning was done.

The historical feature-off batch 64 balanced/four-stream expert result (~89.84µs) is still faster than V10 distributed (~97.18µs in the first new cohort). Those are different cohorts, so this is not a matched effect estimate, but it remains an unresolved performance target. The V10 central control keeps frontier lowering enabled and must not be described as feature-off.

The correctness gate covers the ordering regression, exact published-prefix sealing, resource caps, ordinary fallback, callbacks/queries, updates, destruction and kernel ownership. The defective V8 negative control is preserved. Fatal asynchronous device-error quarantine remains source-reviewed, not newly injected. Full serving, HiSparse, GLM, multi-device application behavior and production deployment are not qualified by this microbenchmark work.

## Artifacts and next phase

- RESULTS-v10.md: first matched Hassan and affected holdout cohort, unchanged and retained.
- BOUNDARY-v10.md: architecture, V8 rejection/V9 correction, source identities, separate timestamp evidence.
- REMAINING-v10.md and REMAINING-v10-cells.csv: every broader cell and its limitations.
- boundary-holdouts-repeat-j55818/summary.json and boundary-attention-repeat-j55818/summary.json: complete repeat results, with original manifests and raw logs retained locally and on the cluster.

V10 HIP SHA256 is `857a3d8d714f057cb04bc5025434200eaa5a3c6a31ad8224d94e59d13cd241a2`; HSA is `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`. The default-off distributed policy is archived separately from main PR1 runtime source. The broader manifest is `133262bf2887ca1e429eaa5af8f9e15b38b4b0f1232af4f931a41bc236ce8739`; repeat attention/waiter manifest is `8e3f224be9a91e6b9a03fc0a216f1cb245620dd72bd14ec77b96117804cf7e4a`.

The stream architecture phase stops at this evidence checkpoint, before the September 20 deadline. The overall goal remains active: recover the known HiSparse candidate, remeasure it with the established application protocol, run official GLM 5.2 resident benchmarks without HiSparse, and produce the requested new minimal PR with separate microbenchmarks. No full-model result is inferred from the V10 microbenchmark win.
