# Partial overlap and two/four-stream continuation

Extends the measured attention fork/join producer. Each stage prepares independent
attention summaries from disjoint token partitions, joins them with stable softmax
rescaling, then updates the query: q_next = q + 0.125 * attention_output. All next-stage
branches consume this updated query, so every wait represents a real data dependency.
The same total key/value token work is split over 1,16 or64 sequential stages.
All schedules produce the same output within each configuration.

Configurations: balanced and uneven (main branch 7/8 of tokens, remainder split
among side streams), at128 queries and16384 total tokens; a resource-occupied
control uses2048 queries,4096 tokens,1stage. Each uses2 or4 branches. Serial executes
all branches on one stream; parallel uses one stream per branch and event joins;
wide launches all partition CTAs in one kernel on a single stream. Useful attention
work is unchanged between arities. The stage-count variants have different query
feedback dependencies; only within-configuration timing comparisons are causal.

Real work: FP32 QK, online softmax and weighted64-vector V accumulation. No spin
kernel, masking or padding. One256-thread CTA per query and partition. Each step
consumes a new segment of the same fixed total KV input, rather than rereading an
arbitrarily repeated toy workload. The uneven case has an ideal speedup bound near
8/7 regardless of2/4 streams; more streams cannot remove its critical path.

Three runtime modes: stock /opt/rocm7.2.4, exact RC4 off, exact RC4 on. Three process
rounds rotate mode order.16 measured trials rotate schedules after4 warm trials.
Two changing input seeds. Every output is checked against independent double-
precision CPU attention with query feedback, without GPU partition logic; references
are shared across2/4 branches and balanced/uneven partitions, hashed at completion.
Every operation poisons state and validates timing order of branches, joins and
subsequent continuations. Raw per-stage branch/join envelopes for trial0 are logged
outside GPU timing; every measured trial's aggregate envelope/gap metrics retained.

Run only on one GPU on node2, as sasha through the supplied salloc + gpu-profile
interactive path. Set ASC_OUT to a fresh directory and run python3 run.py.
ASC_QUICK=1, ASC_ROUNDS=1, ASC_REPEATS=4 selects a geometry/correctness check.
ASC_CONFIG can select one named configuration for a separate diagnostic; flags
such as GPU_NATIVE_EVENT_TRACE must not be used for headline timing runs.
