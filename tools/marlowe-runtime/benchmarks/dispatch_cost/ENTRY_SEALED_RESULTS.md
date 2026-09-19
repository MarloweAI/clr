# Completed start-event diagnostic — job 51845

Explicitly completing the begin event before the unchanged graph launch removes the small-KV relative loss, but expert losses remain. This establishes sensitivity to the launch frontier and scheduling state; it does not establish a timestamp-accounting error or qualify a runtime.

One node2 GPU, root-owned standalone submission/monitoring. Slurm 0:0; all 72 processes, 49,536 rows and 172 cells passed frozen-source, library/control/map, row, correctness and raw-hash audits. The downloaded mirror re-audits. No runtime bytes changed. Graph bodies, capture, references, warmups and trial counts stayed unchanged. A single new benchmark binary changes timing instrumentation and its receipt/schema only. Six Williams orders balance all six runtime/timing combinations. All trials are retained.

The primary metric is host time from just before graph launch through end-event synchronization. It excludes the explicitly measured begin-event wait. Original GPU and whole-host measurements remain recorded. Sealed GPU elapsed includes the host gap after the begin timestamp, so comparing original versus sealed GPU durations alone would be misleading.

| Graph target | RC2/stock, original | RC2/stock, completed start | RC2/d3, original | RC2/d3, completed start |
|---|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | +3.155% | +0.078% | +2.763% | -0.098% |
| b16-balanced, 4_streams | -28.275% | -30.583% | +8.075% | +5.396% |
| b64-balanced, 2_streams | +3.638% | +2.116% | +4.540% | +2.537% |
| b64-balanced, 4_streams | -9.132% | -11.233% | +9.383% | +6.384% |
| b64-skewed, 4_streams | -13.867% | -14.459% | +4.341% | +5.474% |

For KV, stock launch-to-completion changes from 696.785 to 701.063 us while RC2 changes from 718.770 to 701.608 us. Thus relative convergence reflects both sides changing, predominantly RC2 improving. It is not merely moving a GPU timestamp. The begin-event wait itself is about 7.6 us and remains in the recorded whole-host result. No host synchronization is proposed as an application optimization.

The two-stream expert residual remains +2.116% versus stock and +2.537% versus d3 with a completed start. Every expert target remains slower than d3 in all six completed-start rounds. The original failed qualification gates remain in force; these controlled timings cannot replace them.

Next discriminator: observe the retained launch predecessor before any notification, graph submission or logging. Count hardware readiness separately from CPU completion, including hardware-ready/CPU-pending observations. Ordinary recorded events can retain submitted CPU status after hardware completion, so a CPU-only completion guard may miss opportunities. Observations must be untimed and treated as sequential samples, not an atomic snapshot.

If hardware-ready frontiers are common, review a completed-frontier path that conservatively supplies SYSTEM acquire on the first actual captured batch. Pending/unknown frontiers retain ordinary dependency markers. Batch capture, disabled roots, partial errors and publication remain required proof obligations. Dependency fusion for pending producers is a larger change and should follow evidence.

Raw root `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-sealed-j51845`; local mirror `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-sealed-j51845`. Complete original/sealed GPU, whole-host, submission, launch-host and begin-wait measurements are in `contrasts.json`.
