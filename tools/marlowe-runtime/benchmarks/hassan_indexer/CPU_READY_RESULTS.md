# CPU-observed readiness before original Q/K publication — job54901

2026-09-19, node2, one GPU. Slurm completed0:0; standalone root monitor and independent local artifact audit pass224 retained timing trials,3500 numerical checks, and25472 layer-readiness receipts. No runtime library was changed. The original54847 results remain immutable.

**Reject this CPU-ready scheduler with retained ANDs.** It preserves the original graph but makes the grouped Q/K workload26.25% slower than the matched CPU-observer control. Polling completion signals alone is neutral in the primary profiling-OFF measurement. The user goal of substantial true parallel speedup is not achieved.

| Same original g50 graph,200 Q/K pairs per trial | Profiling-OFF us/pair | Change vs whole-DAG publication |
|---|---:|---:|
| Both complete lanes prepublished |9.643254|reference|
| Same packets prepublished, plus matched CPU observer |9.638229|−0.052%|
| CPU waits for both actual producer completions, then publishes next layer |12.168580|+26.19%|
| K HIP graph replay, separate HIP-event timing boundary |10.329190|context only|

Primary timing is CLOCK_MONOTONIC_RAW immediately before CPU entry-gate release through acquire observations of BOTH final SYSTEM-release completions. It includes every CPU wait, per-layer packet publication, and doorbell in the scheduler mode. Four fixed rotated/reversed rounds each retain eight trials per cell; timing cells also include profilingON calibration and the K HIP reference. Scheduler-vs-observer regressions are+26.58%,+26.05%,+26.34%,+26.33% across the four rounds. All trials are retained. The HIP reference changes the timing boundary, publication and command ownership and is not a matched causal comparison.

All three modes have byte-identical flattened401-packet sequences per lane: common pending entry gate,200 original kernels,199 ordinary ordered NONE/NONE cross-lane ANDs, and an ordered SYSTEM-release exit. Each kernel keeps original AGENT/AGENT scopes, its ordered bit, kernel object, argument address, geometry and61,440LDSbytes. The unchanged AITER/FlyDSL dispatches, scheduler, input bytes and warm capture protocol match54847 and historical K54286. No native PM4 packet is present.

The scheduler publishes only entry+first kernel before gate release. For each following pair, it actively waits for both unique predecessor completion signals to reach0, checks both again immediately before EACH lane's publication, then supplies the original AND+kernel. It alternates lane order by layer and trial. The final chunk adds the exit packet. GPU dependencies/fences are retained; CPU readiness is an extra scheduling condition. The observer control performs the same active waits, duplicate both-zero reads, three CPU timestamp records and lane order while the entire graph is already published. It therefore checks whether observation itself changes signal visibility/recognition. Its spin-iteration count naturally follows progress and need not equal the dynamically fed mode's count.

The audit proves all six mode/lane packet blobs are identical,400unique signals complete on every raw trial, every retained raw trial has199 receipt records, observer/ready modes have actual ordered both-zero observations, and CPU-ready mode has exact contiguous indices/counts/capacity for every layer and final exit. All required output phases pass FP32 normalized-error screens, including changed inputs with poisoned outputs for every mode. Graph/kernargs/tensors/modules remain alive until both queues drain and are destroyed; signal generations are never reset early. Post-publication failures exit without reclaiming live GPU storage. No CPU affinity change or full-model run.

## Timing detail and interpretation

| Profiling diagnostic | Whole DAG | Whole DAG + CPU observer | CPU-ready publication |
|---|---:|---:|---:|
| Profile-ON host us/pair |9.477313|9.684353|12.159779|
| Profile-ON dispatch envelope us/pair |9.412710|9.616065|12.092199|
| Producer-ready → first successor packet start, median us |4.880|5.040|7.240|
| Producer-ready → both successor packet starts, median us |5.040|5.200|7.720|
| CPU both-zero observation → first action, median us |not observed|0.060|0.290|
| CPU both-zero observation → both actions, median us |not observed|0.130|0.770|

CPU actions are signal checks in the observer and completed packet publication/doorbell operations in the scheduler. These use one CPU RAW clock. GPU intervals use HSA dispatch profiling in the common HSA system clock; no CPU timestamp is subtracted from an HSA timestamp. The profiling-OFF endpoint is primary. Profiling changes latency by−1.72%,+0.48%,−0.07% respectively, so small differences in the profile controls must not replace the neutral profiling-OFF observer result. All profiled dependency intervals are nonnegative.

The extra CPU publication work costs about0.77us after actual readiness is observed, but that is not an isolated end-to-end component attribution: completion visibility, queue occupancy, packet supply timing, CP lookahead and repeated doorbells also differ. The decisive result is the complete measured cost, which is worse. Reject this scheduler without concluding that pending-barrier handling itself costszero or identifying a firmware defect. The earlier bare replay still places the repeated roughly5us interval after all CPU submission has finished; moving publication into a per-layer CPU loop does not remove it cheaply here.

## Frozen evidence

- HIP0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4; HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4. These are unchanged K diagnostic libraries, not a production-qualified candidate.
- Source manifest238bf46c5c9a0096b66cf57c0d090c2a7ee09eca47d39dad2ba75f7a0c4a610e.
- Result manifestbd467bce53f2822a4943f087d10f06adcbdf0f1cf7604f23520e42172c4ffbe5.
- Local:/home/sashawork/dev/amd-runtime-production/iterations/hassan-cpu-ready-20260919/results-j54901.
- Remote:/workspace/home/sasha/amd-runtime-production/iterations/hassan-cpu-ready-20260919/results-j54901.

Prelaunch review by the user-authorized existing Codex xhigh reviewer found no correctness/timing/lifetime blocker. Root mirrored and re-audited all retained artifacts after successful remote audit. Independent post-run review also rehashed the10 source,5 build and21 result entries and rechecked all packets,224 timings,192 readiness traces,96 profile arrays,3500 numerical checks and25472 readiness receipts without a blocker. No active allocation remains. No runtime port or broad holdout campaign is justified by these numbers.
