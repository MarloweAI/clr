# V8 distributed-boundary source review

## Blocking finding

V8 cannot qualify because an ordinary captured graph can publish its first launch-queue packet before consuming a distributed predecessor. `EnqueueSegmentedGraph` explicitly notifies the launch predecessor only for a level-zero set with more than one segment and a side root. The single-root, launch-only, shared-retire, and one-root-then-fan-out cases call `dispatchAqlPacketBatchImpl` from `EnqueueSegment` before the accumulator command is enqueued. The generic `Command::enqueue` hook therefore inserts the full-tail bridge after those captured packets.

This was safe with V7's central boundary because the preceding all-lane final join was already on the launch physical queue. V8 removes that join. Queue order then covers only the old launch-queue tail; an old side tail can still be running when the new root reads its output. The hole applies both to hard-cap ordinary fallback and to any ordinary/ineligible graph following a distributed command.

The proposed V9 hook is sufficient: factor the existing tail bridge into `Command::materializeGraphPredecessor`, and call its distributed-only form from `dispatchAqlPacketBatchImpl` while holding the consumer queue execution lock and before any raw publication. Limit this raw hook to ordinary publication (`graph_completion == 0`) and retain the `!defersGraphRetirement() && !consumesGraphFrontier()` guard. Recursive bridge enqueue is already the established lock path. Calling before the deferred-kernel-retirement early return is safe; it can retire the boundary early, and the eventual packet publication still follows it. A delayed-side distributed producer followed by an ordinary single-root consumer is the required regression fixture.

No second correctness blocker was found in the six-file V8 diff.

## Descriptor and dependency coverage

The immutable descriptor is correctly owned by `GraphFrontierCommand` and contains one tail per physical HSA queue plus the owning `amd::Device`. A compatible successor adds every foreign tail to the first batch on each physical queue and relies on packet order for the matching physical queue. Because each prior leaf precedes the final segment on its physical queue, this establishes every prior leaf to every new root. The retained predecessor command keeps its generation, exact kernels, arguments, signals, and streams alive until all successor readers retire.

The descriptor uses `gpu_queue_->id`, which is the physical queue identity already used by assignment and dependency lowering. A live non-idle predecessor cannot release that queue; an idle queue has already completed its tail. Device identity prevents interpreting queue IDs across devices.

Preparation remains atomic with respect to publication. All packet plans and prefix descriptors are built before signal reset and before `markPublished`. The command is sealed before it enters the HostQueue batch. The vector move into its empty descriptor uses the equal standard allocator and does not allocate after publication; using `swap`/`noexcept` would make that implementation intent more explicit but is not required for correctness.

## Partial and zero prefixes

Selecting `plans[submitted - 1].prefix_boundary` records exactly the last published segment on each touched physical queue. A nonchained zero-segment prefix exposes the already-published entry token. A chained zero-segment prefix copies the predecessor descriptor, so public retirement still waits the inherited work. A central predecessor is represented by its central token on the launch physical queue. These cases keep the predecessor reference until ordinary retirement, preventing token reuse.

The private `frontier_` handle remains a nonzero command tag in distributed mode and is deliberately never produced. All distributed consumers and bridges select `graphBoundary()` rather than that tag. Toggle incompatibility takes the ordinary notification path, so no reviewed path waits the unproduced handle.

## Fence and public visibility contract

The copied signal-carrying kernel is upgraded to at least AGENT release. The first successor kernel retains SYSTEM acquire, and all compatible queues belong to the same GPU agent. This is sufficient for device-data ordering; SYSTEM acquire would not have repaired a release-NONE producer, so the explicit upgrade is necessary.

The public marker waits the entire descriptor in ordered groups of five. Its last wait performs AGENT acquire, and `publishGraphFrontierPackets` marks pending/dirty state, forcing `releaseGpuMemoryFence(true)` to emit the ordinary SYSTEM acquire/release barrier with a normal profiling signal. Host callbacks, events, queries, copies, destruction, and SDMA therefore receive public visibility without reading a private token. The marker retains its owner while borrowing the immutable descriptor, and negative completion preserves ownership and quarantine.

## Performance risks and recommendation

For two queues, V8 replaces the central join plus side wait with two direct foreign-tail waits. The packet count is unchanged, but the extra join-completion-to-side-wait hop disappears. This can plausibly reduce first-pair skew; it can also move equivalent command-processor work. Larger queue counts can increase all-to-all wait packets.

Distributed planning currently constructs the unused `terminal` vector for every segment even though no prefix join is built, and copies the prior descriptor into `empty_boundary` for every chained launch. Both are prepublication and safe, but they add allocator/copy cost to the submission path. Remove the unused terminal construction before timing. Keep or explicitly account for the zero-prefix copy. Prefix-descriptor allocation otherwise replaces V7's prebuilt prefix-join storage rather than adding a wholly new preparation stage.

Keep V8 build and fixture results as provisional implementation evidence only. Qualification requires the V9 pre-dispatch bridge fix, the targeted delayed-side-to-single-root fixture, the existing lifecycle/ownership/cap suites, exact distributed-path receipts, and separate timestamp and performance runs.
