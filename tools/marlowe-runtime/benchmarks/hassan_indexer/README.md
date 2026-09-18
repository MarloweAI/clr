# Hassan's Q/K scheduling workload

Single-GPU microbenchmark extracted from [Hassan's reproducer](https://github.com/MarloweAI/native-runtime-four-arm-reproducer/tree/b8a96bb4d842f628142e417ebb6753d4492bcaff).
It reuses the exact 91-line scheduler and existing AITER/FlyDSL GEMMs. No GPU compute kernel is modified.
The original repository measures TP8 L10 serving cadence; this extraction measures the projection pair only.
It cannot reproduce changed routing, downstream attention, request pauses or full-model latency.

| BF16 projection | Input | Weight | Output | Split K | Solution |
| --- | --- | --- | --- | --- | --- |
| Q | 4 × 2048, stride (2048,1) | 4096 × 2048, stride (2048,1) | 4 × 4096 | 4 | FlyDSL 1400 |
| K | 4 × 6144, stride (6144,1) | 128 × 6144, stride (6144,1) | 4 × 128 | 12 | FlyDSL 4881 |

These are 16/48 KiB inputs, 16/1.5 MiB weights and 32/1 KiB outputs (Q/K).
The full dispatch dictionaries, including exact kernel names, are retained in `projection-dispatch.json` and checked against the installed AITER configuration before running.
Stored `us` values in those dictionaries are historical tuning metadata, not measurements from this benchmark.
Inputs and weights are seeded synthetic BF16 values with these exact shapes and strides; they are not captured model activations or checkpoint weights. Their bytes must match across all processes.

Serial executes Q then K on the main stream. Events records readiness before Q, executes Q on main and K on the side stream, then joins K back to main. The unchanged helper owns events through graph capture and uses ordinary events. Results include eager invocation and HIP graph replay, with graph replay the primary hardware-scheduling endpoint. Event timing includes device idle periods from host submission; it is not a sum of isolated kernel durations.

Each process checks changing inputs and a 200-invocation queued burst in both modes against FP32 matrix multiplication. HIP/HSA mappings are checked before loading kernels, after warmup/capture and after timing. The numerical screens reuse the historical normalized RMS/max thresholds (Q .0067/.20, K .012/.15); applying them to these synthetic inputs is a bounded correctness screen, not a full-model numerical guarantee. No correctness or profiling operations occur inside timing loops. Timings include every fixed trial.

The frozen campaign compares **stock and current candidate only**, each with serial/events, using four Williams rounds. Each process runs both eager/graph with eight trials of 200 invocations after 40 warmups. Submission order alternates by round. CPU affinity is inherited; all relevant runtime controls, loaded HIP/HSA hashes, source identities and data hashes are retained. Old experimental runtimes are not tested.

`run.py --spec SPEC --out NEW_DIRECTORY` executes the frozen campaign; `--audit` revalidates retained results. A separate Slurm launcher owns resources and monitoring. A current-runtime loss against stock remains a failure of the performance goal, even if streams improve on serial within that runtime. A serial/events loss is retained and does not justify changing kernels or dimensions to manufacture overlap.
