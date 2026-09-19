# Omitting CPU-proven satisfied Q/K barriers — job54925

2026-09-19, node2, one GPU, Slurm COMPLETED0:0 in16seconds. Remote and independent local audits pass288 retained timings,4500 numerical checks and38208 layer-readiness receipts. No runtime libraries changed. The original54847/54901 experiments remain immutable.

**Close the CPU-readiness architecture for this workload.** Removing barriers after actual CPU-observed completion improves that scheduler19.10%, but it still loses6.76% to whole-DAG prepublication and does not produce a true parallel win over the historical serial8.75–8.87us/pair. Do not port this scheduler, tune it further, or run full-model/holdout campaigns on it.

| Original g50 Q/K,200pairs/trial | Primary profiling-OFF us/pair |
|---|---:|
| Whole DAG prepublished |9.642178|
| Whole DAG + matched CPU observer |9.677539|
| CPU-ready publication, retain satisfied AND |12.723976|
| CPU-ready publication, omit satisfied AND |10.293689|
| K HIP replay, separate HIP-event timing boundary |10.386294|

The same-byte keep→omit comparison saves2.4302875us/pair, with round improvements−19.07%,−19.00%,−19.08%,−19.14%. Omission still loses0.651511us/pair to whole prepublication and0.616150us/pair to the observer control. Four predetermined rotated/reversed rounds each retain eight trials. All trials are kept; no CPU pinning or kernel modification. Do not subtract the keep value in prior54901 from this job: this is a new helper build/process/cohort, and only within-job keep→omit is causal. HIP reference and historical serial use different boundaries and are context, not matched direct-AQL performance claims. The contemporary direct-AQL controls alone reject the optimization as a net win.

## Why omission preserves the original graph

Both CPU-ready modes wait for BOTH real unique predecessor completion signals to reach0 and recheck both immediately before EACH next-lane publication. The CPU enforces the original full join; it never fabricates a ready signal or drops an unfinished dependency. Signal generations, graph, argument pools, tensors and code objects stay live through both final queue completions. The omitted AND is ordered NONE/NONE and supplies no memory fence. Every successor kernel retains its original barrier=1 and AGENT-acquire/AGENT-release scopes. Producers release their writes at the same HSA-agent scope before completion, and successors acquire at that scope; the CPU only observes completion and does not read producer data. This reasoning is limited to the reviewed same-agent kernel DAG, not cross-device, SDMA or unknown-scope operations.

Exact K source already implements this semantic shortcut: rocvirtual.cpp WaitingSignal685–711 skips completed external signals after signal_load_relaxed; ROC_CPU_WAIT_FOR_SIGNAL waits on CPU with acquire semantics and likewise does not append a GPU wait. dispatchBlockingWait emits no AND for an empty wait list. The diagnostic's acquire observations and retained unique signals are at least as strong. The existing option is not being promoted: this direct mechanism did not meet the performance goal.

All modes use400 unchanged original Q/K packets and400owned completion signals per trial. Modes0/1/2 retain199ANDs per lane and have401packets per lane including entry/exit. Mode3 first chunk remains entrySYSTEMacquire+kernel, later chunks contain the original kernel only, and the final chunk includes orderedSYSTEMrelease, for202packets per lane. Packet audit reconstructs every original byte except owned completion handles, verifies all scopes/geometry/code/kernargs, and proves that modes0/1/2 are byte-identical while mode3 removes only the199satisfied ANDs per lane. Both CPU-ready modes have identical active waits, rereads, CPU timestamp receipts, lane-order alternation, and live-work error handling. Every raw run checks all400completion values after BOTH finalSYSTEM exits before resetting anything.

Every retained raw trial has199 receipt rows. The38208 mode1/2/3 rows prove actual both-zero reads and action order; mode2/3 rows additionally prove contiguous per-layer indices, counts, capacity and final exit indices. Changed-input/poisoned-output and FP32 output checks pass for all four modes; original input bytes, AITER configs/sources, graph topology, immutable kernargs and mapped library hashes match the retained protocol. Kernel scopes and output lifetimes are preserved even though mode3 lacks cross-lane AND packets.

## Where time changed

| Profiling diagnostic | Whole DAG | +CPU observer | CPU-ready keep | CPU-ready omit |
|---|---:|---:|---:|---:|
| Profile-ON host us/pair |9.577327|9.738601|12.693715|10.274277|
| Profile-ON dispatch envelope us/pair |9.503365|9.675720|12.622617|10.204189|
| Profiled producer end → first successor packet start, median us |4.960|5.080|7.840|4.881|
| Profiled producer end → both successor packet starts, median us |5.120|5.240|8.320|5.3405|
| CPU both-zero observation → both publications/checks, median us |not observed|0.130|0.780|0.770|

Primary timing is CPU RAW gate release through both finalSYSTEM completion observations, and includes all CPU polls, copies and doorbells. Signal resets, initial publication and pending-gate hold occur before this boundary and are reported separately. Profiling changes primary latency by−0.67%,+0.63%,−0.24%,−0.19% respectively. CPU action intervals use RAW timestamps; HSA packet intervals use the common HSA system clock. No cross-domain subtraction is performed. All profiled dependency intervals are nonnegative.

A profiled dispatch end is not an independent observation of the instant its completion value becomes visible. Thus these intervals do not separately identify producer completion publication, consumer queue wakeup/recognition, fence cost or kernel dispatch cost. Omitting the satisfied AND causally improves the complete scheduler including packet supply/copy/handling; it is not a pure firmware-cost measurement. The host action time barely changes, while profiled handoff shrinks by about3us. It remains around5.3us and the complete scheduler still loses to prepublication.

The evidence now rules out native PM4 at these short joins, extra GPU-polling kernels, single-queue concurrency on this setup, and this CPU-readiness scheduler. It supports retaining the original two-queue behavior while narrowing the remaining device-side boundary with a concrete source/measurement hypothesis. It does not establish a firmware bug or a universal impossibility result. There is no newly qualified runtime and the large true-parallel Hassan speedup remains unsolved.

## Frozen evidence

- HIP0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4; HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4; unchanged K diagnostic libraries.
- Source manifest61aff43a7c065b253cf42dba5c7c39c0ed2672fafbaff7b94b3611a75bebbda5.
- Result manifest9964535c2a0cfa77c0e02c9cd175fa0e4a0522210a5775c1a3105c16a8c45298.
- Local:/home/sashawork/dev/amd-runtime-production/iterations/hassan-ready-omit-20260919/results-j54925.
- Remote:/workspace/home/sasha/amd-runtime-production/iterations/hassan-ready-omit-20260919/results-j54925.

The existing user-authorized Codex xhigh reviewer checked both semantic rationale and changed source before launch without blockers. Independent post-run review rehashed10 source,5 build and23 result entries and decoded all packets,288timings,4500numerical checks and38208readiness receipts without a blocker. Root owns the completed standalone monitor and local/remote audits. No active GPU allocation remains.
