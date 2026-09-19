# Prelaunch review

Reviewed by existing Codex xhigh same_queue_pilot_review agent, 2026-09-19. No launch-blocking issue. Common SYSTEM-acquire gate, reset dispatch SYSTEM/SYSTEM, ordinary reset_done and ordered SYSTEM-acquire waits dominate both unchanged Q/K lanes. Final SYSTEM-release exits and queue retirement precede internal signal loads, profiling and destruction. Captured helper graph, module, kernargs and device pointer table stay alive. Explicit eager/captured poison-and-reset fixtures plus exact final-zero/numerical checks cover stale resets. total_us includes CPU ordinary resets, publication, GPU reset/waits, Q/K and host exits; post-drain inspection stays outside.

Causal comparison is m1/m2: matched implementation with different backing addresses and memory path. m0 has CPU reset and fewer packets, so is a practical ordinary reference rather than a matched placement control.

Integration recommendation: separate GraphExec-owned per-inflight GPU dependency tokens from ordinary host retirement. Existing ExternalSignal/WaitingSignal/native-wait paths CPU-load signals and must not carry local tokens. Direct ordered AND packets can consume generation-owned tokens; ordinary per-lane and final callback completions retain CPU lifetime ownership. No generic HwQueueTracker relocation. No application/shape-specific eligibility.

## Independent post-run audit

Job55130 passed the existing xhigh review. The reviewer reran the frozen audit and independently recomputed raw rows and artifact bindings:231 timings/3528 numerical checks,224 grouped rows,96 grouped profile traces,39 queue wraps. Every matched primary trial favors local; exact total=sum(prepare,publish,gate,latency) within floating-point rounding. All packet/reset/table/placement/lifetime checks pass. The main limitation is one reset/final envelope per200 direct pairs versus four50-pair HIP launches. No unchanged-HIP, serial, small-graph or production claim follows yet.
