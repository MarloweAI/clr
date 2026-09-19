# Fused entry acquire/release discriminator — job 52028

**Do not select the additional scope change.** Preserving the captured release scope while adding the required SYSTEM acquire does not materially improve the five preselected targets. Their GPU changes range from -0.360% to +0.628%; b64 two-stream changes only -0.122%. The first kernel’s promoted release is not the dominant residual cost in these measurements. Retain the earlier fused diagnostic as the useful architectural candidate.

One root-owned node2 GPU; standalone launch/wait/audit; Slurm0:0. All144 ordinary correctness processes,48 injected-failure processes,4 untimed scope proofs and36 timing processes passed. Local raw/library mirror independently audited. All24,768 timing rows/172cells are retained. Six balanced orders compare immutable51980 fused, rebuilt full-scope fused, and acquire-only fused in the identical new binary. No model or waiter benchmark was run here.

HIP `f16306c0606cdad4d7648479317c6910706477fa30deb46fe19f2b181b5d73ce`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Source diff against cab5670: `9d7e01c712aa89f6e29c7c360d08b138c34cd156ab575354d5a77bf8aaece16a`. Diagnostic remains isolated from PR1 production source.

The per-call treatment upgrades the first actual kernel acquire to SYSTEM without requesting a release. It preserves every captured release scope and any unrelated pre-existing system-scope request. Dependency packets, barrier bits, native min24 admission, retained ownership, partial-error retirement and final side joins are unchanged. Existing bookkeeping records actual release scope and keeps pending/dirty state for normal publication.

Untimed traces prove the intended contrast for every eligible root:96expert and40KV roots in each arm. Each first chunk has one packet. Full arm publishes SYSTEM acquire/SYSTEM release; acquire-only publishes SYSTEM acquire/AGENT release, preserving captured AGENT release. No unrelated scope request forced SYSTEM in the acquire-only observations. The scope_requested receipt is sampled at generic batch entry, so the full arm includes its new request. Traced times are never performance evidence.

| Preselected graph target | Immutable fused us | Rebuilt full scope us | Acquire-only us | Same-byte change |
|---|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | 701.903 | 702.022 | 699.492 | -0.360% |
| b16-balanced, 4_streams | 158.205 | 157.625 | 158.615 | +0.628% |
| b64-balanced, 2_streams | 114.724 | 114.944 | 114.804 | -0.122% |
| b64-balanced, 4_streams | 99.903 | 99.803 | 100.384 | +0.582% |
| b64-skewed, 4_streams | 163.495 | 164.546 | 164.395 | -0.091% |

No GPU or launch-host elapsed cell regresses above2% for acquire/full, full/prior, or acquire/prior. Submission time has13,4,and3 >2% cells respectively; every value is retained in contrasts.json. No stock/d3 cohort was rerun in this bounded experiment, so the earlier residual percentages are not re-estimated from separate jobs.

This rejects the promoted first-kernel release as a useful next optimization; it does not prove the full remaining cost comes from the dependency wait. Source inspection also confirms WaitingSignal already filters completed hardware signals at consumption, so a new readiness check alone would duplicate existing behavior. Next, use the existing completed-start control with immutable fused bytes to separate pending-dependency sensitivity from the remaining cost before changing more runtime code.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-scope-j52028`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-scope-j52028`. Frozen inputs, patches, scripts, scope proofs, every timing metric and per-round contrasts are preserved alongside it.
