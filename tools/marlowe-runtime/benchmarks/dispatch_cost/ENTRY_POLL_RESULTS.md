# Bounded graph-entry CPU polling — job 52103

**Reject the 1 microsecond polling candidate.** All 40 armed KV polls exhausted the budget and still selected a GPU dependency wait. Of 48 armed expert polls, 47 exhausted the budget; only one observed completion, at exactly 1000 ns. The intended packet-elimination mechanism rarely helped in these observations. There are no accepted performance timings, and no longer polling budget is proposed.

One root-owned node2 GPU, standalone launch/wait with a journaled receipt, Slurm 1:0. The build, 144 ordinary correctness processes and 48 injected-failure processes passed. The job stopped at its frozen requirement for at least one within-budget KV completion, before completed-start proofs or timing. This is a hypothesis-gate failure, not a runtime correctness failure. The original spec, raw manifest and stop are preserved; `partial-audit.json` validates the available artifacts while explicitly recording `complete=false` and `performance_qualified=false`.

HIP `31670bc57eb710da5e0738fdeafd267c2cfa226ae1cfde561a9c122a3bfaad9d`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Frozen spec SHA256 `93a10b7b2a79d9b2939ca867b37e288bc978710b9c6a348f51323472c394c00e`.

The diagnostic starts from fused first-batch entry plus the separate consumption observer. At most one eligible root per graph may poll its retained producer signal: Compute engine, known distinct physical queues, initial value exactly one, at most 1000 ns of voluntary polling and 64 extra signal reads. Cap zero bypasses the added admission/status/clock reads. Every outcome continues ordinary dependency import/filtering, strict min24 native admission, SYSTEM acquire, ownership and retirement. No wait is manually removed. Output occurs after graph submission/join and only in separate observation processes; native tracing stays off.

| Observation process | Imported dependencies | Armed roots | Completed within budget | Deadline reached | Entry waits submitted |
|---|---:|---:|---:|---:|---:|
| Experts, polling off | 96 | 48 | — | — | 93 |
| Experts, polling on | 96 | 48 | 1 | 47 | 91 |
| KV, polling off | 40 | 40 | — | — | 40 |
| KV, polling on | 40 | 40 | 0 | 40 | 40 |

All polled values initially required waiting. Poll loop durations span 1000–1010 ns; each process's median is 1000 ns. These counters exclude admission and the initial signal load, so they are not the full added API cost. Clock checks bound voluntary work, not wall-clock latency under OS preemption. The two expert wait totals come from separate untimed processes and do not establish a causal two-packet saving. Instrumented outcome rates are not production-rate estimates.

No sealed proof, 36-process timing grid, waiter retest or model test ran. The earlier fused51980 result—95.83% waiter excess removed, useful four-stream improvements, residual two-stream stock and expert d3 losses—remains the latest measured candidate performance. The polling library is diagnostic only and is not promoted into PR production code.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-poll-j52103`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-poll-j52103`. Mapped library hashes, controls, all correctness rows, source/reference bindings and artifact hashes passed the partial audit. An independent Codex xhigh review agrees that the failed mechanism gate should stand; do not waive it to run timing or extend the polling budget.
