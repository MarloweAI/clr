# Independent source review

Reviewed 2026-09-19 before interpreting any experiment result. This is a static source and contract review; the reviewer did not submit, run, or monitor a GPU job.

## Verdict

PASS for the bounded experiment. The frozen source isolates the proposed fence placement from signal placement, packet topology, dependency edges, reset method, kernel code/resources/arguments, and completion/drain behavior. I found no source-level correctness or causal-comparison blocker.

The verdict is deliberately narrow. It covers the captured, ordered, same-GPU-agent, compute-only Q/K graph checked by this harness. It does not establish a generally valid HIP graph lowering for SDMA packets, host nodes, cross-agent execution, unordered first dispatches, unresolved launch predecessors, or producers whose releases are weaker than the audited scopes.

Frozen `source.json` SHA-256: `66967ed0faacd247a0936c86026bb14221cec574357059f9eb0056e1f5a68cdb`.

Key reviewed hashes recorded by that freeze are:

- `replay.cpp`: `7ca3ae3e351ff8ab471ed4f38c905e0f01747b7ec1280173e8e26debc4cacd46`
- `run.py`: `42589e7f427d085d5f70fdae84688e507c82357dd22d8c0b414708d6ba1384f5`
- `benchmark.py`: `7840b5135166d603e33713b0304d3498fdb7424e86e7443345a40a9fdfb8516f`

## Causal comparison

Modes 0/2 use the same private-host token arena; modes 1/3 use the same GPU-local token arena. Mode selection is `storage = mode % 2`, while only modes 2/3 enable the candidate fence placement. All four modes use cached direct token resets, identical final host signals, identical packet counts, and the same publication and complete-drain path.

Within each matched placement, the only packet differences permitted by construction and checked byte-for-byte by `run.py` are:

| Packet | Modes 0/1 | Matched modes 2/3 |
|---|---|---|
| Main entry barrier | SYSTEM/SYSTEM | NONE/NONE |
| Side entry wait | SYSTEM/NONE | NONE/NONE |
| First kernel on each lane | AGENT/AGENT | SYSTEM/AGENT |
| Remaining kernels | AGENT/AGENT | AGENT/AGENT |
| Final join | SYSTEM/SYSTEM | AGENT/SYSTEM |

Completion-signal substitutions are identical within each matched placement and are required to connect the private replay. The audit reconstructs complete 64-byte barriers from zero, reconstructs every kernel from its captured template, and permits only those completion handles and the listed first-kernel acquire bits. It also checks exact mode 0/2 and mode 1/3 signal receipts, packet counts, graph dependency layers, token/final disjointness, physical placement, allocation ownership, alignment, and both queue wraps.

## Fence contract

The candidate placement is consistent with the audited topology:

1. Each first kernel is ordered after its resolved entry packet and performs a SYSTEM acquire before entering the active phase. This moves external and prior-graph visibility acquisition to the first actual consumer on each lane.
2. Each captured kernel retains its original AGENT release. Later cross-lane steps retain the original AGENT-acquire kernels after their dependency packets, so the existing same-agent producer/consumer chain remains intact.
3. The final join is ordered after the last main-lane kernel and explicitly depends on the last side-lane completion. Its AGENT acquire therefore follows both branches' AGENT releases.
4. The final join retains a SYSTEM release before its ordinary host completion becomes visible. The next graph is ordered after that join, and its first kernels perform SYSTEM acquire.

This relies on the HSA packet-header contract in the pinned ROCr source: an acquire is applied before the packet enters the active phase and exposes prior releases to subsequent dispatch loads on the same kernel agent; a release occurs after dispatch completion but before packet completion and publishes completed dispatch stores at the selected scope (`hsa.h`, lines 2880-2906 in the reviewed ROCr source). The completion signals still provide control dependencies when the intermediate barrier packets use NONE fence scopes; memory visibility is supplied by the adjacent kernel/join fences described above.

## Lifetime, reset, and failure handling

Each replay starts only when no prior replay is in flight. Token values and timestamp words are reset through cached, aligned `hsa_signal_value_t` pointers, followed by `SFENCE` before packet publication. The final host signal is waited with acquire semantics. Reuse is prohibited until that completion is observed and both queue read indices have advanced past their last published packet. Only after that complete drain are token values, guards, and final completions checked. A publication or in-flight failure exits without reclaiming live GPU storage.

These conditions make direct reset and same-arena reuse acceptable for this synchronous diagnostic harness. They are not a lifetime design for overlapping production replays; any runtime port would need generation/in-flight ownership and failure quarantine appropriate to its asynchronous API.

## Evidence required from a result

The audit requires the frozen source and build receipts, exact packet bytes, exact timing row keys, 128 raw and unique profiling records per group, queue index continuity and wrap, complete token counts, valid dispatch timestamps, unchanged kernargs and loaded-library identities, and all numerical checks after poison/change/restore phases and every timed cell. There are 576 timing rows and 4,590 numerical checks across g1 and g50 when both groups complete.

A passing run can answer whether this fence placement changes the matched private-replay cost on this graph. It cannot by itself justify a runtime port. Any favorable result still needs integration evidence for actual HIP lowering, asynchronous lifetime, all supported node types, and visibility tests that exercise the production launch boundaries.
