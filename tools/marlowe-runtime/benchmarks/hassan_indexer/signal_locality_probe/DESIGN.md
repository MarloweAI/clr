# Signal locality diagnostic

This tests one specific lower-layer hypothesis for Hassan's original warmed Q/K graph: CP completion and barrier traffic to host memory contributes materially to the handoff interval. It is not a scheduler-policy sweep or a production candidate.

The prior direct packet experiment prepublished the complete original dependency DAG and still had roughly 5 microseconds between profiled dispatch end and the next pair starting. End is not an independently observed completion-publication timestamp. Original Q/K already overlap; making the completion path cheaper is the opportunity.

## Mechanism and scope

Pinned ROCr source 97f5574fe2fdc7bef44fb01545347912ee9f1779 allocates DefaultSignal's SharedSignal in CPU fine-grained memory. GPU_ONLY changes the signal implementation, not its placement. This private ROCr build adds two reserved diagnostic attributes to hsa_amd_signal_create: bit63 selects the diagnostic owner, bit62 selects GPU-local placement. The normal API behavior is unchanged when those bits are absent. Both controls create a real SharedSignal and BusyWaitSignal object, with identical 4KiB dedicated allocation, flags, alignment, guard words and lifetime. GPU mode requires the selected local fine region to be FRAME_BUFFER_PUBLIC.

This is private implementation behavior, not a portable public-HSA placement API. Pinned MemoryRegion sets HostAccess on public framebuffer memory and the KFD path maps it into CPU VA. That supports nonconcurrent ordinary CPU loads/stores. It does not support CPU atomic RMW across PCIe. Therefore the private owner skips Signal's usual destruction CAS, failing closed if host waiters or retained async owners exist. Every ordinary signal retains its original destruction behavior. The harness never performs CPU RMW, waits, IPC exports or async registration on internal diagnostic signals.

## Matched experiment

One GPU on node2. Three internal-signal modes share the same two HSA queues and identical packet sequences: normal pooled GPU_ONLY host signals; private dedicated host-page signals; identical private GPU-local-page signals. Host-page versus local-page is the placement contrast. Pooled versus dedicated host is a required control for page layout/object changes.

Entry gate and two final host retirement signals remain standard IPC signals. Original Q/K kernel objects, arguments, input hashes, dimensions, splitK, AGENT fences, ordered bits, dependency DAG and both final SYSTEM exits are unchanged. Each full run prepublishes 400 original dispatches and 398 cross-queue AND packets. No host internal-signal observation occurs during the primary gate-release-to-both-final-exits interval.

All signals reset only after both queues drain. SFENCE plus readback of every initialized value precedes packet publication. Both final exits and both queue read indices must retire before signal-zero/guard/profiling readback, reuse or destruction. Live-work errors exit without unwinding live storage. Pointer receipts verify fine-grain flags, host/agent base equality, actual owner and allocation extent. Host/local extents must match.

A short original g1/two-pair correctness pilot precedes the g50/200-pair run. FP32 reference checks include poisoned outputs and changed/restored inputs. Four rotated rounds retain eight trials per cell, with profiling-off primary and separate profiling-on diagnostics. The whole graph, tensors, code modules and kernargs remain live. These are real HSA objects, so post-drain profiling APIs are valid; their dispatch-end stamps still do not independently establish signal-ready time.

A placement win would justify a capability-gated runtime internal completion allocator with host-visible final retirement. It would still require application-transparent HIP integration and a matched original serial/two-stream comparison. A negative result rejects this specific allocation policy; it cannot prove all signal locations/cache/TLB policies equivalent. No broad microbenchmarks or model jobs until a useful true-parallel Hassan candidate exists.
