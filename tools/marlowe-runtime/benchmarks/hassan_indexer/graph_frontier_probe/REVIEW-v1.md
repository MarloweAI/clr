# Independent hook and source review: v1

## Verdict

The v1 candidate is suitable for the bounded, default-off GPU fixture run on its current qualified surface: direct-dispatch HIP, one gfx950 agent, enabled captured kernel nodes, no profiling or activity callbacks, and argument-only graph updates. This is source clearance for testing, not runtime qualification or a performance claim.

Reviewed identity:

- baseline: `7d32325def2918c31f7217b40699b4b551c20f9e`
- candidate patch SHA-256: `8442025c3adb0402996609f36465f63d002dfe779c3aeca9759e657bcc4617a7`
- source manifest SHA-256: `a10a8926d2d649c76f0c830101e405d55dc88a1e0406eb5ff16a072eaa53acea`

The implementation diff across the nine runtime files was reviewed directly. `git diff --check` passed. CPU-only build job 55490 passed. No GPU timing evidence was available for this review, so no latency, throughput, or Hassan-result conclusion follows from it.

## Accepted contracts

The public-retirement hook is correctly attached before ordinary command submission. A deferred graph command stays in the normal host submission batch but suppresses the immediate `CL_COMMAND_TASK` flush. The next ordinary command detaches the graph command's preallocated bridge under the launch queue execution lock, arms it only after detachment, enqueues it, and then forms behind it. This avoids a graph-command/bridge ownership cycle. `execution_` is explicitly recursive, and the existing watermark path already enqueues a marker while holding it, so this recursive bridge enqueue is valid.

The bridge is a real marker. It gets the normal batch head, profiling timestamp, ordinary completion signal, and HSA callback. Its raw no-scope wait consumes only the private frontier; the following ordinary system fence and signal retire the host batch. Private graph handles do not enter `HwEvent`, `HwQueueTracker`, host waits, IRQ callbacks, or native-wait admission.

The callback ownership split is sound. A successfully completed graph command releases its predecessor lease because its final all-lane token proves that every read of the predecessor token has retired. Its own GraphExec and generation lease remains until final command destruction, so a successor can safely keep reading that command's frontier. A successfully completed bridge releases its graph owner after its raw wait retires. Both paths test `status == CL_COMPLETE`; this matters because ROCclr routes negative completion statuses through the same callback mask. Atomic exchanges make callback and cleanup idempotent. Error paths preserve references and quarantine storage instead of recycling it.

Watermark, finish, synchronization, notification, event/callback insertion, query, copies, and normal stream destruction all pass through an ordinary marker or command and therefore materialize the frontier. No background retirement thread is required. `hipGraphExecDestroy` can remain asynchronous because the deferred command owns GraphExec until retirement. Deferred commands are kept off force-destroyed internal side streams.

The first/nonchained predecessor protocol is coherent. Notification occurs outside all execution locks; the retained original tail and its exact notification marker prevent ABA. After canonical acquisition of all participating execution locks, the launch accepts exactly that tail and retries after an intervening submission. The ordinary predecessor signal is imported on the launch queue, the private entry token is completed after it, and the first kernel on every touched physical lane acquires SYSTEM. On a chained launch, launch-queue order follows the prior final join and side lanes wait the prior frontier.

Topological publication and final joining are also coherent. Producers are published before cross-lane consumers. Each segment completes a private token, the current last token for every touched physical lane is included in the prepared prefix/final join, and ordered barrier packets extend the AND above five dependencies. The final packet acquires AGENT and releases SYSTEM. Partial-publication injection uses a prebuilt join of only the touched lanes before entering normal host retirement.

The raw queue reservation leaves one AQL slot unused and bounds each reservation chunk to `queue_size - 1`. Publication copies the packet body before the release-store of its header. Dynamic side-queue release is safe only after the queue drains; at that point its token value is independent of the physical queue. GraphExec retention prevents destruction of the internal streams before the public final join and bridge retire. `getQueueID()` reacquires a dynamically released hardware queue while its execution lock is held.

Signal reuse is guarded by per-launch generation ownership. Cached ROCr value pointers are reset only for a fully retired generation using lock-free aligned signal-width stores followed by `SFENCE`. The generation is returned to the pool only from final command cleanup after successful retirement. Monotonic graph kernarg allocation keeps argument-only updates from overwriting an older launch, and the graph launch mutex prevents packet-template mutation while a launch copies and publishes its packets.

## Unresolved qualification gates

Function-changing graph updates and module unload are not qualified. Retaining GraphExec keeps packet templates and the monotonic kernarg pools alive, but it does not by itself prove ownership of the exact executable referenced by an already-published `kernel_object`. The candidate must not claim this case.

A lightweight fix is available from the existing object model: while snapshotting each launch under `graph_signal_launch_mutex_`, resolve every distinct current `hip::DeviceFunc` to its `amd::Kernel*`, call `retain()` on those kernels, and store the deduplicated list in the `GraphFrontierCommand` launch lease. Release them only from the command's final idempotent cleanup. `amd::Kernel` owns a `SharedReference<amd::Program>`, so retaining the exact kernel also holds its program and device executable across a function-changing update or module unload. Until that lease is implemented, such operations should force ordinary retirement or make the frontier path ineligible.

Two performance risks remain measurements, not correctness failures in the bounded fixture. CPU enqueue can allocate a new `(segments + 2)` private-signal generation for every launch until a public bridge completes, and a full AQL ring spins while all participating execution locks are held. Qualification needs an in-flight capacity/backpressure policy and actual timing data before this can be considered for a production path.

The deliberate error quarantine preserves references rather than proving drainage and reclaiming them. That is safe for the diagnostic failure fixture but needs an explicit owned quarantine/drain policy before production use.
