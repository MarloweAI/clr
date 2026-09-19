# Per-stream retirement sharing — job 53285

Sharing completion bookkeeping within each logical stream reduces host submission cost but does not fix the remaining GPU regressions. The original benchmark kernels, inputs, stream assignment and timing protocols are unchanged. This candidate is diagnostic; the production runtime in PR1 is unchanged.

Node2 job53285 completed0:0. HIP SHA256 `57c5f40acd76cb4210cb123393031f7452c754500c75cff644caa34de652d19b`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Immutable parent HIP `862f3cd7eded1e9cd4f4f2037f83de0871a36c27afca3c880b9d658a5c895473`. Same-byte diagnostic off/on comparisons separate the intervention from the parent-to-rebuild bridge. All trials retained.

| Original graph workload | Stock GPU us | Rebuilt off | Parallel retirement sharing | Additional one-stream/shared setting |
| --- | ---: | ---: | ---: | ---: |
| Experts b64 balanced, 2 streams | 110.8635 | 115.1335 | 114.9940 | Not retested here |
| Experts b64 balanced, 4 streams | 117.134 | 99.753 | 100.714 | Not retested here |
| Hassan Q/K | 19.8427 | 22.0984 | 22.0872 | 19.1185 |

For the balanced two-stream expert, sharing reduces host submission9.8325→8.9775us (8.70%), while GPU time changes−0.12%. Its3.73% loss to stock remains in all four process rounds. This is a useful CPU-path improvement, not a device-gap explanation or an allocator-only measurement. Four-stream gains remain. Grouped-KV split1 stays near stock and split22 remains6.2–9.3% faster; copy graphs fall back, so those gains are not attributable to the new sharing path.

Hassan retains two regions for two parallel segments, so sharing is effectively neutral there:22.0984→22.0872us. Parallel execution remains11.31% slower than stock. The explicitly selected one-stream/shared specialization reaches19.1185us,3.65% faster than stock (all10 process rounds improve); host submission falls45.93%. This is not a general policy: prior job53134 showed unconditional serialization regresses useful parallel expert workloads45–75%.

The candidate keeps each cross-stream exported completion at its original boundary and merges only unexported boundaries on the same logical stream. Expert graphs use3→2 or5→4 retirement regions. Every entry import, interior dependency marker, batch publication boundary and final side-tail join stays in place. Per-replay planning cost is included. Profiling/async/unsupported paths fall back.

Correctness and identity audits pass remotely and locally:54 existing fixture processes/1,404 reference rows;12 old-export/new-region lifetime and injected-prefix-failure processes/57 rows;3 two-GPU device/setter-invalidation processes/42 rows. The new lifetime fixture destroys graphs before completion and includes disabled roots, updates, stream changes and a slow side prefix. Failure injection is after a published segment, not inside packet publication. Two GPUs were allocated for invalidation; performance uses GPU0 only.

The unchanged expert/grouped holdout protocol passes48 timing processes/9,728 rows/76 cells plus6 structural proofs. Hassan passes50 processes/800 timing rows/1,000 correctness checks in10 balanced carryover orders, plus3 separate topology proofs. Original four-kernel Hassan graph and200-replay protocol remain unchanged.

Next bounded intervention: omit a final side-tail wait only when the actual last side segment is already a transitive dependency of the actual last launch-stream segment. Keep unconsumed tails, independent Hassan roots and every error-prefix join. This has not yet been measured. Choosing between one-stream and parallel plans remains unresolved. PyTorch, waiter-overhead and HiSparse qualifications belong to their previously tested bytes and do not transfer to this candidate.

Raw and immutable source: `iterations/hassan-qk-micro-20260918/lane-retire-j53285`, `lane-retire-source.json`, `lane-retire-full.patch`, `lane-retire-harness.json`. Whole-run local audit: `lane-retire-j53285/local-final-audit.json`.
