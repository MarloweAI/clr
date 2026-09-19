# Profiling method and current evidence

As of 2026-09-18, causal runtime controls and end-to-end timing are established. Device-side sampling is calibrated on Hassan Q/K. A complete attribution of runtime time to individual CPU phases and GPU packet/dependency stalls is not established.

## Measure the critical path, not an additive overhead total

Host submission, command processing, kernels and transfers overlap. CPU submission time plus GPU execution time is not application latency. Likewise, graph elapsed minus summed kernel durations is not runtime overhead: kernels overlap, instrumentation misses entry/exit work, and host arrival can leave the device idle.

| Layer | Current measurement | Interpretation and limit |
| --- | --- | --- |
| Application completion | Monotonic host clock through final synchronization | User-visible span, including host, GPU, waits and measurement operations |
| CPU submission | Host clock around repeated eager calls or graph replay | Includes Python/framework bindings and runtime; not isolated C++ runtime CPU cost |
| Device span | Timing events surrounding the fully joined workload | Includes dispatch starvation and dependencies, not just kernel instructions |
| Inside kernels | Separate diagnostic copies with per-wave fixed-frequency samples | Execution ordering/envelopes, subject to code-generation and recording perturbations |
| Runtime structure | Untimed queue/segment/native-policy receipts and counters | Proves paths, mapping and emission; does not measure GPU stall duration |
| Runtime interventions | Frozen binary, independent controls, unchanged workload | Causal effect of the changed behavior, which can include multiple CPU/GPU mechanisms |

Performance runs keep verbose runtime tracing off. Structural checks and instrumented runs are separate. Some profiler modes explicitly disable optimized graph paths, so a profiler result requires verification that it observes the intended implementation.

## Controlled experiment sequence

1. Freeze exact kernels, inputs, topology, runtime and dependencies. Verify mapped library hashes, not just environment requests. Retain every trial and distinguish data-audit success from performance acceptance.
2. Write the hypothesis and expected distinguishing observation. Use same-binary controls for attribution and stock plus a rebuild-off arm where appropriate. Rotate process order and inspect per-round results.
3. Check correctness under changed inputs, required dependencies, stream reuse, update/invalidation, completion and object lifetime before accepting timing.
4. Calibrate observations: original kernel, instrumented kernel with recording off, then identical instrumented bytes with recording on. Inspect generated ISA, register/LDS/scratch use and timestamp endpoint semantics.
5. Use the measured schedule to select a concrete intervention; retest original uninstrumented kernels. Carry promising candidates to workloads that should retain useful parallelism before proposing a general policy.

## What direct GPU samples have established

The [Hassan calibration](benchmarks/hassan_indexer/TIMESTAMP_RESULTS.md) uses one recording lane per wave, separate Q/K buffers and no cross-stream logging counter or extra CTA barrier. The 100 MHz device clock gives 10 ns tick granularity, not 10 ns attribution accuracy. End samples include probe-induced waits and omit subsequent trace stores and retirement.

Recording adds about 0.69 us under stock/events and 0.98 us under current/events. Disabled instrumentation also changes generated code. Therefore a constant subtraction cannot recover uninstrumented timings. Generated resource checks show no change in the SDK occupancy ceiling; they do not measure actual concurrent occupancy.

In the sampled 200-replay burst, stock K advances far ahead of Q while the current runtime aligns corresponding Q/K invocations. That supports investigating dependency/placement structure. It does not explain the expert benchmark, which synchronizes around a single replay, or establish a HiSparse mechanism.

The [subsequent uninstrumented intervention](benchmarks/hassan_indexer/SHARED_RETIREMENT_RESULTS.md) changes graph mapping and completion bookkeeping while preserving original kernels. It improves Hassan from 22.186 to 19.108 us; contemporaneous stock is 19.903 us. Conditional same-binary effects are 2.011 us for logical coalescing and 1.067 us for shared retirement. The latter bundles CPU command lifetime, completion signaling, barriers and submission pacing; it is not a measured allocator-only cost.

## Hardware-counter access and actual use

The [Slurm gpu-profile helper](https://github.com/MarloweAI/slurm/pull/5) is installed for sasha on node2. It grants CAP_PERFMON to a Slurm GPU step; it does not collect counters automatically. Invoke it from a host-side srun step without Pyxis container flags. It is useful for targeted device-wide counter experiments with matched unprofiled controls, rather than enabling collection in every performance run.

Job 45006 on September 16 used that route for 14,160 validated checks with no counter permission warnings. In its 8 ms waiting-only window, ordinary pending AQL produced 1,233,208 summed CPC cache-interface counts versus 56,664 for ordinary native prewait plus the original dependency. AQL counts increased approximately with wait duration while its packet-decode counts stayed nearly constant. This supports a sustained polling/access-path contribution to interference; it does not establish bandwidth saturation, a particular firmware loop or address-specific traffic. Counts are summed event records, not bytes or utilization percentages. The report and matched counter-on/off controls are retained under amd-runtime-production/results/cp-wait-profile-45006.

The recent Hassan timing/timestamp runs did not use this helper or collect those counters. The [new direct packet pilot](benchmarks/packet_wait_mechanism/RESULTS.md), job 53220, uses the helper and passes 384 trials with counters disabled. It extends the older CPU-released-signal experiment to real producer completion and shows both reduced long-chain interference and a larger consumer handoff delay. Next collection should use the existing device-wide collector, match the assigned KFD agent, quantify off/on perturbation and avoid dispatch-profiler modes that change the runtime path. Neither this helper nor these counters provide a firmware instruction trace.

## Missing measurements and next instrumentation

The missing host decomposition should use optional, sampled, preallocated per-thread records around graph planning, command allocation, dependency construction, signal acquisition, packet reservation/publication, notification and completion handling. Record nested/inclusive versus exclusive time, thread and graph identifiers, and relevant counts. Calibrate recording off/on and avoid formatting, file I/O or shared logging locks in measured paths. This is planned instrumentation, not a completed measurement.

Collect packet, barrier, signal, allocation and notification counts alongside those phases. Counts demonstrate work volume; they do not directly give device stall time. Targeted device completion timestamps and calibrated kernel samples can constrain the remaining critical path. Preserve unexplained time explicitly until an intervention and corroborating measurements identify it. Unchanged total CPU submission does not rule out a change in packet arrival timing.

## Where the changes execute

The current changes are C++ in CLR's HIP graph code and ROCclr queue backend. CMake with ROCm clang/clang++ builds a Release CPU shared library, libamdhip64.so, loaded into the application process. ROCr/libhsa-runtime64.so is another host user-space library; its bytes are fixed across these cohorts. These are not a new kernel driver or GPU firmware image.

CPU runtime code chooses queues and dependencies and publishes AQL/PM4 command packets. Existing GPU command-processing machinery consumes those packets; compute units execute separately compiled attention kernels. The native-wait code constructs a WAIT_REG_MEM packet on the CPU whose wait operation occurs on the device, followed by the original AQL dependency that retains full condition/fence/notification semantics. Changing a CPU library can therefore change both CPU work and GPU scheduling without changing attention kernels.
