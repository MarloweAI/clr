# First-batch graph-entry dependency — job 51980

**Useful architectural improvement, still not qualified.** Fusing the entry dependency into the first captured root batch improves four of the five preselected targets relative to the same build’s lazy ordinary marker. No aggregate cell loses more than 2% in GPU or host elapsed time in either fused/lazy or fused/eager comparison. Submission time has 18 fused/lazy and 22 fused/eager cells above 2%; those measurements remain retained. The two-stream expert case remains 3.421% slower than stock, and four expert targets remain 4.37–5.83% slower than historical d3. Keep the final HiSparse bridge held.

One node2 GPU, root-owned standalone launch, wait and validation; Slurm 0:0. All 216 ordinary correctness processes, 24 injected-failure processes, six untimed dependency proofs and 180 timing processes passed. All 69,408 timing rows across 229 cells are retained. Six balanced Williams orders cover stock, immutable RC2, historical d3, and three modes of one new build. The local raw/library mirror independently passes the same audit.

HIP `bf7ab37233fce87f88e00020c3538791d02ed549081d54274921487a654659e1`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Full source diff `fe97960bedd46a6120bac12ccd91e80d580ae1c683b60bf41e6380397ff3658b` against cab5670 + the recorded RC2 patch. This is an isolated diagnostic; PR1 production runtime source is unchanged.

The graph retains and materializes its launch predecessor before any graph packets. For a qualified flat single-device kernel graph, each first nonempty captured side-root accumulator owns that event separately from its ordinary wait list. It imports the hardware dependency exactly once, keeps the existing min24 native admission and AQL wait, then applies SYSTEM acquire to the first kernel batch. Ownership remains until accumulator retirement. Empty/disabled, uncaptured, cooperative, copy, child, unknown-device and profiling paths retain ordinary markers. Lazy markers use identical eligibility and frontier preparation, so fused/lazy isolates the representation change. The eager control measures the net effect and rebuild differences.

Errors after partial submission retire the failing accumulator and join every actual side tail before the graph-release callback. New fixtures toggle disabled roots on repeated execution and inject failures after dependency publication or after kernel publication, followed by immediate graph destruction and kernel-argument-pool churn. Existing transfer and full-buffer publication checks remain unchanged. Untimed proof observes exactly 96 expert and 40 pure-KV eligible roots in each lazy/fused process, and one import per fused root; eager and lazy have no fused imports.

| Preselected graph target | Stock us | Historical d3 us | RC2 us | New eager us | New lazy us | Fused us | Fused / lazy |
|---|---:|---:|---:|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | 690.792 | 691.422 | 709.347 | 707.893 | 710.362 | 701.813 | -1.204% |
| b16-balanced, 4_streams | 232.758 | 150.205 | 162.505 | 164.836 | 162.225 | 158.375 | -2.373% |
| b64-balanced, 2_streams | 111.093 | 110.084 | 115.224 | 115.524 | 115.854 | 114.894 | -0.829% |
| b64-balanced, 4_streams | 116.634 | 95.833 | 104.333 | 106.403 | 103.693 | 100.423 | -3.153% |
| b64-skewed, 4_streams | 195.326 | 155.615 | 163.685 | 163.745 | 164.075 | 164.686 | +0.372% |

The KV and three balanced-expert fused/lazy improvements occur in all six rounds. The skewed four-stream target is mixed (+0.372% aggregate). Relative to eager markers, the balanced four-stream improvements are 3.919% and 5.620%; the two-stream gain is only 0.546%. This supports reducing marker representation overhead, but does not establish the source of the remaining entry penalty.

Waiter pending-minus-alone excess is 2106.478 us on stock and 87.840 us fused: **95.830% removed**. Immutable RC2 removes 95.797%, d3 95.843%, eager 95.837%, and lazy 95.727%.

| Contrast | Aggregate non-waiter cells slower by >2% |
|---|---:|
| full_vs_rc2 | 7 |
| lazy_vs_full | 0 |
| fused_vs_lazy | 0 |
| fused_vs_full | 0 |
| fused_vs_stock | 4 |
| fused_vs_d3 | 4 |

Every residual >2% loss and every >2% rebuilt-eager/RC2 difference is retained below. The rebuilt control itself changes several attention-dispatch timings, including eager cases; do not attribute those differences to fused entry behavior.

| Contrast | Cell | Change | Rounds slower |
|---|---|---:|---:|
| full_vs_rc2 | dispatch, 256, 1024, 1, eager, wide | +2.535% | 4/6 |
| full_vs_rc2 | dispatch, 256, 1024, 1, graph, serial | +2.113% | 5/6 |
| full_vs_rc2 | dispatch, 256, 1024, 1, graph, wide | +2.512% | 4/6 |
| full_vs_rc2 | dispatch, 256, 1024, 4, eager, parallel | +2.649% | 4/6 |
| full_vs_rc2 | dispatch, 256, 1024, 4, eager, serial | +3.055% | 4/6 |
| full_vs_rc2 | dispatch, 256, 1024, 4, graph, parallel | +2.811% | 4/6 |
| full_vs_rc2 | dispatch, 256, 1024, 4, graph, serial | +2.898% | 4/6 |
| fused_vs_stock | dispatch, 256, 1024, 1, graph, parallel | +2.242% | 4/6 |
| fused_vs_stock | dispatch, 256, 256, 1, eager, wide | +3.330% | 4/6 |
| fused_vs_stock | dispatch, 256, 256, 1, graph, wide | +3.240% | 5/6 |
| fused_vs_stock | experts, b64-balanced, 2_streams, total, graph | +3.421% | 6/6 |
| fused_vs_d3 | experts, b16-balanced, 4_streams, total, graph | +5.439% | 6/6 |
| fused_vs_d3 | experts, b64-balanced, 2_streams, total, graph | +4.369% | 6/6 |
| fused_vs_d3 | experts, b64-balanced, 4_streams, total, graph | +4.790% | 6/6 |
| fused_vs_d3 | experts, b64-skewed, 4_streams, total, graph | +5.829% | 5/6 |

Stock and historical d3 lack the required external launch-entry edge. Their timings are useful comparators, but discarding that edge is not an acceptable way to recover their performance. Before selecting a minimal implementation, distinguish the cost of the required pending dependency from remaining packet/fence or host-submission work. This experiment does not make a new HiSparse performance claim.

Attempt 51968 built these same bytes and passed all 216 ordinary checks. Its first injected-failure epoch passed; the next epoch saw the deliberately injected prior `hipErrorUnknown` through `hipGetLastError`, because the fixture had not consumed it. The fixture now explicitly verifies and clears that expected error at its origin. The original attempt and harness are preserved; 51980 reran every gate using unchanged, hash-pinned runtime bytes. No timing ran in 51968.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-fused-j51980`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-fused-j51980`. `contrasts.json` contains every cell, metric and round; the frozen spec, patches, scripts and prior-attempt snapshot remain in that iteration directory.
