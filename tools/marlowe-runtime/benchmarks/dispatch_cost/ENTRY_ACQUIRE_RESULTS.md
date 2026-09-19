# Graph-entry release deferral — job 51810

Deferring the entry barrier release for eligible kernel-only graphs did not resolve the RC2 performance regressions. None of the five preselected target cells improved by 2% against the identical-byte full-fence control. The diagnostic is not selected for production.

One GPU on marlowe-mi355x-2; root-owned standalone submission and monitoring, Slurm 0:0. The launcher completed in about five minutes, including build, 120 correctness processes and 80 timing processes. All frozen-input, control, mapped-library, row and artifact audits passed, including the downloaded mirror. All trials remain retained.

HIP `9533923f0c914a05f9146d56d36201e1f3cb7b12ef491bd2ff94156a3ad1ac36`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Four balanced orders compare stock, immutable RC2, and the same diagnostic bytes with the flag off/on. Timing uses the unchanged binaries, workload, references and trial counts from job 51663, with trace disabled.

The change retains the entry dependency, SYSTEM acquire, completion signal, timestamp, handler and command ownership. It defers release with dirty/pending/invalid fence bookkeeping so existing engine and CPU publication boundaries must supply it. Eligibility is cached only for flat, known-single-device kernel-only graphs. Host, copy, event, child, unknown and multi-device graphs retain ordinary entry behavior. This is not a general fence-elision policy.

| Graph target | Stock us | RC2 us | New full-fence us | New acquire-only us | Same-byte change | Acquire vs stock |
|---|---:|---:|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | 689.422 | 707.292 | 705.672 | 704.562 | -0.157% | +2.196% |
| b16-balanced, 4_streams | 230.987 | 161.565 | 163.326 | 161.955 | -0.839% | -29.886% |
| b64-balanced, 2_streams | 110.484 | 115.134 | 115.414 | 114.834 | -0.503% | +3.937% |
| b64-balanced, 4_streams | 116.664 | 105.704 | 104.343 | 104.773 | +0.412% | -10.192% |
| b64-skewed, 4_streams | 196.107 | 163.725 | 167.376 | 164.336 | -1.816% | -16.201% |

Waiter pending-minus-alone excess is 2090.579 us on stock and 86.511 us with acquire-only: **95.862% removed**. The repeated two-stream expert loss remains above 2% in all four rounds. KV gather remains 2.196% slower in aggregate.

Across all 229 cells, acquire-only has three aggregate >2% losses against the same-byte full-fence control, including two eager cells where this graph-only change is inactive. The fresh full-fence build also has three >2% losses against immutable RC2. These observations are retained; they do not establish a causal fence effect. All per-round GPU, host and submission measurements are in `contrasts.json`.

Correctness covers native/placement off/on, acquire off/on and queue caps 1/4/8. The new full-buffer fixture uses fresh patterns for every completion method and epoch, verifies 64KB/8MB output through D2H, and checks stream synchronization, ordinary events, timing-disabled events and stream query. Separate untimed receipts prove active kernel entry and copy-root fallback. These checks validate this diagnostic, not production deployment.

The existing data also argues against a pure GPU-event accounting explanation for the residual stock losses. On full-fence versus stock, KV loses 16.250 us GPU and 16.706 us host; two-stream experts lose 4.930 us GPU and 4.950 us host. The host clock starts before the begin-event enqueue and ends after completion. Missing entry ordering can still alter overlap, but the regression is visible in host completion time as well.

Together with lazy submission (51714) and shared CPU retirement (51745), this rules out those individual changes as sufficient remedies. It does not isolate the full causal cost of the generic entry repair or justify removing correctness dependencies. The full minimal-byte microbenchmark screen remains failed and the final new-byte HiSparse bridge remains held.

Raw root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-acquire-j51810`; local mirror under `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-acquire-j51810`.
