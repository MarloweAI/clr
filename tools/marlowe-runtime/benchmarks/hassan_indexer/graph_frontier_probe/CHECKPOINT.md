# Current checkpoint — September 19, 2026

V10 is the new measured Hassan best: 10.207µs per original-sized warm two-stream pair, versus matched v7 11.662µs and stock 14.273µs. It retains 95.87% removal of added waiter overhead. See RESULTS-v10.md and BOUNDARY-v10.md for the matched four-mode timings, separate overlap evidence, and correctness qualification.

All 76 expert/KV cells are within 1% of stock or improve. One attention cell loses 2.2% to stock, and one skewed expert cell loses 2.8% to matched v7 with substantial round variation. A fresh unchanged-suite repeat and the remaining 208-cell gate are running; V10 is not fully qualified. The historical feature-off expert best remains a separate unresolved comparison. Earlier V7 expanded coverage found four stock regressions of 2.66–3.51%, also present with v4 (REMAINING-v7.md).

V8 is rejected: it allowed an ordinary single-root consumer to precede a distributed side tail. The preserved test returns 51 rather than 146. V9/V10 bridge before raw publication and pass that regression and the existing lifetime/capacity tests. Main PR1 runtime sources have not been promoted to these diagnostic builds.

Complete raw artifacts remain in `/home/sashawork/dev/amd-runtime-production/iterations/hassan-graph-frontier-20260919` and its `/workspace/home/sasha` cluster mirror. This archive contains frozen source patches, harnesses, build identities, summaries and manifests, without duplicating all raw binaries and process maps. Goal2 HiSparse/GLM qualification and a new minimal PR remain pending.
