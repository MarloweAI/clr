# Selective native-wait regression matrix

This suite compares stock HIP/HSA, one candidate with native waits disabled, and
identical candidate bytes with native waits enabled. It tests the runtime policy;
it does not replace the standard Marlowe GLM serving benchmark.

Run on one allocated MI355X GPU. For the current Marlowe campaign, use node2 and
the supplied `salloc → srun --pty gpu-profile → bash -i` route. Inside that shell:

```bash
python3 run.py --candidate-lib /path/to/overlay/lib \
  --output /path/to/fresh-results
```

For a development build whose HIP and matching HSA live in different directories,
add `--hsa-lib /path/to/matching/hsa/lib`. The default stock directory is
`/opt/rocm/lib`. The benchmark verifies one visible GPU and each measured process's
actual mapped HIP/HSA hashes. It compiles each source once and uses that same
binary in all modes. Output directories must be fresh; failed processes and raw
samples are retained. At least three process rounds rotate runtime order.

The fixed full matrix contains:

- The original 2,048-increment graph: alone, pending side-stream wait, ready wait.
- The existing attention chain workload: balanced/uneven work, 1/16/64 dependent
  stages, two/four branches, serial/parallel/wide schedules, and the occupied
  control. Every output is checked against independent double-precision CPU work.
- Eager and graph dispatch prefixes of 32–4,096 kernels, plus delayed waits near
  completion. Repeat `--cases dispatch --queue-cap 1` to exercise physical queue
  sharing; the default cap is four queues.
- A GPU-written checkpoint followed by 4/16/64 tail kernels before consumer wait.
  This catches stale producer-backlog estimates without relying on a host sleep.
- Interleaved and trailing event records. A logical graph event record need not
  become a separate physical AQL packet. Eager interleaving and graph interleaving
  are separate cells; do not assume both must suppress admission.
- 100,000 eager launches with/without per-launch profiling events. Host submission
  time includes queue backpressure and is not described as CPU instruction time.

The full default suite has 14,958 measured operations in54fresh processes.
`manifest.json` records source, binary and runtime hashes and process outcomes;
`summary.json` retains every cell's process medians and paired percentage changes.
Producer duration is included in the performance screen. Resume, join and
continuation gaps are reported separately with absolute and relative deltas, and
per-cell pending counts/fractions are retained. A gap can increase while the
producer finishes much earlier and total latency improves; individual component
ratios are therefore diagnostic rather than independent acceptance gates.
Correctness, exact cell coverage, finite positive times, and runtime identity are
mandatory. A slowdown above 2% in every paired process round fails the performance
screen (exit3); all deltas remain visible, including smaller or inconsistent ones.
The original pending-wait case must also remove at least half of the excess time
over its matching alone control in every round, against both stock and off. This
prevents an ineffective/always-disabled policy from passing the full suite. A
subset without the minimal case records this gate as untested.
A passing finite screen does not prove universal neutrality or production readiness.
Use a separate allocation for replication before promotion.

`callback_dispatch_prefix.cpp`, `queue_churn.cpp` and `eligible_pool_pressure.cpp` are additional
standalone semantic/forward-progress tests. Compile with `hipcc -O2 -std=c++17
--offload-arch=gfx950 -pthread`. Run each under stock, candidate-off and candidate-on.
The callback test surrounds a blocked host function with two 300-kernel graphs;
its watchdog detects host submission blocking and the consumer must observe600.
The pool test forces2,300 pending waits behind an eligible2,048-kernel producer,
exercising native buffer rotation and nonblocking AQL fallback. Use
`GPU_NATIVE_EVENT_TRACE=1` only for separate admission/rotation diagnostics.
The churn test concurrently creates, exercises and destroys eight streams while
another thread executes128eligible producer/consumer handoffs; both threads
validate outputs. Trace runs are excluded from headline performance comparisons.

PyTorch event/graph, threaded event-generation reuse, cooperative launch, upload
and lifetime checks remain separate release qualification requirements. Full-model
qualification must use the unchanged standard Marlowe recipe, without HiSparse.
