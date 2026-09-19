# Hard-cap and v2 ownership review

## Verdict

A generation-owned intrusive reference to its pending `GraphFrontierCommand` is a sound way to make hard-cap selection safe. The cap path may retain that command while holding `graph_signal_pool_mutex_`, drop the mutex, and use the existing event completion path to materialize and wait. The design needs one correction: the generation's pending reference must be detached on every terminal callback, not only successful completion. Success permits later reuse; an error detaches the cycle but permanently quarantines the generation.

The v2 captured-kernel ownership delta is sound for the stated purpose. It does not transfer v1 performance or fixture qualification to v2.

## Concrete capacity hooks

Add an owned raw pointer and serial/kind metadata to `GraphSignalGeneration`:

```cpp
amd::GraphFrontierCommand* pending = nullptr;  // owns one retain
uint64_t pending_serial = 0;
```

The pool already owns the generation. Do not use a non-owning command pointer: `ReferenceCountedObject::retain()` asserts if the count has reached zero, and a final `release()` may already be inside `terminate()` or destruction.

Install the pending retain only after packet plans, callbacks, signal reset, and every other fallible pre-publication operation have succeeded, but before `markPublished()` and the first packet publication. Under `graph_signal_pool_mutex_`, retain the locally live command, store it in the generation, and record the serial. From that point the existing path must always publish a sealed prefix/final join and enqueue the command. A pre-publication failure must occur before this retain is installed; otherwise a command that is never enqueued cannot receive the callback needed to break the cycle.

Extend the command's existing terminal callback rather than adding an independently ordered callback. In that callback:

1. Lock `graph_signal_pool_mutex_`.
2. Verify that `generation->pending == self` and atomically/mutably detach it.
3. If `status != CL_COMPLETE`, set `quarantined = true` while still locked.
4. Unlock the pool.
5. Release the detached pending reference.
6. Continue the existing predecessor-reference release only for exact `CL_COMPLETE`.

The detached command must be released outside the pool mutex. It can eventually invoke `GraphFrontierCommand::releaseResources()`, whose owner callback takes the same mutex. Releasing under the mutex would create a direct self-deadlock. ROCclr invokes HIP callbacks before committing the terminal status, but the submission batch still owns multiple references while the callback runs, so dropping the pool's reference there cannot destroy the callback object in place.

On success, final command destruction remains the only point that clears executable owners and sets `busy = false`. This preserves the current rule that the generation survives while a successor still reads its frontier. The completion callback only removes the pool's pending-command edge. On failure, the callback removes that edge and marks the generation quarantined; final cleanup must not mark it reusable or release safety-critical quarantine ownership. Keeping the pending reference on error would leave the cycle

```text
GraphExec -> generation -> command -> GraphExec
```

permanent and would prevent the existing `release_owner_(false)` cleanup from running at all.

At the fixed cap, select the oldest nonquarantined busy generation with a non-null pending command. While holding the pool mutex, call `retain()` on that command; the generation-owned reference proves its count is nonzero. Then drop the mutex and call `awaitCompletion()` directly. A separate `notifyCmdQueue(false)` is unnecessary: `Event::awaitCompletion()` already calls `notifyCmdQueue(kCpuWait)`, which inserts an ordinary marker. The command enqueue hook first inserts the preallocated graph-frontier bridge, so the wait receives normal public completion without reading a private signal. Release the snapshot reference before reacquiring the pool mutex and retrying acquisition, because that release may be the one that reaches command destruction and takes the pool mutex to mark the generation free.

If `awaitCompletion()` returns false, do not retry indefinitely. The notification may have failed to allocate, or the command may have completed with an error. Recheck quarantine state and return a deterministic allocation/runtime error or fall back to the established ordinary graph path. Quarantined generations count against the hard resource cap and are never silently reused. If all capped entries are quarantined, waiting cannot make progress.

There is a short valid interval after the terminal callback detaches `pending` and before final command destruction changes `busy` to false. A cap scan can see `busy && pending == nullptr`. It must not dereference anything or allocate above the cap. The cheapest clean handling is a pool condition variable signaled after `busy` or `quarantined` changes; alternatively, drop the lock and yield/retry. Never wait on that condition while holding an execution lock.

`AcquireGraphSignalGeneration()` is currently called before the canonical execution locks, and `GraphExec::Run()` holds `graph_signal_launch_mutex_`. Keep the capacity wait there. The resulting order is:

```text
graph launch mutex -> pool snapshot/retain -> unlock pool -> command await/notify
```

The completion callback takes only the pool mutex. No pool or execution mutex is held during notification or host wait, and no command release occurs under the pool mutex. This avoids an execution/pool inversion. Holding `graph_signal_launch_mutex_` across the wait is conservative but does not block the completion callback; it simply serializes update/disable and another launch of the same GraphExec.

No `HostQueue` reference is needed. For an incomplete application-stream command, normal `HostQueue::terminate()` cannot free the queue: it inserts a marker when the batch is nonempty and awaits the last command before destroying the queue. If the selected command is already terminal, `awaitCompletion()` returns without dereferencing its queue. This proof does not apply to force-destroyed queues, so frontier commands must remain excluded from GraphExec internal side streams.

## Idle and destroy behavior

The cap guarantees bounded generations, but by itself it does not make `hipGraphExecDestroy` promptly retire an under-cap idle frontier. The generation owns the command and the command owns GraphExec until an observer, watermark, cap wait, or launch-stream destruction materializes it. This matches v1's deferred-retirement behavior, but it is an explicit ownership cycle while idle.

If production requires bounded destroy retirement without a background thread, add a pre-release hook in `hipGraphExecDestroy`: snapshot and retain every non-null pending command under the launch/pool locks, drop both locks, call `notifyCmdQueue(false)` on each snapshot, then release the snapshots and finally drop the public GraphExec reference. This is nonblocking; callbacks break the cycles after the ordinary bridges complete. Notification allocation failure must be surfaced or followed by a synchronous `awaitCompletion()` fallback. The hook must run before `ge->release()` because the destructor cannot initiate it: the pending-command cycle is what prevents the destructor from being reached.

## v2 executable ownership

The v2 candidate (`337e759d8ab5ba79666e7fabad56bf6a45838cf374269f49ac0d680d50f29cb9`) binds ownership to the exact `NDRangeKernelCommand::kernel()` used during packet capture, before the command submits into the capture buffer. Each first owner performs one intrusive `amd::Kernel::retain()` and places it in a `std::shared_ptr` with a matching `release()` deleter. Copies into the launch generation share that control block; deduplication by raw kernel pointer avoids redundant launch leases. This is preferable to `SharedReference<Kernel>`, whose copy behavior is unsuitable for a relocating vector.

`amd::Kernel` contains `SharedReference<amd::Program>`, so the retained exact kernel keeps the program and device executable underlying an already-copied `kernel_object` alive. `graph_signal_launch_mutex_` serializes recapture/update with launch snapshotting. Monotonic kernarg allocation separately keeps old argument storage valid. Successful final cleanup clears `generation->kernel_owners` before marking the generation free and outside `graph_signal_pool_mutex_`; quarantined generations preserve the owners.

Add one eligibility guard before claiming the module/function case: every eligible captured kernel node must have at least one `capturedKernelOwners_` entry. If any is empty, use the established graph path. This covers stale capture state or an unrecognized captured command type instead of publishing a packet whose executable lease was not proven.

v2 has compile evidence only at this checkpoint. Function-changing update, module-unload lifecycle fixtures, and unchanged performance measurements remain separate gates.
