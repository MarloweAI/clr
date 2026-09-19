# Same-queue parallelism capability — jobs 54716 and 54739

2026-09-19, node2, one GPU per sequential job. Both Slurm jobs completed 0:0 and passed independent remote/local correctness and artifact audits. No HIP runtime is loaded and no runtime candidate was built or promoted.

**Decision: close the proposed one-AQL-queue parallel-layer implementation for this setup.** Kernel dispatches did not overlap on one queue, even with both barrier bits and every per-kernel fence removed. Identical probe machine code overlapped in all 16 two-queue controls. This is a necessary-capability failure before a runtime port, not a new Hassan performance regression. It does not prove a universal HSA limitation or identify a firmware bug.

The first pilot 54716 co-published independent kernel pairs (barrier bits 1/0), followed by an ordered empty Barrier-AND. Kernel scopes were SYSTEM/SYSTEM. Neither the one-block nor the 256/24-block configuration overlapped in any of 72 parallel layers per geometry. Serial controls were also0/72. All 8-layer dependency, full-capacity, wrap and lifetime checks passed. Because captured Q/K kernels normally carry AGENT/AGENT scopes, this negative alone was insufficient to reject the architecture.

Follow-up 54739 isolates scopes and the first barrier bit. Every same-queue sequence begins with an ordered SYSTEM-acquire/NONE-release entry barrier and ends with an ordered NONE-acquire/SYSTEM-release barrier owning the sole completion. Independent kernels have no completion signals. All packets are co-published once, with the first header held INVALID until all bodies/later headers are written, then one release header publication and one terminal doorbell. Thus the NONE-scope controls preserve host input publication and final output lifetime.

| Configuration | One-block kernels: overlap / trials | Q256/K24 geometry: overlap / trials |
|---|---:|---:|
| First release × second acquire: SYSTEM/AGENT/NONE, nine cells, barriers 1/0 | 0 / 72 | 0 / 72 |
| Exact AGENT/AGENT kernels, barriers 1/0 | 0 / 8 | 0 / 8 |
| Exact NONE/NONE kernels, barriers 1/0 | 0 / 8 | 0 / 8 |
| SYSTEM/SYSTEM kernels, barriers 0/0 | 0 / 8 | 0 / 8 |
| AGENT/AGENT kernels, barriers 0/0 | 0 / 8 | 0 / 8 |
| NONE/NONE kernels, barriers 0/0 | 0 / 8 | 0 / 8 |
| Serial controls, SYSTEM or NONE, barriers 1/1 | 0 / 16 | 0 / 16 |
| Two distinct AQL queues, SYSTEM/SYSTEM, shared entry gate | **8 / 8** | **8 / 8** |

Each of the 17 configurations has four reversed rounds and both kernel publication orders, for 272 retained trials. For the primary nine-cell grid only the first kernel release and second kernel acquire change; the outer acquire/release remain SYSTEM. Two-queue controls publish/ring both queues while their entry barriers wait on a shared CPU-controlled signal, then release that gate. Both final completions are waited before data is read or freed. This removes CPU publication skew as an explanation for the control.

Overlap is established by a bounded bilateral GPU rendezvous: each kernel's block 0 publishes its own fresh epoch and must observe its peer before a 1 ms GPU deadline. Both succeeding proves overlapping live kernel progress, without comparing clocks on different XCDs. The serialized first kernel must time out; every serial control does. Per-block timestamps are retained as diagnostics only. Reversing kernels and 1.5/2 ms durations prevents a favorable single ordering from determining the result.

The large geometry uses 256 and 24 workgroups, 128 threads per group, and 61,440 dynamic LDS bytes per group; the minimal case uses one workgroup each and 512 LDS bytes. These match the important Q/K block/LDS reservations but do NOT execute Hassan's MFMA/memory workload. The long durations create an easy opportunity for concurrency and are not application latency measurements. No original Q/K speedup or HiSparse result is claimed.

Correctness covers all workgroups: each block release-increments its role's completion count after its final block synchronization; every block of each following layer acquire-checks both complete producer counts and values. Host checks every final count/value after the ordered system completion. Pilot54716 has 64 trials and 40,608 per-block checks; follow-up 54739 has 272 trials and 38,352 checks. Both retain exact packet bytes, raw GPU records, maps, code metadata/ISA, source hashes and receipts. The follow-up's positive-control status is separate from correctness; both pass. The original pilot's explicit CAPABILITY_FAIL receipt remains unchanged.

The GPU source and executable .text are identical across the two jobs (SHA256 d0361c6f07fe58d680ad4bdce927e1701cda2291922b7858c9bed46b826d3938). Full code-object hashes differ only through symbol/string/hash sections, which is documented in KERNEL_IDENTITY.json. Actual mapped HSA is b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4, with no mapped libamdhip64. No performance-counter helper or CPU pinning is used.

Prelaunch review used the user-authorized Codex xhigh fallback. It identified and fixed separate capability status, whole-workgroup joins, production-relevant AGENT 0/0 controls and the gated two-queue control. First-invalid publication, barrier semantics, and all live-work error/lifetime paths were checked. Unexpected second-queue publication failure exits without freeing live storage. Review supplied the primary [HSA System Architecture 1.2 specification](https://hsafoundation.com/wp-content/uploads/2021/02/HSA-SysArch-1.2.pdf): the barrier bit permits out-of-order launch, but does not require useful concurrent hardware scheduling.

The evidence supports continuing with distinct AQL queues on this tested MI355X/HSA stack and reducing their handoff cost. It eliminates a tempting architectural shortcut before spending effort porting it. In particular, do not weaken production fences or claim that coalescing logical streams creates physical concurrency. The earlier Hassan results still stand: stock has useful two-queue overlap, but its repeated join/dispatch interval consumes the benefit; GPU polling helps the long-producer and split-graph cases but regresses frequent joins inside the unified Q/K graph.

Frozen reproducer sources are under same_queue_probe/pilot and same_queue_probe/fence_probe. Their launchers refer to the retained workspace paths. Reproducing elsewhere requires an explicitly new source manifest and output root; never overwrite the original hashes/artifacts.

Identities and raw roots:

- Pilot source manifest 5b7f875ad3508c099016c284837937dfa3a519dbf2677ed85e3116fdc662f825; result receipt 3bc6ab75cfa59d598c0ba60d5108c388dd98d29fa04fb1c0561c3e756348475f.
- Follow-up source manifest b94770b37d7e33775705a41cada17ef0c30b988e9b2583885da8788d6a73fc94; result receipt 6b3f81dfa65ad215d4dcce351516c0448548b5606bf3f14e33a8b65f09056349.
- Local roots: /home/sashawork/dev/amd-runtime-production/iterations/hassan-same-queue-20260919/{pilot/results-j54716,fence_probe/results-j54739}.
- Remote mirror: the same suffix under /workspace/home/sasha/amd-runtime-production/iterations/hassan-same-queue-20260919.
