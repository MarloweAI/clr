# Distributed physical-queue boundary review

## Verdict

The distributed boundary is semantically viable for the existing frontier-qualified path, but only with an explicit producer-release invariant and an exact sealed tail set. It is a reasonable focused experiment for the measured two-queue first-pair skew. It does not remove the required graph boundary: every new physical queue must still wait for every prior physical queue. It removes the extra `final join completion -> side entry wait` hop and makes the two-queue boundary symmetric, so improvement is plausible but not established.

## Required boundary contract and minimal hooks

Replace the single `Command::graphFrontier()` handle with a read-only boundary descriptor on `GraphFrontierCommand`. The descriptor needs the backend agent/device identity and one `{physical_queue_identity, private_tail_signal}` entry for each touched physical queue. Physical identity must be the same stable identity used by packet publication, not a logical stream index. The command and its generation continue to own the signals, captured kernels, arguments, and side streams.

`RunGraphFrontier` can reuse the current physical `tails` map. For a compatible retained predecessor, the first batch published on physical queue `q` receives every predecessor tail whose physical identity differs from `q`; queue order covers the matching tail. All later batches on `q` follow that first batch. This establishes every prior leaf to every new root because each prior leaf precedes its queue's terminal tail. The existing arbitrary-length barrier batching already handles more than five dependencies. A different agent/device, an ordinary predecessor, or an unavailable descriptor must use the existing ordinary-entry path.

Do not publish the current all-lane final join for a compatible private successor. Before enqueuing the no-op `GraphFrontierCommand`, seal its descriptor from the tails actually published. A partial-publication path must expose only the last signal on each touched physical queue. If the ordinary entry packet was published but no graph segment was published, its launch-queue token is the touched prefix and must be represented. All packet batches, prefix descriptors, and bridge capacity must still be prepared before the first packet.

`GraphFrontierMarker` should retain its owner and borrow the owner's immutable descriptor; `arm()` must not allocate. Change `materializeGraphFrontier` to consume the complete tail set with ordered AND packets and then create the existing ordinary fenced profiling signal. The generic command hook, watermark, capacity fallback, queries, events, callbacks, copies, graph destruction, and stream destruction can otherwise keep their current bridge path. The hard-cap decision remains before publication and ordinary fallback must bridge the full descriptor.

The successor command's existing predecessor reference is sufficient for lifetime. Release it only after successful retirement of every successor tail reader. Batch completion through an ordinary bridge provides that proof; negative completion keeps the predecessor and quarantines storage. GraphExec update and destruction remain serialized, and exact captured-kernel ownership remains per generation.

## Fence requirement

A successor's SYSTEM acquire cannot compensate for a producer with release scope NONE. Current qualified gfx950 packets do have at least AGENT release: `AMD_OPT_FLUSH=1` selects AGENT acquire/release dispatch headers, `AMD_OPT_FLUSH=0` selects SYSTEM/SYSTEM, and the frozen packet traces show `release=1`. However, `graphSignalPacketsEligible()` does not enforce this property.

The copied signal-carrying tail kernel must therefore be forced to release at least AGENT, or eligibility must reject a weaker tail header. Forcing the minimum in `prepareGraphFrontierKernels` is the cheaper robust rule and adds no packet; it is a no-op for the current headers. AGENT release paired with the successor's SYSTEM acquire is sufficient for data ordering between queues on the same GPU agent. A SYSTEM release is required only when making the boundary public: the ordinary bridge must wait every private tail, acquire their device writes, and issue the existing SYSTEM-release ordinary completion signal for host, copy, and external observers.

## Performance interpretation

For two physical queues, the distributed form does not reduce the number of wait packets. It replaces the centralized join plus side wait with two direct cross-queue waits and removes one dependent-signal hop from the side. That could reduce the observed approximately 3.4 microsecond first-pair skew and help one-pair launches, while grouped launches should only affect their first pair. It may also merely move equivalent command-processor work, especially when the current final join has time to complete before the next launch arrives. With many queues, all-to-all first-use waits can exceed the centralized packet count.

Proceed only as a default-off, identical-work experiment with receipts proving the descriptor path, physical tail coverage, terminal release scopes, chained launches, and ordinary bridge retirement. Treat timestamp evidence and performance evidence separately; no performance claim follows from this review.
