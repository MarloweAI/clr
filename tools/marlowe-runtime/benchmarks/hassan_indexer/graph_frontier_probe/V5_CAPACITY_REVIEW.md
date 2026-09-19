# v5 hard-cap and prompt-destroy source review

## Verdict

v5 is rejected because `hipGraphExecDestroy` uses the multi-statement `HIP_RETURN` macro as the unbraced body of an `if`. The macro's first assignment is conditional and the remaining error handling and `return` execute unconditionally. Every destroy therefore returns at that line, including successful notification, and skips `ge->release()` plus registry erasure. The observed stale error is consistent with this expansion.

The required control-flow fix is:

```cpp
if (!ge->NotifyGraphFrontiers()) {
  HIP_RETURN(hipErrorLaunchOutOfResources);
}
```

After that fix, I found no additional correctness, deadlock, or lifetime blocker in the pending-command/capacity transition. The remaining items below are production performance and resource-policy risks.

## Capacity and callback progress

The generation's `pending` pointer owns a real intrusive retain installed after every fallible preparation/reset step and before `markPublished()` or the first packet publication. The remainder of the path always publishes a sealed join and enqueues the command. A command that cannot receive a terminal callback therefore does not acquire the pool-owned reference.

At pressure, the pool-owned reference makes `oldest->retain()` safe under `graph_signal_pool_mutex_`. Notification, host wait, and both releases occur after dropping that mutex and before any execution lock is acquired. Releasing the capacity snapshot before the next pool scan is necessary because it may be the final reference that enters `release_owner` and marks the generation free; v5 does this.

The callback detaches `generation->pending` on every terminal status. It marks an error generation quarantined under the pool mutex, unlocks, notifies waiters, and only then releases the detached command reference. This correctly breaks the pool cycle on errors without recycling unsafe storage. The predecessor edge is still released only for exact `CL_COMPLETE`.

ROCclr invokes HIP callbacks before the terminal status compare-exchange. That ordering is safe here:

- `FormSubmissionBatch` still owns the callback object through multiple batch references, so releasing the pool reference inside the callback cannot destroy `self` in place.
- A capacity thread already owns its snapshot reference while blocked in `awaitCompletion()`.
- `awaitCompletion()` is signaled only after the status transition, not by the earlier pool condition notification.

The `busy && pending == nullptr` transition makes progress. The pending callback first notifies while `busy` is still true; a waiter may wake, rescan, and wait again. Final command cleanup later sets `busy = false` under the same mutex and issues a second notification. Because `condition_variable::wait(lock)` atomically releases the pool mutex and sleeps, the final state change cannot be lost between the rescan and wait. Spurious wakes return to the loop. Error transitions are skipped as quarantined, and an all-quarantine pool returns failure rather than waiting forever.

The lock order is consistent:

```text
Run: graph launch mutex -> short pool operations -> no pool -> notify/await
Destroy: graph launch mutex -> pool snapshot -> drop both -> notify
Callback: pool only -> drop pool -> intrusive release
Final cleanup: external/driver cleanup -> pool state update -> graph release
```

No path waits or notifies while holding the pool or a vdev execution lock, and no intrusive command release occurs under the pool mutex. Holding the graph launch mutex across capacity backpressure does not block either terminal callback; it only serializes launch/update/disable for that GraphExec.

## Prompt destroy lifetime

With the braces fix, `NotifyGraphFrontiers()` runs while the public GraphExec reference and registry entry are still live. It snapshots and retains each pool-owned pending command under launch-then-pool locking, then drops both locks before calling `notifyCmdQueue(false)`. Callbacks may detach pending references concurrently, but the snapshot retains keep the command objects alive through notification.

The raw `HostQueue*` in a pending command remains valid without adding a queue reference. A normal application stream cannot finish destruction while an incomplete last/batched command exists: `HostQueue::terminate()` materializes the batch and awaits its last command first. A command that has already reached a terminal status cannot remain in `generation->pending`, because its terminal callback detaches pending before committing that status. Frontier commands remain excluded from force-destroyed internal side streams, where this proof would not apply.

If any notification allocation fails, the braced failure path leaves the user's GraphExec reference and registry membership intact. Notifications already issued during the same pass are harmless; a later destroy retry can finish the remaining commands. On full success, dropping the public reference is safe because every still-asynchronous command owns GraphExec through its launch lease.

## Material risks after the blocker fix

`NotifyGraphFrontiers()` currently notifies every pending command. Several pending commands on one launch queue share one ordered batch: notifying any one appends at the current tail, and the enqueue hook materializes the latest private frontier, retiring all earlier commands. The current loop can therefore allocate up to 1024 redundant notification markers during destroy. This adds latency and makes a partial allocation failure much more likely. A cheaper equivalent is to snapshot one pending command per owning `HostQueue` (prefer the newest serial for clarity), notify those representatives, and retain/release them with the same rules.

The cap is hard only per GraphExec and in units of generations. One generation contains `segments + 2` HSA signals, and the process can own many GraphExec objects. A default of 1024 therefore prevents unbounded growth of one executable graph but is not a global HSA-signal budget. Production qualification still needs a device/process token budget or a much smaller justified per-exec limit.

Capacity pressure deliberately turns an asynchronous graph launch into a host wait. That can produce large latency cliffs, and a sufficiently tight diagnostic limit can deadlock an application whose earlier GPU graph waits for host input that the same blocked thread planned to provide after launch returned. If that workload is in scope, cap exhaustion should fall back to the established ordinary-retirement graph path instead of waiting. With the selected backpressure contract, this is an inherent semantic risk rather than a lock bug in v5.

Pool acquisition scans up to 1024 generations and destroy scans/notifies all pending generations. These costs are off the measured v4 path until pressure or destroy, but they should not be treated as negligible production overhead without dedicated evidence.
