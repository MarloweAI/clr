# Correctness-only stock baseline — job 52166

**The residual two-stream loss is reproduced by the two graph correctness repairs alone.** Fresh repaired stock is 4.520% slower than fresh vanilla stock on the two-stream expert target; fused51980 is 0.243% faster than repaired stock. Across all 172 tested expert/KV cells, fused has no >2% GPU or host elapsed-time loss versus repaired stock. It still loses 3.441% GPU time to installed stock on the two-stream target, so the original stock screen remains failed. These results measure repair effects; they do not establish an unavoidable latency floor.

One root-owned node2 GPU, standalone launch/wait/audit; retry52166 completed Slurm 0:0. The initial52159 attempt stopped before compilation because the remote checkout lacked the stock commit; its failed checkout/log and frozen spec are retained. An exact stock commit/tree/blob pack, preserving the original shallow boundary, passed checkout and patch preflight before retry. No timing/protocol settings changed.

Two fresh builds share the same recipe: vanilla `fe5035afc8713dfc6adedd3c00c4306c93a160f8`, and that exact source plus only the source hunks of `b36e37b` (actual-tail completion) and `d862ffe` (launch-entry fork). Independent review reconstructed the resulting file byte-for-byte: `hip_graph_internal.cpp`, 36 added/28 removed lines, SHA256 `017ae6262ba3969ff5bea69f71ef8aef7ea4ee8a085d13520d6f0636af739c64`. No native-wait, spare-queue, placement, fusion or signal-metadata changes were inherited.

| Runtime | HIP SHA256 |
|---|---|
| installed | `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac` |
| fused | `bf7ab37233fce87f88e00020c3538791d02ed549081d54274921487a654659e1` |
| vanilla | `e2331511d322c6c6aed0fb98197a5703319ca4393d84329dccdcbf025ea9115c` |
| repaired | `4f1d72c5388340ecfba70b6c48002c78591968566f31bc6ae6f92be1a173bc95` |

Every runtime maps HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Installed and freshly built stock explicitly reproduce asynchronous entry-order failures in the unchanged51635 probe; all synchronized controls report45/45 increments. Repaired stock and fused pass all36 positive processes: six fixtures at queue caps1/4/8, including entry ordering, tails/lifecycle, terminal completion, transfers, publication and disabled roots. All negative rows are retained; these runtimes are comparison baselines, not qualified implementations.

| Target, graph total | Installed stock µs | Fresh vanilla µs | Repaired stock µs | Fused µs | Repair/vanilla | Fused/repaired | Fused/installed |
|---|---:|---:|---:|---:|---:|---:|---:|
| h32-miss256-r1152 / gather-parallel | 689.703 | 690.042 | 707.583 | 699.782 | +2.542% | -1.102% | +1.461% |
| b16-balanced / 4_streams | 233.378 | 233.488 | 252.969 | 158.855 | +8.343% | -37.204% | -31.932% |
| b64-balanced / 2_streams | 111.284 | 110.404 | 115.394 | 115.114 | +4.520% | -0.243% | +3.441% |
| b64-balanced / 4_streams | 117.354 | 117.084 | 132.624 | 99.543 | +13.273% | -24.943% | -15.177% |
| b64-skewed / 4_streams | 193.526 | 193.846 | 209.807 | 165.505 | +8.234% | -21.115% | -14.479% |

Every target repair/vanilla GPU penalty is positive in all four balanced rounds, and every target fused/repaired GPU effect is negative in all four. For two-stream experts, launch-to-completion host time also changes +4.744% repaired/vanilla, -0.499% fused/repaired and +3.104% fused/installed. Thus the residual is not confined to GPU event timestamps.

| Contrast | GPU losses >2% | Whole-host losses >2% | Launch-host losses >2% | Submission losses >2% |
|---|---:|---:|---:|---:|
| vanilla_vs_installed | 0 | 0 | 0 | 8 |
| repaired_vs_vanilla | 6 | 8 | 8 | 22 |
| fused_vs_repaired | 0 | 0 | 0 | 58 |
| fused_vs_installed | 1 | 1 | 1 | 31 |

Fresh vanilla versus installed stock has no >2% GPU/whole-host/launch-host gain or loss, bounding this observed rebuild effect. Fused versus repaired stock has three GPU and four host gains above2%; fused versus installed stock has three GPU/host gains. Submission times have additional short-duration differences and are retained separately, including58 fused/repaired losses above2%; absence of elapsed-time regressions does not mean every submission cost is neutral.

All GPU losses above2% in these contrasts are listed below.

| Contrast | Cell | GPU change | Positive rounds |
|---|---|---:|---:|
| repaired_vs_vanilla | attention_fetch, h32-miss256-r1152, gather-parallel, total, graph | +2.542% | 4/4 |
| repaired_vs_vanilla | experts, b16-balanced, 2_streams, total, graph | +2.755% | 4/4 |
| repaired_vs_vanilla | experts, b16-balanced, 4_streams, total, graph | +8.343% | 4/4 |
| repaired_vs_vanilla | experts, b64-balanced, 2_streams, total, graph | +4.520% | 4/4 |
| repaired_vs_vanilla | experts, b64-balanced, 4_streams, total, graph | +13.273% | 4/4 |
| repaired_vs_vanilla | experts, b64-skewed, 4_streams, total, graph | +8.234% | 4/4 |
| fused_vs_installed | experts, b64-balanced, 2_streams, total, graph | +3.441% | 4/4 |

The four-arm comparison uses four Williams orders,32 processes and22,016 retained rows, with eight trials per cell and the unchanged51845 expert/KV binary and references. It isolates the combined effect of the two correctness repairs; it does not separate entry from tail repair. Fused/repaired includes all differences in the fused stack (including queue allocation, native admission and placement), so the large four-stream gains cannot be credited to entry fusion alone. Earlier same-byte fusion comparisons address that narrower question.

This is a 172-cell expert/KV comparison. It does not retest attention-dispatch, original waiter, the full broad matrix or HiSparse. The historical95.83% waiter reduction remains from51980. Repaired stock does not replace the original performance goal, qualify a package, or excuse dropping synchronization. The result supports prioritizing the remaining cost of the required graph fork over tuning native admission to address this specific two-stream residual.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-baseline-j52166`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-baseline-j52166`. Source pack, extraction patches, both build recipes, frozen spec, receipts and all raw contrasts are preserved alongside the results. Local mirrored audit passes every mapped hash, control, reference and retained row.
