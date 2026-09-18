# Singleton graph-entry barrier-value representation — job 52130

**Do not select this change.** Replacing the single selected entry AND packet with an equal-zero AMD barrier-value packet does not resolve the residual microbenchmark penalties. The two-stream expert target changes only -0.105% and KV -0.164%; the skewed four-stream target slows 1.940%. No aggregate GPU or host elapsed-time cell changes by more than 2% in either direction. Close this packet-representation branch without a mask, condition or ordering-bit sweep.

One root-owned node2 GPU; standalone launch/wait/audit; Slurm 0:0. All 144 ordinary and 48 injected-failure processes, eight untimed packet proofs, and 36 timing processes passed. All 24,768 timing rows across 172 cells are retained. The downloaded raw/library mirror passes the same audit.

HIP `17745cdf9b0a590321422b7ad0ebb7f75b1ebf2b51ba149ed2979d4975770a73`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Source full-patch SHA256 `711edcd5a6a91e6f95430a98b5a0ff4e1acaaec0c0edd3e316fedd89d4363634`.

The diagnostic starts from fused51980 plus its separate observer. Only an exact singleton retained entry dependency on a device with barrier-value support changes representation. Ordinary ready-signal filtering, every native prewait call and min24 admission remain unchanged. A zeroed one-slot packet uses EQ0, all-bits mask, barrier bit one, no packet scopes and completion signal zero. The first kernel retains SYSTEM acquire/release. There is no new completion allocation, instruction buffer, raw signal pointer or CPU polling. Accumulator ownership, partial-failure retirement, joins and graph lifetime remain unchanged.

Separate proof processes observe 96/96 expert and 40/40 KV entry waits emitted as vendor-value packets with header256/format2/mask-1/condition0/value0/completion0. Ordinary controls emit 93/96 expert and 40/40 KV AND waits; the differing counts come from separate instrumented processes. All 272 completed-start imports emit no entry wait. Timing uses observer0 and native trace0. Source review independently verified that representation selection is active with observation disabled.

| Target, graph total | Prior fused GPU µs | New build, AND µs | Same build, value µs | Value/AND GPU | Value/AND launch-to-completion host |
|---|---:|---:|---:|---:|---:|
| h32-miss256-r1152/gather-parallel | 700.313 | 700.903 | 699.752 | -0.164% | -0.127% |
| b16-balanced/4_streams | 158.245 | 158.975 | 157.375 | -1.007% | -0.597% |
| b64-balanced/2_streams | 114.644 | 114.564 | 114.444 | -0.105% | -0.047% |
| b64-balanced/4_streams | 100.153 | 99.973 | 100.093 | +0.120% | -0.334% |
| b64-skewed/4_streams | 162.555 | 162.366 | 165.515 | +1.940% | +1.576% |

Six balanced process orders compare immutable fused51980, rebuilt AND, and identical-byte value. Each process retains eight trials per cell and uses the unchanged 51845 binary/references. Whole-host, launch-host, GPU and submission metrics remain in the raw contrasts. None of the five target GPU effects has the same sign in all six rounds.

| Contrast | GPU losses >2% | Whole-host losses >2% | Launch-host losses >2% | Submission losses >2% |
|---|---:|---:|---:|---:|
| full_vs_prior | 0 | 0 | 0 | 11 |
| value_vs_full | 0 | 0 | 0 | 5 |
| value_vs_prior | 0 | 0 | 0 | 6 |

There are also zero >2% GPU/whole-host/launch-host gains for each contrast. The full submission-loss list follows; these short host measurements are retained, not promoted to end-to-end regressions.

| Contrast | Cell | Submission change |
|---|---|---:|
| full_vs_prior | attention_fetch, h128-miss128-r1152, memcpy, resident, eager | +2.149% |
| full_vs_prior | attention_fetch, h128-miss128-r1152, memcpy-serial, total, graph | +2.237% |
| full_vs_prior | attention_fetch, h32-miss128-r1152, gather, miss_attention, eager | +2.143% |
| full_vs_prior | attention_fetch, h32-miss128-r1152, gather-parallel, total, graph | +3.030% |
| full_vs_prior | attention_fetch, h32-miss128-r584, gather-parallel, total, graph | +3.664% |
| full_vs_prior | attention_fetch, h32-miss32-r1152, gather-parallel, total, graph | +2.615% |
| full_vs_prior | experts, b16-balanced, 1_streams, total, eager | +2.744% |
| full_vs_prior | experts, b16-balanced, 2_streams, total, graph | +2.139% |
| full_vs_prior | experts, b64-balanced, 1_streams, total, graph | +2.960% |
| full_vs_prior | experts, b64-balanced, 2_streams, total, graph | +3.749% |
| full_vs_prior | experts, b64-skewed, 4_streams, total, graph | +2.513% |
| value_vs_full | attention_fetch, h32-miss128-r584, gather, copy, graph | +2.121% |
| value_vs_full | attention_fetch, h32-miss256-r1152, gather, miss_attention, graph | +2.773% |
| value_vs_full | experts, b16-balanced, isolated, expert0, graph | +2.217% |
| value_vs_full | experts, b16-balanced, isolated, expert1, graph | +3.165% |
| value_vs_full | experts, b16-balanced, isolated, expert3, graph | +3.069% |
| value_vs_prior | experts, b16-balanced, 2_streams, total, graph | +2.005% |
| value_vs_prior | experts, b16-balanced, batched, total, eager | +2.870% |
| value_vs_prior | experts, b16-balanced, isolated, expert0, graph | +3.519% |
| value_vs_prior | experts, b64-balanced, 1_streams, total, graph | +2.368% |
| value_vs_prior | experts, b64-balanced, 2_streams, total, graph | +2.508% |
| value_vs_prior | experts, b64-balanced, 4_streams, total, graph | +3.152% |

No new stock/d3 comparison, waiter measurement or HiSparse run occurred. The earlier fused candidate still has the measured 95.83% waiter excess reduction and unresolved stock/d3 losses. This test does not qualify new source or a package. The null result constrains this packet representation only; it does not prove that GPU waiting is free or identify a firmware implementation.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-value-j52130`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-value-j52130`. `contrasts.json` retains all cells, metrics and round effects; the frozen spec, full patch, launcher, audit and review are alongside it.
