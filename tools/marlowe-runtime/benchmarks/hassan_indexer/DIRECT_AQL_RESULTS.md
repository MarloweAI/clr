# Exact original Q/K packets on two AQL queues — job 54847

2026-09-19, node2, one GPU, Slurm COMPLETED0:0 in15seconds. Remote and independent local artifact audits pass320 retained trials and2550 numerical checks. Original K runtime bytes were used only to capture the original graph and provide a contemporaneous HIP reference. No runtime was changed, deployed, or promoted.

**Reject native PM4 prefixes at the short internal Q/K joins.** They make the exact grouped replay4.468x slower than ordinary AND joins, with the original kernels, memory, dependencies and scopes retained. Bare two-queue replay exposes only modest grouped headroom after host submission is removed from the measured execution interval. The requested large parallel speedup remains unsolved.

| Original graph grouping | K HIP replay reference, GPU us/pair | Private replay, ordinary AND, us/pair | Private replay, native prefix + same AND, us/pair | Causal native effect |
|---|---:|---:|---:|---:|
| One pair, repeated200 times |16.672399|10.054776|10.052266|−0.025%; identical-packet control |
|50 pairs, repeated4 times |10.272939|9.625889|43.009760|**+346.81%** |

Private replay numbers are profiling-OFF CPU gate release through acquire observation of BOTH final SYSTEM-release completions, divided by200pairs. HIP reference is a C++ hipGraphLaunch loop with HIP-event timing; its timing boundary and command ownership differ. Thus private-vs-HIP is headroom context, not a matched causal subtraction or attribution to IRQs. The apparent gaps are6.617623us/pair for g1 and0.647050us/pair for g50, roughly39.69% and6.30% of the respective HIP reference. This does not bound every possible runtime architecture. Historical warm stock serial is about8.75–8.87us/pair under its recorded HIP protocol; the direct grouped result does not establish a win over that baseline.

The native regression repeats in all four reversed/rotated rounds: +349.36%,+337.82%,+344.48%,+350.32%. The identical-packet g1 control varies by only−0.129% to+0.126% per round. All fixed trials are retained. No CPU pinning, full-model run, or gap/outlier deletion was used.

## What remains on the device

The profiling pass uses HSA dispatch timestamps in the common system clock domain. It measures packet-processing intervals, not independently instrumented kernel execution. Profiling changes host latency by−0.75% for bare g50 and+0.10% for native g50, so it does not explain the large difference. All producer-to-dependent-start intervals are nonnegative.

| Grouped replay diagnostic | Ordinary AND | Native + same AND |
|---|---:|---:|
| Profile-ON host time, us/pair |9.553353|43.052798|
| Profile-ON dispatch envelope, us/pair |9.483513|42.981715|
| Median producer-ready → first next packet start, internal joins, us |4.921|8.401|
| Median producer-ready → both next packet starts, internal joins, us |5.120|41.242|
| Median producer-ready → both next packet starts, ordinary graph-boundary joins, us |5.120|5.200|

Timing columns use medians of the four round medians. Gap columns pool the6,272 internal and96 replay-boundary intervals per mode from the profiling traces. The internal gap is computed from the later of the two producer end timestamps to the first/both next dispatch start timestamps. Native prefixes appear only on the49 internal boundaries per50-pair graph, not on the three boundaries between replays. Those untreated boundaries remain around5.2us, while treated internal joins grow to41.2us for both successors. This is consistent with the causal timing result and localizes the slowdown to the native internal treatment. The median dispatch-interval overlap is4.28us with ordinary joins and0 with native prefixes; this is a dispatch-profile observation, not a new calibrated proof of exact kernel overlap.

Every packet for both lanes was already published before the common CPU entry gate was released. Consequently ongoing CPU submission cannot account for the repeated internal5us intervals in this diagnostic. Device-side packet scheduling, dependency recognition and fence processing remain candidates. This does not identify which component is responsible, nor establish a firmware bug. Changing host retirement alone is not supported as the route to a large grouped speedup by this result.

The user-supplied independent long-producer result remains valid:3.179ms without waiters,5.362/7.137ms with one/two event waiters,3.391/3.458ms with GPU polling. It removes90.29%/92.95% of the added penalty there. Earlier split-graph Q/K polling also helped its matched split-event baseline30.263→20.993us/pair, while remaining worse than unified events14.254us/pair. Protecting a long producer from waiter interference and cheaply resuming at frequent short joins are different performance requirements. None of these results establishes a full-model polling win.

## Preservation, audit and timing

The original AITER/FlyDSL Q/K kernels, exact configs/splitK, deterministic BF16 input bytes, graph scheduler and warmed capture stream are unchanged. Q is4x4096x2048, K4x128x6144. Read-only extraction is compiled with the exact K internal headers and compile flags. The executable graph's cloned nodes are reconstructed into two-root, fullyjoined layers. Copies retain all64packet bytes except owned completion handles, with original AGENT/AGENT scopes, ordered bits, grid, workgroup, code object, kernargs and61,440LDSbytes. Runtime graph templates are never submitted or mutated by the private queues.

Both modes use398 ordered NONE/NONE cross-lane ANDs per400-kernel trial. Local order supplies the other predecessor. g50 native adds392 PM4 prefixes; g1 adds none and its mode blobs are byte-identical. Joins between graph replays are conservatively preserved; their synthetic direct-AQL representation is not byte-for-byte HIP graph entry/final markers. All400unique IPC completion signals must reach zero on every raw replay. The two4096slot queues fit the whole DAG, use one first-invalid co-publication per lane, and have distinct final SYSTEM-release completions. Capacity, invalid slots, instruction encoding/executable allocation, scopes, dependencies, distinct queue IDs and observed wrapping are audited. No signal is reset before both consuming queues drain. Any error after publication exits without freeing live GPU memory.

The common pending CPU gate gives both queues time to receive all packets before timing. Signal resets, publication, and the200us requested gate hold are outside the primary timing boundary and reported separately. Median total preparation+publication is about10us per200pair trial, not per pair. Gate sleep overshoot is retained. Queue publication order alternates; four predetermined reversed/rotated cell orders each retain eight trials. HSA profiling is a separate ON/OFF factor, with each timestamp queried before signal reuse. HIP profiling or logging is not enabled inside the primary raw trials.

Every output is checked against FP32 after capture, after changed inputs with poisoned outputs for each mode, after input restoration, and after each timing cell. Original data hashes match retained K job54286; graph kernarg bytes are unchanged after all replay modes. Mapped HIP/HSA hashes are checked before AITER import, after capture and after timing. Graph, GraphExec, all arguments, code modules and tensors remain alive through private queue destruction. The user-authorized Codex xhigh fallback reviewed the source before launch with no remaining blockers, then independently rehashed the10 source,5 build and38 result inventory entries and rechecked packets,320 timings,2,550 numerical checks and128 profile traces. No post-run blocker was found.

## Frozen identities and decision

- HIP:0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4; unchanged K diagnostic, not production-qualified.
- HSA:b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4.
- Source manifest:6914a52689b49de36786a7e1d678b246060c5d214ea8456e8b766449763e580d.
- Result manifest:99b6db77de6542ac3f9dc06f3474fc71646362af2b7ff8c060bbb466d76f922f.
- Raw local:/home/sashawork/dev/amd-runtime-production/iterations/hassan-direct-aql-20260919/results-j54847.
- Raw remote:/workspace/home/sasha/amd-runtime-production/iterations/hassan-direct-aql-20260919/results-j54847.

Close the native-at-every-short-internal-join hypothesis. Do not relax the production admission guard based on long-producer polling results. Do not implement invasive host-lifetime changes merely to explain this remaining gap. A subsequent experiment must distinguish specific device packet costs, with a matched ready/pending or no-dependency control that preserves its claimed semantics; no firmware attribution or runtime promotion is justified yet. The goal of a substantial true-parallel Hassan runtime win remains open.
