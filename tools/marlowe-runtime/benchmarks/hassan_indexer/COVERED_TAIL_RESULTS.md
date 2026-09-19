# Covered final stream waits — job 53362

Removing a final wait whose actual side-stream tail is already consumed by the launch-stream dependency chain fixes the persistent balanced two-stream expert GPU regression in this allocation. This preserves useful parallelism. It does not solve automatic stream selection: Hassan still needs the separate one-stream/shared-retirement specialization to beat stock.

The entire node2 job completed **0:0 in 10m09s**. All source, artifact, mapped-library, control, correctness and timing audits pass remotely and locally; all trials are retained. This is diagnostic evidence, not a production-qualified package.

## Same-allocation expert results

GPU microseconds; lower is better. Parent is the immutable lane-retirement binary from job53285 with sharing enabled. New off/on use identical bytes, both with lane retirement enabled and the same per-replay ancestry computation. Only final wait selection differs.

| Original graph workload | Stock | Parent | New omit off | New omit on | On / off | On / stock |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| b16-balanced / 2 streams | 229.227 | 230.057 | 230.038 | 225.728 | -1.87% | -1.53% |
| b16-balanced / 4 streams | 235.188 | 159.565 | 159.485 | 152.435 | -4.42% | -35.19% |
| b64-balanced / 2 streams | 111.394 | 115.084 | 114.294 | 109.654 | -4.06% | -1.56% |
| b64-balanced / 4 streams | 117.114 | 99.623 | 101.264 | 93.843 | -7.33% | -19.87% |
| b64-skewed / 2 streams | 194.026 | 194.796 | 194.326 | 189.296 | -2.59% | -2.44% |
| b64-skewed / 4 streams | 195.856 | 163.065 | 161.125 | 157.195 | -2.44% | -19.74% |

The balanced b64 two-stream target improves **114.293750→109.653749us**, a same-byte gain of **4.06%**. Stock is111.393750us: the candidate is **1.56% faster**, with every round improving1.01–2.28%. Host completion improves3.76% versus off and1.39% versus stock; CPU submission improves7.58% versus off. The parent-to-new-off bridge is−0.69% GPU and−0.65% submission for this target; it is measured separately and is not assigned to wait omission.

Across all76 expert/grouped cells there are no aggregate GPU losses above2% against stock or new-off. The first allocation did **not** pass every original screen: isolated b64-skewed merge/eager host time is15.1775us versus stock14.5225us (+0.655us/+4.51%) and new-off14.5775us (+4.12%). Two of four rounds lose about9%, two are near neutral; GPU median is+0.51% versus stock. The graph-only intervention is inactive on this eager path. The unchanged confirmation below does not reproduce that loss; preserve both allocations separately; do not exclude trials or investigate multi-second gaps. Submission-only cells also have mixed signed changes and are retained in the raw summary.

Grouped split1 stays within0.12% of stock GPU; split22 is5.06–8.18% faster. These copy graphs use fallback, so their retained gains are not caused by final-wait omission.

## Hassan remains a separate stream-choice problem

Original four-kernel graph, original Q/K kernels, shapes, inputs and200-replay protocol:

| Setting | GPU us | Host us | Submission us |
| --- | ---: | ---: | ---: |
| Stock | 19.99246 | 20.03028 | 4.39808 |
| Immutable parallel parent | 22.19718 | 22.23757 | 4.33108 |
| New parallel, omission off | 22.16478 | 22.20859 | 4.42302 |
| New parallel, omission on | 22.21948 | 22.26196 | 4.47408 |
| New one-stream + shared retirement | 19.26939 | 19.30919 | 2.34718 |

The explicit one-stream/shared setting is **3.62% faster than stock GPU** and3.60% faster host, with all10 process rounds improving. Submission falls46.63%. Parallel omission on is11.14% slower than stock and differs+0.25% from same-byte off. Structural receipts confirm its two independent roots retain their required final join; no wait is omitted. These are different configurations, not a single automatic policy. Prior expert holdouts reject unconditional one-stream execution because it regresses useful parallel work45–75%.

## Why the omission is correct, and what was measured

Track each logical stream's actual last submitted segment and exact sealed retirement region. On complete successful execution only, walk explicit dependencies backward from the actual last launch-stream segment. Omit a side wait only if its actual tail is an ancestor and its stream/command/region identities match. Never infer coverage from an earlier consumed export or a shared command alias. Both toggle arms do the same planning work.

The existing interior dependency path already waits on and retains the exported completion command, including its fence. Every export is sealed at its original boundary. The removed final marker had cache-ignore scope too. Preserve entry imports, interior waits, packet batch boundaries, allocation/assignment, every unsupported path, every error-prefix join and each unconsumed final tail. If some tails remain, the final marker remains. The measured4.64us target gain is the effect of this intervention, including CPU/packet/scheduling changes; it is not a universal per-marker cost or firmware attribution.

Codex xhigh source/fixture review found no correctness blocker after a flags-macro continuation fix before compilation. Claude quota was exhausted and the user-authorized fallback was used. The reviewer highlighted map/DFS replay cost: Hassan new-off submission is2.12% above the immutable parent, so topology caching/preallocated data merits consideration before promotion. Do not infer zero planning cost from small GPU differences.

## Validation and exact identities

- 54 existing correctness processes /1,404 reference rows, caps1/4/8 and three new-byte configurations.
- 15 lifetime processes /60 rows, including an old exported command followed by a newer open region, disabled roots, parameter changes, stream changes and destruction before completion. Six failure processes inject after three published segments and retain all side joins; this is not an intra-packet-publication failure test.
- 12 new covered-tail processes /72 rows. One DAG consumes an earlier side export but has a later slow unconsumed tail; it must keep that wait. Another consumes one of two side tails; it removes only that one and keeps the final marker for the slow independent tail. All output slots are checked after launch-stream readback. Caps4/8 use distinct physical queues; cap1 is an additional alias control.
- Three two-GPU setter/device-invalidation processes /42 rows. Performance uses GPU0; GPU1 is used only for correctness.
- Six separate expert/grouped structural proofs and48 unchanged timing processes /9,728 rows /76 cells in four balanced orders.
- Three separate Hassan structural proofs and50 timing processes /800 timings /1,000 correctness checks in ten balanced carryover orders.

New HIP SHA256 `1f8cb274554d3437478ddee0eba00260d5d2a15a8462408127640f1984d41810`; parent `57c5f40acd76cb4210cb123393031f7452c754500c75cff644caa34de652d19b`; HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Stock HIP `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`. Mirrored actual libraries also hash correctly locally.

The [diagnostic source commit](https://github.com/MarloweAI/clr/commit/40d4389) contains the tested source contents on branch `marlowe/covered-tail-diagnostic-20260918`; it is separate from PR1's main runtime. Exact build provenance remains base `cab5670a350678f2b0a6feb388fcbbca56c426a1` plus frozen `covered-tail-full.patch`, because committing the same contents afterward can change embedded version metadata on rebuild. Controls: native wait1, node-count placement1, qualified spare1, lane-retire1; covered-tail0/1; tracing0 for all timings. The one-stream arm additionally sets logical-coalesce1/shared-retire1.

Raw, source/hash manifests, scripts, library mirror and local-final-audit.json: `iterations/hassan-qk-micro-20260918/covered-tail-j53362`, sibling `covered-tail-source.json`, `covered-tail-harness.json`, `covered-tail-full.patch`, `covered-tail-port.patch`, `run_covered_tail.py`, `audit_covered_tail.py`, `covered-tail-lib`. Remote mirror uses the same suffix under `/workspace/home/sasha/amd-runtime-production`.

Next: an opt-in plan selector using completed blocks of actual requested replays, with calibrated timing-marker overhead, no extra kernel executions and an unprobed validation phase. It must report decision lag and exploration amortization; a decision cannot affect already submitted work. The eager host confirmation below is complete. Qualify one chosen package across broader microbenchmarks, waiter overhead, PyTorch and retained HiSparse C1 on/off, followed by C4. Prior fusedRC1 waiter/PyTorch/model qualifications do not transfer to these bytes.


## Unchanged confirmation — job 53419

One node2 GPU, same exact source/harness/spec/runtime/workloads/protocol/order as the53362 expert/grouped matrix. No kernel, input, repetition, exclusion or timing change. Slurm completed0:0; remote and local audits pass all48 timing processes/9,728 rows/76 cells and six separate structural proofs. Spec SHA256 remains `c90d251e33bfbf5712aa1a43667d1c79d3057995f9a7e92cdad4c414b4f1ce3b`.

| b64 balanced two-stream graph | Stock | Immutable parent | New omit off | New omit on |
| --- | ---: | ---: | ---: | ---: |
| GPU us | 110.583501 | 115.123749 | 114.464000 | 109.623499 |
| Host us | 120.4750 | 124.8025 | 124.3025 | 119.2475 |
| Submission us | 9.0925 | 9.0425 | 8.9675 | 8.4125 |

Same-byte omission improves GPU4.23%, host4.07% and submission6.19%; all four rounds improve GPU3.49–4.31%. Against stock it is0.87% faster GPU and1.02% faster host, with all GPU rounds improving0.04–2.22% and host rounds neutral or better. This repeats the target's recovery without pooling the two allocations or replacing the first baseline.

The isolated eager merge host cell is14.530us versus stock14.665us (−0.92%) and new-off14.5675us (−0.26%). Its earlier+4.51% host loss does not repeat above2% in any confirmation round. This resolves the need for one unchanged confirmation, not the attribution of that earlier variation; no gap investigation was performed.

Across76 aggregate cells, omission-on has **zero GPU and total-host losses above2%** against stock or same-byte off. It has15 GPU/host wins above2% versus stock. Submission-only changes remain mixed:18 cells lose and28 win above2% versus stock; two lose and17 win versus off. Those metrics are retained and this is not a claim of universally lower CPU cost or statistical equivalence. The full stock screen, original first-allocation host result and all signed per-round values remain available.

Raw: `iterations/hassan-qk-micro-20260918/covered-confirm-j53419`; exact source/spec reused from53362. `local-final-audit.json` binds the verifier, manifest and summary hashes. Hassan was not rerun in this confirmation; its50-process53362 comparison remains the current evidence. No runtime or package was promoted.
