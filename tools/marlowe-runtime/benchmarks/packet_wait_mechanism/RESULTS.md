# Direct packet wait pilot — job 53220

The direct HSA pilot passed all 384 trials on one GPU of marlowe-mi355x-2 through the installed gpu-profile helper on 2026-09-18. It did not enable hardware counters. The exact effective, permitted and ambient capabilities were CAP_PERFMON only; mapped HSA SHA256 was b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4. No HIP runtime was loaded. This is a mechanism pilot, not a runtime performance qualification or evidence of a firmware bug.

## Controlled packets and measured tradeoff

Four HSA queues are created and reused. Producer and consumer start behind a common CPU-released gate. The consumer prefix is no dependency, ordinary Barrier-AND, empty Barrier-AND plus the same dependency, or the existing native WAIT_REG_MEM plus the same dependency. The ordinary dependency preserves the full signal condition and SYSTEM fences. The native prefix has no fences and no barrier bit. All kernel packets use SYSTEM fences and a barrier bit. Consequently these timings must not be transferred to captured AGENT-scope graphs.

Producer cases are initially-ready target, one 20 us kernel with a real completion signal, and 32/2048 serial timestamp kernels with a real final completion signal. Optional 256-kernel independent work and a fourth-queue readiness observer have matched off arms. Treatment order and two queue-role assignments rotate. Every trial waits for all participating final completion signals before reclaiming buffers/signals.

Below are medians of six retained trials per cell with observer and independent work both off, in microseconds. The sampled span is the later producer/consumer in-kernel end minus the first producer sample; it excludes trace stores and hardware completion and is not application latency. Each column is a separately computed median.

| Producer | Consumer prefix | Producer sample span | Consumer start after last producer sample | Joined sampled span |
| --- | --- | ---: | ---: | ---: |
| 20us kernel | Ordinary dependency | 20.08 | 11.79 | 35.11 |
| 20us kernel | Empty packet + dependency | 20.08 | 11.57 | 34.89 |
| 20us kernel | Native + dependency | 20.08 | 27.35 | 50.13 |
| 32 kernels | Ordinary dependency | 157.46 | 11.53 | 172.57 |
| 32 kernels | Empty packet + dependency | 157.98 | 11.07 | 172.65 |
| 32 kernels | Native + dependency | 138.44 | 27.77 | 170.63 |
| 2048 kernels | No consumer dependency | 9129.64 | Consumer may run early | 9129.64 |
| 2048 kernels | Ordinary dependency | 10400.68 | 11.23 | 10415.65 |
| 2048 kernels | Empty packet + dependency | 10401.66 | 12.15 | 10417.13 |
| 2048 kernels | Native + dependency | 9147.60 | 43.33 | 9193.61 |

The long-chain treatment reduces producer interference while increasing the subsequent consumer delay. The short producer has no comparable dispatch-chain saving and loses overall. The 32-kernel result is close and should not establish a threshold. An empty extra packet does not reproduce the native prefix's delay. This supports a benefit/cost architecture for native admission, rather than applying it to every dependency; it does not establish a general policy or explain the remaining expert/Hassan regressions.

The 2048-kernel sampled joined span improves in both queue assignments: ordinary/native 10411.75/9321.91us and 10417.11/9092.59us. These are two software-queue assignments, not verified command-processor hardware-pipe identities. Independent-queue results are retained in analysis.json and are mixed: improvement to the producer does not imply improvement to every other queue.

## Observer calibration and limits

The device reports a 100 MHz timestamp clock. The kernel uses S_MEMREALTIME and waits for the clock result. The observer places a system-scope 64-bit signal load between two clock reads, with vmcnt waits and buffer_inv sc0 sc1 in the emitted ISA. It has 144 valid last-nonzero/first-zero brackets and 48 initially-ready observations, which are left-censored. Typical brackets are 2.6–2.7us in this observer-on treatment. No valid dependency upper bound was negative.

Cross-queue/XCD clock skew has not been calibrated. The observer changes cache activity and scheduling; observer-off remains the primary comparison. Consumer start after the readiness bracket includes dependency handling, fences, dispatch admission and initial shader work. A roughly 40 us gap in an observer-on native arm is not a measurement of a firmware polling interval. The last producer timestamp precedes output trace stores and the hardware completion-signal update.

## Pilot correction and audit

Earlier job 53179 failed before GPU execution because hipcc --genco produced an offload bundle that was treated as ELF. Job 53189 also failed before GPU execution because its device target spelling was hipv4 rather than hip. Both are retained.

Job 53195 completed 51 trials before a GPU memory fault during the first delayed native case. Its instruction buffer used allocation flags 0, unlike the working cp_wait benchmark and production hostExecutableAlloc. Job 53220 adds HSA_AMD_MEMORY_POOL_EXECUTABLE_FLAG to that buffer plus untimed address/queue receipts. Buffer size/lifetime, packet bytes, signal kind and GPU source are unchanged. The new pilot passes; missing executable access is a supported correction, but the precise prior fault cause is not established, especially because 12 ready native trials passed with the older allocation. The old maps predated transient buffers and cannot establish whether the faulting page was mapped at fault time.

Local audit independently revalidated all 384 trials, 64 cells and 404 retained artifact hashes. A separate source/evidence review checked all allocation receipts, drained producer/consumer queues before subsequent publication, aligned pointers, and all observer brackets. Executable .text, kernel descriptor and metadata sections are identical across v3/v4 even though complete ELF hashes differ in symbol/string/hash sections. No further success-path lifetime blocker was identified.

Frozen source: iterations/packet-wait-mechanism-20260918/v4 under /home/sashawork/dev/amd-runtime-production, with remote mirror under /workspace/home/sasha/amd-runtime-production. Raw pilot-j53220 contains per-dispatch traces, trials.csv, addresses.csv, selected live maps, source/library/capability identities, ISA/metadata, analysis.json and receipt.json. The checked source files are included in this directory. Source hashes are recorded in SOURCE.json. Failed pilot artifacts remain in their original roots.

## Next counter pass

Reuse the existing device-wide collector from benchmarks/cp_wait_interleaved, with CPC_CPC_TCIU_BUSY and CPC_ME1_BUSY_FOR_PACKET_DECODE, each paired with CPC_ALWAYS_COUNT. Match the exact allocated KFD agent, verify counter dimensions and reject permission/degradation warnings. Use observer-off primary arms and interleave collection off/on within the same process and queues. Preserve a process without an initialized collector to detect profiler queue/configuration effects; no dispatch-counting interceptor. Window counts include gates, fences, submission and completion, so they cannot be called signal-address-specific transactions.

The earlier permission-qualified job 45006 already found sustained pending-AQL cache-interface activity and much less native activity. The new real-producer-completion pilot extends that evidence to handoff timing. Do not rerun old counter sweeps as though that evidence did not exist, and do not combine separate cohorts as a matched causal measurement.
