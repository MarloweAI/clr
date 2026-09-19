# V3 prelaunch source review

Existing Codex xhigh reviewer same_queue_pilot_review: no remaining correctness blocker. Source manifest9a208150aef0a181a7aeda414da398418c978095ee809449849daa6aa657df83, candidate patchaa2d1eecff3a368f0b9e2a22ec917f4a91f17f18b0b39e87e99b5a5536c7eb6e.

Verified separate launch/pool locks, callback-before-status handling, per-logical-stream retirement, explicit reset SYSTEM/SYSTEM, at least AGENT producer/consumer scopes, direct raw ANDs with native history break, no local handle in queue-idle CPU tracking, retained reset frontier, complete final joins and partial-prefix drainage. Eligibility is rechecked with the actual segment assignment. No internal cross-physical edge means the token path performs no useful work, so it falls back; this is structural, not a workload threshold.

The reviewer caught a missing format-string argument in the v2 diagnostic packet receipt; fixed before any GPU test. V1 failed CPU compilation on a const qualifier, v2 built but will not be GPU tested. V3 includes both fixes. GPU timing proceeds only after strict correctness/lifecycle and path validation gates; real per-graph timing and CPU preparation remain unproven.

## Post-run independent xhigh audit

The independent graph_local_result_review recomputed all hashes and two-stage medians, verified the complete 64-cell/512-trial matrix with no extra unmanifested timing directories, and reproduced all four grouped host/local and stock comparisons. No receipt failure was found. The short regression is present in every round and its proofs never take the new path.

The key evidence boundary is explicit: original kernels/configs/inputs/scheduler remain fixed, but this warm graph-only harness differs from the canonical reproducer and its 50-pair graph is synthetic. The grouped win is not an unchanged-serving-graph claim. Timed path execution is inferred from matched untimed proofs, with trace disabled during timing. Native-wait/minimal-parent controls are a supported next test, including a same-byte path-off/minimal arm and physical-queue/spare receipts. No qualification or full-model claim.

Private HSA is copied, not built by runtime-build-v3.json commands. Its exact source/build provenance is retained in the sibling signal-locality experiment and existing PR checkpoint; the v3 receipt hash-binds its unchanged library bytes. This preserves the same-binary causal comparison without implying that the v3 build recipe alone rebuilds HSA.
