# Frozen expert and grouped-KV holdouts — v4 / job 55597

**No large regression versus stock in these 76 cells; a material tradeoff remains versus frontier-off.** V4 on is lower than stock in 63 rows and higher in 13; the largest increase is 1.08%. But balanced four-stream experts are consistently faster with the existing frontier-off path: v4 on adds 4.54% at batch 16 and 10.90% at batch 64. Earlier frontier v1 has essentially the same tradeoff. This is not a new regression from executable ownership, and it is not a universal nonregression result against the best available configuration.

Job 55597 completed 0:0 on node2 / one GPU. Remote and downloaded local audits pass: 48 timing processes, four rotated process rounds, 9,728 retained timing rows, plus six separate path-proof processes. Each process retains eight trials per cell; the reported value is the median of four process medians. Every measured numerical comparison passed. Timing processes have tracing and dispatch timestamps disabled.

The workload binary, CPU references, data shapes, schedules, timing loops, phase coverage and four-round protocol are frozen from the existing suite. Compared modes are stock, earlier v1 frontier, v4 frontier off, and identical v4 bytes with frontier on. No benchmark kernel or dimensions were changed. Expert proof receipts contain all 48 expected frontier launches with completed/recycled generations. Grouped transfer graphs take the existing fallback; their improvements are not caused by the new frontier path.

| Graph replay, GPU µs | Stock | Earlier v1 frontier | v4 off | v4 on | On vs stock | On vs off |
|---|---:|---:|---:|---:|---:|---:|
|b16 balanced / 2 streams|224.788|227.438|222.027|227.208|+1.08%|+2.33%|
|b16 balanced / 4 streams|234.098|154.955|147.805|154.515|-34.00%|+4.54%|
|b64 balanced / 2 streams|111.104|110.534|107.093|111.554|+0.41%|+4.17%|
|b64 balanced / 4 streams|117.053|99.273|89.533|99.293|-15.17%|+10.90%|
|b64 skewed / 2 streams|194.446|195.996|186.826|195.037|+0.30%|+4.39%|
|b64 skewed / 4 streams|194.027|153.985|154.315|152.885|-21.20%|-0.93%|

For batch-64 balanced/four-stream experts, the on/off penalty is 9.66–12.08% across the four rounds, so it should be treated as a real remaining performance issue. This graph is still 15.17% faster than stock. The current v4 on versus earlier v1 contrast ranges from −1.76% to +1.01% across all 76 cells; no large ownership-related loss appears here.

Grouped KV graph totals with one split range from −3.99% to +0.19% versus stock; 22 splits range from −8.76% to −5.65%. Same-byte frontier on/off is within 0.55% for all these graph totals because they use fallback. Some small prefetch cases still lose to their own prefetch-off schedule; this is preserved workload behavior, not evidence that transfer overlap is universally beneficial.

The full 76-cell table, including eager and isolated component cases, is `HOLDOUT-v4-cells.csv`. Raw per-round contrasts, GPU/host/submit measurements and every timing remain in `holdouts-j55597`. This suite covers experts and grouped small-KV transfers; it does not replace the original long-producer waiter, all other stream micros, the unchanged serving application, HiSparse or GLM qualification.

## Decision

Preserve v4 and the faster expert fallback. Continue with a generic boundary/retirement design and capacity safety, using the expert penalty as a holdout to explain and avoid. Do not add tensor-size, kernel-name or benchmark-specific selection rules to hide the conflict. The measured first-pair Q/K skew gives a separate concrete boundary lead, but it has not yet been shown to explain the expert penalty.

## Identity

- Specification SHA256: `5dd6969f95f65b59d0c7924e08f0667e31d7a5561d2f23173fb2862178124c32`.
- Raw manifest SHA256: `a603d5e0a239e4d83038d3ab3fc5540871f56fbdb05aad614a6baf9bb999715e`.
- Frozen workload SHA256: `de0bc5d2fa4d589868a6ed43dd831c461eb54cca8706fad42c3d4003df50e83b`.
- v4 HIP: `b378fec20d524ae611b119bd986095fb0bd1d081be5cf485d2bbae6ce8cec78f`.
- Earlier v1 HIP: `3de08d266bed17cba7a9aa93a217a1724edd50feaadcbdd9429da13ae51aecbe`.
- Both candidates use private HSA `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.

Audit: `python3 holdouts/run.py --audit --spec holdouts-v4-spec.json --out holdouts-j55597`. Runtime/control/rocBLAS hashes, exact source hashes, frozen binary/reference hashes, numerical results and path receipts are checked. The archive stores manifest/summary/table; full raw data remain at the working root and its node2 workspace mirror.
