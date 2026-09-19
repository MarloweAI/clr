# Stream and segmented-graph correctness fixtures

`native_pool_pressure.cpp` checks pending-wait submission progress.
`eligible_pool_pressure.cpp` exercises the admitted native instruction pool.
`pytorch_minimal_wait.py` checks the PyTorch event path.
`graph_entry_ordering.cpp`, `graph_tail_lifecycle.cpp` and
`graph_terminal_completion.cpp` cover launch predecessors, graph lifetime and
completion of all submitted graph tails. The entry transfer/publication/disabled-root
fixtures cover copies, host visibility and changing graph nodes.
`graph_fused_inspect.cpp` and `graph_fused_invalidation.cpp` form the two-device
cache-invalidation fixture; compile the host inspector using the runtime build
flags for `hip_graph_internal.cpp`, then link it with the HIP fixture. Preserve the fixture's command-line
requirements; these are correctness checks, not timing results.

Compile C++ fixtures with `hipcc -O2 -std=c++17 --offload-arch=gfx950` and execute
through the package wrapper. Run all four native-wait/node-placement flag pairs,
including 0/0. Use the required GPU count and keep mapped-library receipts. The
historical investigation additionally contains multi-device cache-invalidation,
partial-error and broader publication fixtures; their old results do not qualify
newly rebuilt bytes.
