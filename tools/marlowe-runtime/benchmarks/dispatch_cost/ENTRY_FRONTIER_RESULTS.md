# Untimed graph-entry readiness — job 51871

An already-completed-frontier optimization has no observed opportunity at the sampled entry point in these original-mode microbenchmarks: **0/256** predecessors were hardware-ready. The completed-start positive controls were **256/256** hardware-ready, yet all still had pending CPU status. Do not implement a CPU-completion shortcut or assume the controlled result translates into a useful ready fast path.

Fresh trace-only RC2 HIP `12307867311100701be013ac30bc6cb79a60e8cbcddec7be898d027d88372d32`, HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`. Full base-relative source diff `07247b822eb37311734c74d62f54bee1f9f27c56e6d3b2bc84e7b57e85540258`. Root standalone job on one node2 GPU; Slurm 0:0; downloaded artifacts re-audit. Two unchanged entry/publication correctness probes and eight observation processes passed. All 512 expected records are present.

| Suite / topology | Original samples | Original HW ready | Completed-start samples | Completed-start HW ready | Completed-start CPU complete |
|---|---:|---:|---:|---:|---:|
| attention_fetch, mixed-copy, 2 roots | 80 | 0 | 80 | 80 | 0 |
| attention_fetch, kernel-only, 2 roots | 80 | 0 | 80 | 80 | 0 |
| experts, kernel-only, 2 roots | 48 | 0 | 48 | 48 | 0 |
| experts, kernel-only, 4 roots | 48 | 0 | 48 | 48 | 0 |

The observer samples immediately after retaining the launch predecessor, before notification, wait-list creation, qualification scanning or graph submission. It records CPU status before and after a nonblocking hardware-ready query; graph classification occurs afterward, and copied observations print on function exit after submission. These are sequential observations, not an atomic snapshot. No latency printed by this traced binary is accepted as performance evidence. Trace overhead can affect later scheduling.

All original-mode observations had a present hardware signal and were not ready. All positive-control observations were hardware-ready while CPU status remained pending. This matches recorded events using nonflushing commands: GPU completion need not retire the CPU command immediately. The existing retained event owns the direct/notification signal and prevents pool reuse during observation.

Next design question: reduce the cost of a pending launch dependency while preserving the complete wait and memory-publication contract. Compare a graph-entry-specific native-prewait cost policy with dependency submission integrated into the first captured batch. The former must distinguish compute producers from SDMA, retain physical-queue/signal/pool guards and keep the original AQL barrier; the latter adds ownership, disabled-root and partial-submission obligations. A global cost bypass remains rejected by prior regressions. No new production policy is selected by these counts.

Raw root `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-frontier-j51871`; local mirror `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-frontier-j51871`. Counts and per-process coverage are in `observations.json`.
