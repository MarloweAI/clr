# Minimal fused-entry candidate: correctness — job 52193

**The minimal candidate passes the tested HIP/PyTorch correctness suite. Production qualification remains open.** This build removes the entry experiment controls from the earlier fused51980 implementation. Subsequent [performance evidence](../dispatch_cost/FUSED_RC1_PERFORMANCE.md) retains95.772% waiter-excess removal but fails the original stock screens; this document describes correctness only.

Package: `marlowe-hip-7.2.4-fused-rc1`.

- HIP: `1de1c55a2ea7a70587ee953288488f6baa94e651b247b4ef7cd7104fdfdded04`.
- HSA: `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
- Build base: `cab5670a350678f2b0a6feb388fcbbca56c426a1`.
- Full source patch: `96c517b48a2c286c0340eeb71f8258766afd24e2443dc69efac9a875c07145d8`.

The four-file port retains a launch predecessor through each eligible side-root accumulator and imports it exactly once before its first captured kernel batch. Native admission and ordinary AQL dependencies stay unchanged, with SYSTEM scope on that batch. Cached eligibility restricts fusion to flat captured kernel graphs on the known single device; replay checks the root's current enabled/captured state. Profiling, copy, child, unknown and other unsupported paths keep ordinary entry markers. Partial submission errors retire published work and join actual side tails before graph destruction. Entry modes, observation output, fault injection, CPU polling and vendor-value experiments are absent. Native-wait and placement flags retain their default-off behavior; the graph-ordering repair and eligible dependency integration apply independently.

Codex xhigh source review compared this port against exact51980: differences are limited to the intended fixed-mode2 and diagnostic/lazy-path removal. Ownership and cached-device headers match the previously tested implementation. The reviewed port adds 118 lines and removes 24 across four files. No new replay topology scan or packet mechanism is introduced.

One root-owned node2 allocation, two GPUs available only for the device-boundary fixture; ordinary tests use one GPU. The standalone script built, packaged, waited, and audited through Slurm 0:0. All 120 single-GPU processes and both two-device processes passed; local downloaded artifacts pass the mirrored audit.

| Coverage | Retained rows |
|---|---:|
| PyTorch streams, events and graphs | 2,560 |
| Graph replay, clone, update and lifecycle | 384 |
| Terminal graph completion | 576 |
| Asynchronous launch-entry ordering | 96 |
| Entry transfers | 288 |
| Full-buffer publication | 192 |
| Disabled/re-enabled roots | 144 |
| Two-device cache invalidation/reconstruction | 4 |

Additional process checks cover threaded event/queue reuse, native instruction-pool rotation and fallback, and ordinary event semantics. The four native/placement flag states are exercised with queue caps appropriate to each fixture. These manifests record the five GPU controls but do not explicitly pin or record AMD_DIRECT_DISPATCH; the broad performance bridge will pin it to one. The two-device test verifies that both placement and fused-entry cache eligibility are invalidated by rejected device-changing updates, remain invalid after restoration, and are rebuilt on a new graph executable. The read-only inspector is compiled with this runtime's own host flags and headers; no runtime tracing/export is added.

Fault injection is deliberately absent from these release-shaped bytes. Earlier51980 fault tests and preserved source structure support the error path, but are not presented as an exact-byte injected-failure test. The suite also does not establish arbitrary nested multi-device graph correctness.

The subsequent unchanged broad matrix52217 and bounded confirmation52255 use these exact bytes, immutable51980 and installed-stock controls, including both native/placement flags off. The >=95% waiter target passes and the two-stream stock failure persists. A HiSparse comparison may gather diagnostic evidence under the revised plan; it cannot qualify deployment or erase a failed screen.

Local package: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/marlowe-hip-7.2.4-fused-rc1`. Raw roots: `fused-production-checks-j52193` and `fused-invalidation-j52193` in the same iteration directory, mirrored under `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918`. External audit records are authoritative for completed checks; the immutable package retains its unqualified build manifest.
