# GPU-local completion signals — job 55065

**Moving the internal completion signals to GPU-local memory reduced the fully prepublished original Q/K execution interval by 25.81% versus matched host-page storage.** All four rotated rounds improve by 25.72–25.85%; all 32 local primary trials are faster than every matched host-page primary trial. An independent Codex xhigh post-run source/artifact audit passes. This is a causal storage-placement result and a new architectural lead. It is not yet a HIP/PyTorch runtime speedup: the diagnostic's costly CPU initialization/readback/guard verification is outside the primary execution interval, and application-transparent integration is not implemented.

One GPU on node2; Slurm COMPLETED 0:0. The short original-kernel correctness pilot preceded the grouped run. All 231 timing rows and 3,528 numerical checks are retained and pass remote and local audits. Seven pilot rows are capability checks, not performance estimates; the main table uses 224 grouped rows, including 32 trials per cell over four rounds. No model job or other benchmark was run.

| Internal completion storage | Primary execution µs/pair, profiling off | Change vs matched host-page control | Profiled previous-pair end → both next dispatch starts, µs |
|---|---:|---:|---:|
| Normal pooled host GPU_ONLY signals, rebuilt ROCr | 9.653228 | — | 5.12 |
| Private dedicated host pages | 9.734463 | reference | 5.16 |
| Identical private GPU-local pages | **7.222479** | **−25.805%** | **2.56** |

The dedicated-host control is 0.842% slower than the rebuilt normal pooled-host control. Local placement saves 2.511984 µs/pair against its matched host-page control and is 25.181% faster than the pooled control. Both placements use the same private signal class, actual 4096-byte allocation extents, flags, alignment, lifecycle and packet topology. The intentional treatment is the selected backing memory region; address, physical placement, and consequent memory-system path differ. These are three modes of identical rebuilt ROCr bytes; the pooled row is not the installed stock binary.

The ordinary HIP replay reference in this run is 10.384889 µs/pair. Its timing/submission boundary differs from fully prepublished direct replay, so it is not the causal denominator above. Historical serial numbers around 8.8 µs/pair come from other runs/protocols; no matched serial win is claimed here.

## What is unchanged and verified

The warmed graph contains the original Q/K AITER/FlyDSL kernels and exact shapes, splitK choices, data hashes and kernargs. The main replay has 400 kernel dispatches, 398 cross-lane AND packets, two entry gates and two SYSTEM-release exits. Both lanes are completely published before release. Packet audits retain the original ordered bits and AGENT/AGENT kernel fences; each AND is NONE/NONE. Every kernel has a unique completion signal. All three modes share the same two queues and have the same 401 packets per lane. Numerical checks include poisoned outputs and changed/restored inputs; queue wrap is exercised.

Allocation receipts prove CPU ownership for both host modes and ownership by the selected GPU for local mode, fine-grain flags, matching CPU/agent bases, correct alignment and 4096 bytes for every private signal. All initialized values are read back as one before publication. Both ordinary host-backed final exits and both queue read indices retire before every internal value is checked zero, both storage guards are checked, profiling is read, or storage is reused/destroyed. No host internal-signal access occurs between gate release and both exits.

The private ROCr implementation constructs real SharedSignal/BusyWaitSignal objects. It does not manufacture handles for normal HSA APIs. Its diagnostic destruction hook avoids the CPU CAS that cannot be assumed supported over PCIe; ordinary signals retain their original destruction behavior. CPU waits/async registration/RMW are forbidden for the private objects. This is private implementation behavior, not a portable public HSA signal-placement API.

## Important cost still outside the primary interval

GPU-local preparation measures **15.896479 µs/pair**, versus 0.032188 µs/pair for matched host pages. This includes per-signal CPU reset, readback and guard verification over the GPU mapping; it is not an isolated reset-cost measurement. Preparation is reported and excluded from the primary interval by design. Post-drain checks are also outside it. Adding preparation alone would erase the execution win, so this prototype is not a usable end-to-end optimization.

The next implementation must remove per-signal CPU traffic through a generic graph-owned signal arena and batched GPU initialization/reset. Prefer a GPU scatter reset of value and required profiling timestamp fields: copying whole SharedSignal templates would unnecessarily overwrite core_signal/id, and SharedSignal is not trivially copyable. Initialization and dependency ordering must be included in total launch/replay timing. Final host retirement, concurrent launch ownership, failure handling, graph updates and signal reuse must remain correct. Only then should the unchanged PyTorch serial/two-stream workload be compared in one matched run. Holdouts remain deferred until that candidate wins.

## Interpretation

The placement change is now experimentally tied to about 2.5 µs of the recurring interval. Source inference alone was insufficient; this matched experiment supplies the missing causal evidence. The separate profiling-on comparison also shortens profiled dispatch-end-to-next-start intervals, with the same direction and roughly the same magnitude. Profiling perturbs execution and its dispatch-end timestamp is not an independent signal-publication timestamp. The result does not isolate propagation, CP polling/recognition, cache policy, or firmware internals, and does not prove a firmware bug.

The positive result justifies one focused architecture implementation; it does not justify reopening admission, helper-budget, coalescing, or CPU-readiness sweeps. A further diagnostic allocation/cache policy sweep is not needed before testing efficient initialization and real runtime integration.


Profiled Q/K dispatch durations do not shrink: normal/dedicated host medians are 4.56/4.48 µs, versus local 4.60/4.60 µs. All 6,400 profiled Q/K dispatch-envelope pairs per mode overlap. These are packet profiling envelopes, not newly instrumented wave timings; they locate the measured saving between successive pairs without claiming exact wave occupancy or clock-rate attribution. Derived values are retained in PROFILE_CHECK.json.

## Provenance and reproduction

- Official ROCr base: `97f5574fe2fdc7bef44fb01545347912ee9f1779`, subtree `projects/rocr-runtime`.
- Private two-file runtime patch SHA256: `89e7a4554560e5d151328630c8e8641be0c67cef6a3445773137b9101c6686b4`.
- Source manifest SHA256: `018c4e69cf5899cb210cfe954a8668286dd09f52184c68d8a57ca172fe2681a1`.
- HSA: `2899f94063127a3c6d0bbba0e5c5c54cab3256499f2f0183f6a53631b5fdad12`.
- Unchanged K HIP: `0e7d28519f042d62539007deb9b849edc191eb7cb7ed5abfafe4b58f0f05dbb4`.
- Raw manifest SHA256: `981f3567a5b96c761d03c4fc8e63555ad25a7ca42360c502b89aa6cc3ba3d48c`.

Task directory: `/home/sashawork/dev/amd-runtime-production/iterations/hassan-signal-locality-20260919`; remote mirror replaces `/home/sashawork/dev` with `/workspace/home/sasha`. Raw results are `results-j55065`. `run.py --out results-j55065 --audit` reproduces the strict local audit. Frozen benchmark/build sources and private patch are included in `signal_locality_probe/` in PR1. Build provenance records the exact source files and tool hashes; source is obtained with `git archive` of the pinned ROCr subtree followed by the included patch, not from the newer local main checkout.

CPU-only build attempts 55038/55047 failed CMake tool-package discovery, and 55050 failed missing xxd before the final library linked. Their logs/build directories remain retained. Build55060 completed after supplying task-local CMake imports for the existing ROCm clang/objcopy tools and a hashed xxd executable. No container-global installation, driver change or firmware change occurred. The GPU experiment used only the final audited build.
