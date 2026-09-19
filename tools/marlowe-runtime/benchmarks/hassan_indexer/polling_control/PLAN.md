# Stock Q/K graph-boundary and GPU-polling control

User-supplied independent reproduction: 2048-kernel producer 3179us baseline; one/two event waiters 5362/7137us vs GPU polling3391/3458us. This removes 90.29%/92.95% of event-wait excess, but is not a short-Q/K or full-model result.

Keep original Q/K BF16 GEMMs (M/N/K4/4096/2048 and4/128/6144), dispatch configs, input tensors/seed and fork/join every pair. All capture streams are prewarmed. Stock HIP f104…/HSA b8cd… only. Eight cases: unified serial/events graphs grouping1/50; split Q/K graphs serial, events, GPU polling, and identical stream-memory operations using CP wait. Every case uses the same C++ replay loop, so results are a separate launch protocol from Python replay results.

The split event vs GPU polling comparison keeps both graph boundaries, projection kernels and dependency topology identical. The only difference is event record/wait vs stream-memory write/wait. CP versus GPU polling keeps stream-memory API, signal allocation, counter protocol and writes identical; process-level GPU_STREAMOPS_CP_WAIT selects implementation. It is not pure waiter latency: both signaling and waiting cost are included. The stock source selects a one-work-item blit kernel for GPU polling and an AQL barrier-value packet for CP waiting; source pointers below.

Two 8-byte HIP signal-memory allocations are reused with increasing 32-bit generations, never approaching wrap. Main publishes ready, launches Q; side waits ready, launches K, publishes done; main waits done before the next pair. This preserves both directions and completion before reuse. Separate Q/K graph exec handles are kept alive through completion. Initial/changed/final FP32-reference checks and exact final signal-generation checks detect obvious stale publication/retirement; they are not exhaustive scheduler proof. No custom attention or polling kernel is inserted into the GEMMs.

Eight short untimed proofs enable only runtime copy logs and require exact GPU-wait receipts (8 for split-poll, zero CP receipts). Four reversed timing orders, eight retained trials/process, 200 pairs/trial;32 timing processes. Report raw medians, per-order medians, GPU elapsed, CPU submission and host total. No filtering, CPU pinning, full-model run or claimed firmware bug. Favorable polling results need a subsequent wave timeline to prove useful overlap; unfavorable broken-graph results do not disprove polling inside a better runtime.

Root owns standalone one-GPU node2 job. Expected3–6min, inspect queue/startup after3min, no progress after2min, running after8min; inspection does not cancel or relaunch. Slurm safety limit15min. Separate from candidate54155, with distinct output root/receipt. Kernel shapes/splitK are not tuned.

https://github.com/ROCm/clr/blob/rocm-7.2.4/rocclr/device/rocm/rocvirtual.cpp#L3169
https://github.com/ROCm/llvm-project/blob/rocm-7.2.4/amd/device-libs/opencl/src/misc/amdblit.cl#L732
