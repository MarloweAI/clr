# Graph-entry submission order — job51714

Result: deferring ordinary side-entry markers is insufficient to resolve RC2 microbenchmark regressions. One of five preselected affected cells improves by2.45% against same-byte eager submission; the remaining four range from0.035% to1.01% slower. No new >2% aggregate nonwaiter loss appears versus same-byte eager, but stock-relative losses remain. The failed full RC2 bridge is not waived.

Fresh diagnostic HIP `0e8ee585dbc5b79fd601da9804af893036fd07379ffb929d7be4029d543d3a3f`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Root standalone launch/monitoring on one node2 GPU, Slurm0:0. All72 entry/tail/lifecycle processes and80 timing processes/229cells passed strict frozen-source/control/map/row audits. Direct dispatch pinned and receipted1, timing trace0. All samples retained. Local raw mirror re-audits exactly.

The diagnostic retains and materializes the launch predecessor before all graph packets, then optionally moves each unchanged ordinary side marker immediately before the first segment on its logical stream. GPU fence scopes and packet counts are preserved. Both native wait and placement are enabled for RC2/eager/lazy; stock is unmodified. Four position/predecessor-balanced orders, unchanged51663 binaries/references/trials.

| Target graph cell | Stock us | RC2 us | Same-byte eager us | Lazy us | Lazy/eager |
|---|---:|---:|---:|---:|---:|
| attention_fetch, h32-miss256-r1152, gather-parallel, total, graph | 688.442 | 708.523 | 709.122 | 709.373 | +0.035% |
| experts, b16-balanced, 4_streams, total, graph | 231.198 | 161.955 | 161.145 | 161.845 | +0.434% |
| experts, b64-balanced, 2_streams, total, graph | 110.344 | 115.674 | 116.084 | 116.124 | +0.034% |
| experts, b64-balanced, 4_streams, total, graph | 117.054 | 105.724 | 106.134 | 103.533 | -2.450% |
| experts, b64-skewed, 4_streams, total, graph | 193.336 | 161.356 | 163.645 | 165.295 | +1.008% |

Waiter excess removal: RC2 **95.863%**, same-byte eager **95.772%**, lazy **95.752%**. The>=95% objective holds. Small-KV gather remains3.04% slower than contemporaneous stock, and b64-balanced/two-stream experts5.24% slower; both losses occur in all four rounds. Six eager-versus-RC2 cells exceed2%, mainly fixed attention rows; those build/order effects remain retained and limit cross-library attribution. The eager/lazy comparison itself uses identical bytes.

Source review identifies another cost: each entry marker separately retires a CPU submission batch, timestamp and asynchronous handler. Next bounded candidate preserves the full-system GPU barrier and its completion signal while retiring the entry command/predecessor through the existing segment accumulator batch. Preserve profiling/event-agent/non-direct-dispatch fallback and promptly retire partial batches on errors. A zero-completion barrier is not selected because engine transitions could otherwise wait on an older signal.

The next diagnostic is a same-byte2x2 of submission order and CPU retirement, with additional pinned-copy/copy-first/forwarded-producer correctness checks. A successful diagnostic still needs the full frozen microbridge and model checks; no deployment qualification follows from this narrower experiment.

Raw root `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-lazy-j51714`; local mirror under `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-lazy-j51714`. `contrasts.json` retains each round and GPU/host/submit medians.
