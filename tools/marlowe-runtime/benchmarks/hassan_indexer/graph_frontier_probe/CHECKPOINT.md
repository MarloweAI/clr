# Current checkpoint — September 19, 2026

V10 is the measured Hassan best: 10.207µs per original-sized warm two-stream pair, versus matched v7 11.662µs and stock 14.273µs. It retains approximately96% removal of added waiter overhead and has separately measured real dispatch overlap. All architecture experiments and validation jobs are complete; raw artifacts are preserved and locally audited.

Read QUALIFICATION-v10.md for the final checkpoint, including the first and repeated holdout cohorts. The repeat's 118 expert/KV/attention cells have no median slowdown above2% versus stock, matched v7 or same-byte central. The broader gate still has inherited pipeline/mixed losses, and the first cohort's marginal regressions remain in the record. This is not universal neutrality or production qualification.

V8 is rejected; its preserved ordering regression returns51 instead of146. V9/V10 correct the raw-publication bridge and pass the same test plus lifetime/capacity checks. Main PR1 runtime source has not been promoted to these diagnostic builds.

Next is Goal2: recover/remeasure the known HiSparse candidate, validate GLM5.2 resident end-to-end performance without HiSparse, and create a new minimal PR with a separate microbenchmark folder. The overall goal remains active. Full raw artifacts are in the local iteration directory and its cluster mirror; this archive contains frozen patches, harnesses, build identities, summaries and manifests.
