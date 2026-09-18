# Segmented graph completion checks

These are correctness fixtures, not performance benchmarks. They preserve the
observation made after launch-stream synchronization before the later device drain.
The device drain establishes eventual arithmetic correctness; it cannot erase an
earlier completion failure.

`graph_terminal_completion.cpp` uses widths6/9/15/23, three creation orders and
four replays. Independent branches contain8–16 kernels, retaining segmented
execution under the runtime's normal scheduling heuristic. It reports48 rows.
`graph_tail_lifecycle.cpp` adds48 observations across direct replay, graph clone,
kernel-parameter update, executable update, child graph and child-parameter update.
Epochs detect stale parameters. Both source graphs are destroyed before clone
replay; executable-update replacements are destroyed before launch. Stream order
A→A→B→A tests repeated launch, switch and switch-back.

Compile using the tested gfx950 toolchain within an allocated GPU job:

```bash
hipcc -O2 -std=c++17 --offload-arch=gfx950 graph_terminal_completion.cpp -o completion
hipcc -O2 -std=c++17 --offload-arch=gfx950 graph_tail_lifecycle.cpp -o lifecycle
GPU_MAX_HW_QUEUES=4 DEBUG_HIP_FORCE_GRAPH_QUEUES=4 DEBUG_HIP_GRAPH_SEGMENT_SCHEDULING=1 ./completion
GPU_MAX_HW_QUEUES=4 ./lifecycle
```

Select and verify the intended runtime overlay before running; merely compiling
against headers does not establish which shared library was loaded. Completion
requires every `ordered_complete`/`correct` field to be1, not just eventual output.
The original fixture deliberately retains failures in CSV without forcing nonzero
exit, so its driver must inspect those fields. The lifecycle fixture fails on the
first incorrect observation; its driver additionally requires all48 labeled rows.

## Observed bug and correction

The original final join picked one segment per logical stream by greatest
*dependency level*. Several independent segments can occupy that same level;
unordered-map traversal does not identify the last enqueue. Track the actual last
successfully enqueued accumulate command per logical stream instead. Tail aliases
are non-owning; original per-segment ownership, wait-list retains and cleanup stay.

Job51007 reproduced premature completion at width15/creation-order0 with the
placement-only diagnostic: all4 iterations, traced and untraced, mask5632
(branches9,10,12), while eventual arithmetic was correct. The failed job performed
no performance timings. The previously unconfirmed endpoint concern is therefore
an observed defect exposed by that diagnostic; stock/legacy placement did not
reproduce it in the earlier fixture runs.

Job51020 kept old and corrected bytes in one allocation. Old placement failed4/48
with native waiting off, guarded256, threshold24 and traced24. Corrected bytes
passed768 observations across caps1/4/8 and scheduling controls.720 untimed receipts
verified the selected endpoint against actual per-logical-stream submission order.
Do not merge streams merely because they share a physical queue.

The corrected generic algorithm is in the PR source. Experimental placement/rank
controls and trace receipts remain in external diagnostic patches. The measured
candidate was HIPd3b22a17535ac59dae2785661acbf593eba7394c1d8965c9e0356e1389fc35f3,
HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4,
basecab5670 plus patch38a91fb038a72604057955a7ab7b140d808c5b8543d6d5aa31a88a88648e6dfc.
This is validation of the correction in diagnostic bytes, not a new production
release of this PR commit.

Job51046 passed75 exact-byte framework/lifecycle processes, including3,200 PyTorch
rows and480 lifecycle rows over native off/guarded/24 and placement/BOTH controls.
The placement lifecycle trace contained752 mapping,192 endpoint and16 assignment
receipts. Child cases cover parameter propagation and executable lifetime; the
current child path is internally single-stream and does not prove nested
cross-stream joins. Logical launch-stream changes do not imply different physical
queues at cap1. Parameter updates preserve topology and kernel functions.

All raw data and strict audits are preserved in iteration
`stream-wait-calibration-20260918`, roots `graph-placement-terminal-j51007`,
`graph-tail-gate-j51020`, `graph-tail-terminal-j51026`, and
`graph-tail-checks-j51046`. Runtime production qualification remains false.
