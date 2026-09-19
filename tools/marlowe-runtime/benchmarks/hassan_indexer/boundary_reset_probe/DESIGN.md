# Cached value-pointer reset: one causal follow-up to55349

Goal1 remains unchanged: improve the original Hassan two-stream Q/K graph through the runtime, with no application/kernel changes or workload-specific heuristic. The larger g50 graph alone does not satisfy it.

55349's explicit graph boundaries preserved the original dependency topology but were not a winner. Its GPU-local signal preparation took7.136us/pair atg1 and4.748us/pair atg50. The public signal-store API traverses GPU-resident SharedSignal metadata before storing. Those numbers therefore do not establish plain store cost; see the predecessor ERRATA.md.

This experiment compares the API reset with a cached pointer obtained from hsa_amd_signal_value_pointer outside timing. Mode3 uses the exact signals and packet arrays of private-host mode1; mode4 uses the exact signals and arrays of private-local mode2. The sole timed reset difference is an aligned lock-free64-bit relaxed store instead of the public API call. All arms retain identical timestamp clearing, SFENCE, packet publication, ordinary host-final completion and both-queue drain. Prior invocations are completely drained before reuse. Owners remain alive; no hot-path pointer lookup, host RMW or concurrent reset. Guards and exact signal values are checked after drainage. Internal timestamp fields are a pinned-ABI diagnostic, not a public interface proposal.

Original kernel objects, dimensions, arguments, AGENT fences and graph dependencies are unchanged. Each graph has an explicit SYSTEM/SYSTEM entry and final join, with the side queue gated by the entry token. Both graph sizes use200pairs total. All preparation, publication and waiting is included in the primary profile-off CPU wall span. Dispatch profiling is a separate arm and cannot define the primary result. The HIP reference uses different submission/timing boundaries and is context, not a causal denominator.

Four rotated/reversed rounds, eight trials per cell;11cells (HIP plus five packet modes with profiling off/on),704timings and5610numerical checks. The existing exact packet, library-map/hash, changed-input/poison-output, signal guards/completion, graph lifetime and queue-wrap audits remain mandatory. This is a packet probe, not an actual HIP integration or production qualification.

Root launches once on node2 with one GPU and monitors the same Slurm job. Soft observation windows:120s startup/stall,300s execution,300s queue; inspect rather than cancel/relaunch. Hard Slurm limit15minutes is only runaway protection.

Decision: first attribute API lookup cost from same-object mode2/4 and host mode1/3 controls. If g1 still has no useful headroom versus the actual HIP reference, this reset optimization alone does not justify a runtime port. Any further boundary/fence change must have a source-level ordering/visibility proof and a matched experiment. No broad holdouts or production run until an original-sized candidate merits them.
