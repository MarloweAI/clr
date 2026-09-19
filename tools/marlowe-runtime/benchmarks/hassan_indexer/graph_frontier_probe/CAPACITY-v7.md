# Frontier v7 resource and lifetime checkpoint

V7 replaces the temporary blocking capacity policy with prepublication fallback to the ordinary graph path. It preserves asynchronous submission when a caller must later release GPU work. It also starts ordinary retirement at public graph-exec destruction, once per logical launch stream. The private generation pool is bounded at 1,024 arenas per GraphExec (diagnostic tests can lower this cap). This is not a global byte budget.

## Evidence

Build 55659 completed on node2. Job 55671 passed nine preflight processes and the required six-cell ownership audit. It then failed compiling the new host-fed test because hipHostGetDevicePointer requires void**; no capacity case ran in that job. Original source, log and partial output are retained. Only the test was corrected in graph_frontier_host_fed_v2.cpp/capacity_v3.py. Job 55677 completed 0:0 and passed all seven capacity cases; downloaded local audits also pass. No runtime bytes changed between these jobs.

| Test | Private launches / total | Peak live generations | Ordinary fallbacks | Result |
|---|---:|---:|---:|---|
| Burst, cap 2 | 2/64 | 2 | 62 | 448 values correct |
| Burst, cap 8 | 8/64 | 8 | 56 | 448 values correct |
| Burst, cap 32 | 32/64 | 32 | 32 | 448 values correct |
| Boundaries, cap 8 | 180/1139 | 8 | 959 | 2210 values correct; callback once |
| Boundaries, cap 1024 | 1139/1139 | 1001 | 0 | 2210 values correct; callback once |
| Idle destruction, cap 8 | 1/1 | 1 | 0 | Destroy returned in 0.01583ms; retirement during HIP-free idle |
| Caller-released GPU work, cap 2 | 2/8 | 2 | 6 | All launches returned in 0.3118ms; 16 values correct; watchdog unused |

The caller-released fixture queues kernels that await a coherent host flag. The submitting thread writes that flag only after all eight launches return. A separate two-second watchdog releases it if submission gets stuck. V7 completed without that rescue. This is a semantics test, not a performance sample. Ordinary queue-ring pressure can still throttle asynchronous direct dispatch; this change does not promise unbounded nonblocking submission.

The idle test destroys GraphExec while delayed work remains, then makes no HIP call for 500 ms. Its release receipt appears after destroy begins and before idle ends. Destruction notifications are deduplicated by HostQueue, not physical queue: separate logical streams retain separate host batches. The burst fixture uses two logical streams and reports two notifications; ordinary boundary/idle cases report one.

## Ownership and ordering

Each generation owns a pending-command reference after all fallible prepublication preparation, and terminal callbacks detach that reference on both success and error. Releases happen outside the pool mutex. Final successful command cleanup permits arena reuse only after successor readers have released their leases. Error generations retain quarantine ownership. Fatal device-error quarantine is source-reviewed, not injected by these tests.

At capacity, no packets or new ownership have been published. An internal hipErrorNotReady sentinel returns to GraphExec::Run, which enters ordinary lowering; genuine allocation failure remains an error. The independent source review found no ordering blocker. For a qualified graph with multiple roots, the predecessor notification materializes the private frontier bridge before segment dispatch. Side roots import that predecessor's completion, and the launch root follows it in queue order. A single root remains on the launch hardware queue; same-queue ordering is sufficient even if its generic bridge is published later. Do not generalize the multi-root bridge ordering to every single-root dispatch.

## Rejected intermediate revisions

V5/job 55635 exposed an unbraced multi-statement HIP_RETURN macro in the new destroy hook: it returned unconditionally and skipped release. V6 fixed the braces and passed finite-work tests in 55646. Its capacity path still waited on GPU completion, which could block a caller whose next action released that work. V7 removes that wait. No performance result is attributed to v5 or v6; the host-fed scenario was not run on v6.

## Identity and remaining work

- HIP SHA256: e692e09467765565866387bd4918468b1cbb43459c7c2c3fd2b1242031713ff0.
- HSA SHA256: 2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12.
- Candidate patch SHA256: a74278542225208a9bca02959d3d927031ad43e439a7ac08f431d74d00af57a3.
- Full patch SHA256: dc13347a5cd733ce35267af392b16bc3a84bf5e4456d21f1eee03a282f1eca0c.
- Source manifest SHA256: bd8d3de42c84685c4bf3445e19ccbe824dfbb44ad8704a86ac87094d893dca24.

Performance is a separate gate: unchanged Hassan stock/off/on job 55680 and frozen expert/KV stock/v4/v7off/v7on job 55683 completed with remote/local audits passing; see RESULTS-v7.md. No HiSparse, GLM or serving-application qualification transfers from these tests. Raw roots are preserved locally and under the corresponding /workspace/home/sasha/amd-runtime-production/iterations/hassan-graph-frontier-20260919 directory on the cluster.
