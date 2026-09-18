# Fixed-work attention dispatch cost

This is a mechanism test, not yet a validated HiSparse proxy. It reuses the real
QK / online-softmax / weighted-V producer and independent double-precision CPU
oracle from `attention_fork_join`. The only kernel extension is a first-head
argument: splitting a branch distributes disjoint output heads over launches.
Each head keeps its complete reduction. No extra intermediate/reduction work is
added. More launches change occupancy, scheduling and launch-boundary costs;
fixed arithmetic and logical bytes do not imply fixed duration or physical traffic.

The matrix has 42 cells per process:

- 256 heads, 256 or 1,024 tokens per partition; 1/4/16/256 launches per branch.
- Eager and full captured DAG, serial and two-stream parallel execution. Unsplit
  wide launch is an additional control at one launch per branch.
- Original 64-head, 8,192-token case with serial/parallel/wide, eager and graph.

The original attention trace stamps each CTA. Report GPU total, host completion,
host submission, each branch's span, consumer handoff and actual overlap separately.
Serial branch spans supply a no-side-wait comparison. The historical field name
`side_ready_before_main_end` compares the last in-kernel CTA timestamps only. It
neither identifies the event signal's zero transition nor proves when a native
packet begins: the current prewait vendor header has its barrier bit clear and
may begin while preceding consumer kernels still execute. Separate traces check
emission, not unbiased packet-entry timing. Do not equate body-end ordering with
native-wait readiness. Multiple waiting consumers remain a subsequent experiment.

`run.py` compiles one binary, then rotates fresh stock/released/candidate-off/
guarded/threshold32/threshold8/cost-relaxed processes across three rounds. It
checks exact cell coverage, every output, finite times, actual mapped HIP/HSA
hashes and controls. Every measured trial is retained. Five separate diagnostic
processes check compiled controls and queue eligibility, including queue-cap1;
actual physical IDs decide whether an edge shares a queue. Trace timings are
excluded from performance summaries. Output directories must be fresh and outside Git.

Example inside the allocated single-GPU container:

```bash
python3 run.py --output /absolute/fresh/results \
  --candidate-lib /absolute/cost-diagnostic/lib \
  --released-lib /absolute/released-v9/lib
```

The diagnostic's count thresholds and cost relaxation are experiment controls,
not a production policy. Default graph scheduling, markers and original dependency
packets remain. A threshold near a particular benchmark's launch count does not
become the shipping choice without the queued, expert, small-copy, original waiter,
PyTorch and matched HiSparse holdouts.


`run_arrival.py` uses the same producer with the independent partition precomputed
outside timing. It compares producer-alone, early cross-queue consumer, delayed
consumer and already-ready-at-CPU. There is no initial fork in the measured
sequence. Prefix length is frozen by the first stock process for every policy and
round; actual producer-body/prefix ordering is reported. A one-thread timer filler
is an arrival control only, not representative producer work. Because the native
packet lacks an ordering barrier, latency exposed after the prefix is not a proven
nonblocking-packet cost. This limit is essential to interpreting job 50349.

`run_dedup.py` holds the attention fixture fixed and compares bounded duplicate
prewait suppression on/off on identical new bytes. Previous-runtime bridges include
native-off, guarded, threshold 8 and relaxed; packet traces add signal-object instance,
generation, virtual-consumer identity and the native call site. This still retains
every original AQL dependency and is not a qualified production implementation.


`run_packet.py` keeps both attention workloads and the original 2,048-increment
waiter unchanged. It rotates ten runtime modes across three process rounds,
retains every timing, and uses separate compiled-control traces. The packet
matrix is interval4 real/zero × ordered/unordered, plus unordered real intervals1
and16, guarded/off/stock and a previous-cost-build bridge. Stock alone freezes
arrival-prefix calibration for all modes. It audits coverage, correctness,
mapped library hashes, compiled controls, binary/source identities and reference
files. The standalone Slurm watcher provides monitoring deadlines; the runner
has no subprocess timeout that silently kills a workload.

Example inside a fresh allocation:

```bash
python3 run_packet.py --output /absolute/fresh/packet-results \
  --candidate-lib /absolute/packet-diagnostic/lib \
  --prior-lib /absolute/cost-diagnostic/lib \
  --waiter-source /absolute/native_wait_policy/minimal_wait.cpp
```

The zero target keeps the real AQL wait and can restore producer interference;
ordered packets wait behind prior work on the entire physical queue. Neither
control is a production policy. See the interpretation limits in the design review.


`run_arrival.py --launches 1 16 32 64 128 256 --modes stock off guarded threshold24
threshold32 threshold64 relaxed` expands only the number of disjoint output-head
launches, preserving the default kernel and oracle. Allowed launch counts are
unique powers of two through256; defaults remain1/16/256. The runtime modes,
workload count receipt, exact coverage and frozen prefix calibrations are recorded.
Use a fresh source/output directory when staging a variant so prior source/hash
receipts remain verifiable.
