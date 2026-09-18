# Minimal runtime microbenchmark comparison — job 51663

The exact RC2 candidate passed its correctness qualification but failed the frozen performance screens. Do not promote it or claim the older diagnostic HiSparse timings apply to these bytes. The final RC2 C1/C4 bridge has not been launched.

HIP `986f1c50c2b6a811d67dcfe1329ee544b9330256313f4745abbab8c22a9994b9`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Core source is equivalent to PR commits d862ffe and b8d4652. Both optimization flags default off.

One node2 GPU; 144 broad + 32 fixed-attention/waiter processes, four position/predecessor-balanced orders, 46,912 retained timing rows, 313 cells. All timing used trace0. Workloads, kernels, references and trial counts were unchanged. In-container source/identity/map/control/output audits passed. Local artifact mirror and deterministic contrast recomputation agree.

Waiter excess (pending minus alone): stock **2095.497 us**, earlier selected diagnostic **84.751 us**, RC2 on **83.477 us**. RC2 removes **96.016%** of same-allocation stock excess.

## Failed screens

RC2 on exceeds the 2% aggregate loss screen in five cells versus stock and seven versus d3; RC2 off exceeds it in seven cells versus stock. Rows below show every failed nonwaiter cell against any required comparator. Positive percentages mean slower. The table does not trim individual trials or average with earlier allocations.

| Case | Cell | Stock us | d3 us | RC2 off us | RC2 on us | On/stock | On/d3 | Off/stock |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| attention_fetch | h32-miss128-r1152, gather-parallel, total, graph | 694.822 | 696.942 | 710.152 | 711.942 | +2.46% | +2.15% | +2.21% |
| attention_fetch | h32-miss256-r1152, gather-parallel, total, graph | 686.652 | 688.442 | 710.682 | 708.243 | +3.14% | +2.88% | +3.50% |
| dispatch | 256, 256, 4, eager, parallel | 184.895 | 188.704 | 188.735 | 188.999 | +2.22% | +0.16% | +2.08% |
| experts | b16-balanced, 2_streams, total, graph | 224.848 | 226.448 | 230.618 | 231.197 | +2.82% | +2.10% | +2.57% |
| experts | b16-balanced, 4_streams, total, graph | 234.018 | 151.295 | 161.995 | 162.286 | -30.65% | +7.26% | -30.78% |
| experts | b64-balanced, 2_streams, total, graph | 111.003 | 110.274 | 115.483 | 115.603 | +4.14% | +4.83% | +4.04% |
| experts | b64-balanced, 4_streams, total, graph | 116.324 | 95.673 | 105.683 | 104.453 | -10.20% | +9.18% | -9.15% |
| experts | b64-skewed, 4_streams, total, graph | 194.047 | 159.526 | 166.295 | 166.496 | -14.20% | +4.37% | -14.30% |
| grouped_s22 | h32-l32-miss128-depth1-planus0-backupside-splits22, prefetch_on, total, graph | 11545.196 | 10822.597 | 11809.473 | 10874.860 | -5.81% | +0.48% | +2.29% |
| grouped_s22 | h32-l64-miss128-depth1-planus0-backupside-splits22, prefetch_on, total, graph | 23069.082 | 21778.783 | 23647.348 | 21781.156 | -5.58% | +0.01% | +2.51% |

Five RC2-on losses against d3 exceed 2% in **all four rounds**: small-KV gather graph h32/miss256; expert graphs b16 balanced/four streams, b64 balanced/two streams, b64 balanced/four streams and b64 skewed/four streams. The b64 balanced/two-stream row also loses to stock in all four rounds. Other failures remain failures; they are not assumed to be noise.

## Interpretation and next comparison

The new generic entry fork also executes with both optimization flags off, making it a plausible common cause of graph losses. This allocation does not isolate it from other source/build differences. Source review finds each ordinary side marker creates its own timestamp, completion-signal bookkeeping and batch handler, uses system acquire/release, and is submitted before any root kernel. The existing micro timing records a start event immediately before graph launch: the repaired side roots now respect that event, whereas the old missing edge did not. These facts do not invalidate or waive the frozen performance screen.

First candidate: retain/materialize the launch predecessor before all graph packets, then submit each unchanged ordinary marker immediately before the first root segment on that logical side stream. Preserve all system fences, dependencies, tail joins and lifetime ownership. Compare eager/lazy scheduling on identical diagnostic bytes with all raw timing retained. Second candidate, if needed: keep the full-system dependency barrier but defer marker retirement/bookkeeping into the segment completion batch; this needs additional ownership/profiling/error-path proof. Do not simply remove the entry fork or change it to a no-scope marker.

The original async initialization discriminator found the same missing edge in stock and earlier diagnostics; RC2 corrected it. The entry/tail/lifecycle checks remain required for any alternative. No gap investigation or full-model performance rerun was launched to explain these micro losses.

## Follow-up results

The proposed lazy-submission and shared-retirement experiments completed as jobs
51714 and 51745. Neither resolves the frozen losses. Job 51810 additionally tested
kernel-only SYSTEM-acquire entry with deferred release; it also fell short, while
preserving 95.86% waiter-excess removal. All are same-byte comparisons with full
correctness and raw artifact audits. See [lazy submission](ENTRY_LAZY_RESULTS.md),
[CPU retirement](ENTRY_BATCH_RESULTS.md), and [release deferral](ENTRY_ACQUIRE_RESULTS.md).
The original failed screens remain in force; no final model bridge was launched.

## Artifact validation recovery

Slurm completed 0:0 and both suites ran their audits and summarizer inside the container. The standalone watcher then redundantly re-ran a library auditor on the login node, where the stock `/opt/rocm-7.2.4` path does not exist. The original failure is retained in the receipt. `verify_placement_bridge_artifacts.py` validates the saved in-container audit/manifest hashes, all raw hashes/control/map receipts, exact source/binaries/references and unchanged recomputed contrasts, without pretending to inspect a live process. Its output distinguishes artifact integrity success from **performance_passed=false**.

Raw roots: `placement-bridge-broad-j51663`, `placement-bridge-attention-j51663` under `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918`; local mirrors under the same iteration name in `/home/sashawork/dev/amd-runtime-production/iterations`.
