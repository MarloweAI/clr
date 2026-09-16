# Attention fork/join microbenchmark

One logical attention operation, not a device kernel using host streams. A short
prepare kernel creates a data-dependent query. Two branches attend to disjoint
halves of a key/value sequence. Each branch computes a stable partial-softmax
summary (maximum, denominator, 64-vector weighted sum). A final kernel combines
the summaries with softmax rescaling. There is no cross-branch dependency until
the join. Query preparation and the join are included in elapsed GPU time.

Each branch has one 256-thread CTA per query, four 64-lane waves. Every wave scans
its token subset and performs real QK, online softmax and weighted V accumulation.
With fewer query CTAs than CUs, a branch cannot occupy all CUs, despite its long
execution time. Two branches can expose more useful parallel work. We measure
query counts at one quarter, one half and all of the GPU's CU count; 8,192 tokens
per branch, dimension64. No spin loop, CU masking or artificial resource reservation.
This is a simple FP32 attention-like kernel, not a tuned FlashAttention replacement.

Three schedules perform identical arithmetic and memory work:
- serial: prepare -> partition0 -> partition1 -> join, on one stream;
- parallel: prepare -> event fork -> one partition per stream -> event join;
- wide: prepare -> a single kernel with both partitions' CTAs -> join, one stream.

The wide control separates exposing parallel work from needing multiple streams.
Large kernels may show little native-wait benefit because there are few dispatches.
No speedup is assumed. Hardware occupancy limits, per-CTA global-clock spans,
actual kernel overlap, HIP total elapsed time, host completion time and whether
the join dependency was pending at submission are recorded. Branch-start skew and
the gap from the last branch completion to join execution are recorded too. Timestamps have the
same per-CTA cost across schedules. They show execution envelopes, not CU utilization.

Fresh processes compare stock ROCm7.2.4 libraries, RC4 native waits off, RC4 on.
Three rounds rotate runtime order. Each process rotates schedule order for24
measured trials per shape after four warm trials; query seed cycles across four
values. All values are checked against independent double-precision CPU attention
over the concatenated tokens, with absolute tolerance2e-5. Every intermediate and
output buffer is poisoned before each trial. Reference bytes are cached only
within the fresh result directory and hashed at completion. No intervals removed.

Run as sasha on node2, one GPU, using the previously supplied salloc/gpu-profile
interactive route and cached ROCm7.2.4 image. Set AFJ_OUT to a fresh result directory
and run python3 run.py from the immutable staged source. An initial geometry check
may set AFJ_ROUNDS=1, AFJ_REPEATS=4 and AFJ_HEAD_DIVISOR=2. That check is retained
separately from the final rotation. No full model is loaded or profiled.
