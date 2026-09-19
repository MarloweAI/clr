# Hassan's Q/K scheduling workload

[Stock-only mechanism diagnostics](STOCK_MECHANISM_RESULTS.md) found that this historical extraction captures two lazy split-K buffer fills on a fresh capture stream. Hassan's serving source warms the actual capture stream first. The prewarmed diagnostic removes this artifact, but stock two-stream execution still loses to serial. The [calibrated warm timeline](WARM_TIMELINE_RESULTS.md) shows useful overlap canceled by a larger interval before the next pair. Historical gates below retain their original protocol; do not transfer their absolute times or runtime wins to a prewarmed graph without a matched comparison.

Latest checkpoint: actual HIP/PyTorch integration now gives a substantial two-stream win on the synthetic 50-pair graph built from unchanged Q/K kernels: 7.477 µs/pair versus stock 10.065 and its own serial control 8.841. The matched host/local signal-placement effect is −24.32%. The short two-stream fallback still regresses 17.04%, so there is no qualified runtime or original-application win yet. The grouped extraction is not Hassan’s unchanged serving graph. Next work must preserve the grouped win while resolving the inherited fallback regression. Comparisons below are matched within each report; absolute times from different protocols are not interchangeable.

| Experiment | Main result | Decision |
|---|---|---|
| [Final-kernel completion](KERNEL_COMPLETION_RESULTS.md) | Forced segmented grouped path −8.57%; still slower than stock/serial | Useful recovery, not the goal |
| [Internal packet publication](INTERNAL_PUBLICATION_RESULTS.md) | GPU −0.06%; CPU submission −11.46% | GPU-neutral; closed |
| [GPU prewait](GRAPH_PREWAIT_RESULTS.md) | Entry +11.22%; grouped internal waits +17.14% | Rejected |
| [Single-queue capability](SAME_QUEUE_RESULTS.md) | No tested same-queue overlap; all16 two-queue controls overlap | No runtime port |
| [Exact two-queue AQL replay](DIRECT_AQL_RESULTS.md) | Ordinary joins9.626; native prefixes43.010us/pair | Native internal waits rejected |
| [CPU-ready publication](CPU_READY_RESULTS.md) |12.169 vs9.638us/pair with matched CPU observer | Retained-barrier scheduler rejected |
| [Satisfied-barrier omission](READY_OMIT_RESULTS.md) | Scheduler −19.10%, but10.294 vs9.642us/pair prepublished | CPU-readiness architecture closed |
| [GPU-local completion signals](SIGNAL_LOCALITY_RESULTS.md) | 9.734 → 7.222 µs/pair; recurring profiled interval 5.16 → 2.56 µs | Placement mechanism established |
| [GPU reset including total replay cost](GPU_SIGNAL_RESET_RESULTS.md) | 9.722 → 7.353 µs/pair, −24.37%, including reset/publication/host exits | Lower-layer feasibility passes; see subsequent HIP integration |
| [Actual HIP graph-local signals](GRAPH_LOCAL_TOKENS_RESULTS.md) | Grouped two-stream 10.065 → 7.477 µs/pair; own serial 8.841; short two-stream +17.04% | Real grouped win; short fallback prevents qualification |

The [architecture checkpoint](ARCHITECTURE_CHECKPOINT.md) records the current runtime result, remaining fallback work and device-side measurement boundary. The [polling evidence and observability review](OBSERVABILITY.md) separates long-producer interference from short-join latency and records a clock-calibrated observation contract; no new runtime or GPU result is claimed. The [earlier same-queue design](NEXT_SAME_QUEUE_PARALLEL.md) is closed. None of these diagnostic outcomes is a new production-qualified runtime.

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
