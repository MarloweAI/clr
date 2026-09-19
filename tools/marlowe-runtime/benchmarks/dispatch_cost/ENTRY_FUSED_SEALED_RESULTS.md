# Completed-start control for fused graph entry — job 52048

**The remaining gap is sensitive to incoming-event state.** With immutable fused51980, the b64 two-stream launch-host loss versus stock is3.790% under original timing and1.606% when the begin event completes before launch. KV moves from+1.304% to-0.128%. This supports a frontier-state interaction, without proving that AQL waiting alone causes the difference. Do not use this altered start condition to waive qualification or add application synchronization.

One root-owned node2 GPU; standalone wait/audit; Slurm0:0. All72 processes/49,536 rows/172cells and exact mapped-library/control/binary/reference audits passed; local mirror re-audited. Six Williams orders cover stock, historicald3(min24/placement), and fused51980, each original and completed-start. The measurement binary is copied byte-for-byte from51845; graph bodies, inputs and8retained trials are unchanged. No new runtime was built.

Sealed mode synchronizes the begin event before launch, outside launch_host_us. That event is then hardware-complete at dependency consumption; existing WaitingSignal drops it, while fused ownership and SYSTEM scope remain. GPU elapsed in sealed mode includes the host interval after its start timestamp, so **launch_host_us is the primary metric**. Whole host, begin-wait, GPU and submission times remain in every artifact. These controls change host/GPU overlap and baseline latency, not merely the presence of an AQL wait.

| Target | Original / stock | Sealed / stock | Original / d3 | Sealed / d3 | Median paired change in gap vs stock us |
|---|---:|---:|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | +1.304% | -0.128% | +1.514% | +0.488% | +10.825 |
| b16-balanced, 4_streams | -30.785% | -32.826% | +5.258% | +1.757% | +3.550 |
| b64-balanced, 2_streams | +3.790% | +1.606% | +3.926% | +1.790% | +2.415 |
| b64-balanced, 4_streams | -13.429% | -14.553% | +3.855% | +2.111% | +0.483 |
| b64-skewed, 4_streams | -15.679% | -14.459% | +3.589% | +1.854% | -5.080 |

Paired change in gap is `(fused − baseline)original − (fused − baseline)sealed`, computed separately in each balanced round, then summarized by its median. It is positive in all six rounds for KV and b64 two-stream against both baselines. Skewed four-stream interactions are mixed; no consistent mechanism is inferred there.

| Target | Stock original→sealed us | d3 original→sealed us | Fused original→sealed us |
|---|---:|---:|---:|
| h32-miss256-r1152, gather-parallel | 699.152 → 700.735 | 697.708 → 696.443 | 708.273 → 699.840 |
| b16-balanced, 4_streams | 241.922 → 238.847 | 159.083 → 157.672 | 167.447 → 160.442 |
| b64-balanced, 2_streams | 118.660 → 119.900 | 118.505 → 119.683 | 123.157 → 121.825 |
| b64-balanced, 4_streams | 125.197 → 122.093 | 104.363 → 102.168 | 108.385 → 104.325 |
| b64-skewed, 4_streams | 204.350 → 198.512 | 166.340 → 166.720 | 172.310 → 169.810 |

The b64 two-stream absolute stock gap is4.498us original and1.925us sealed; the median paired difference of gaps is2.415us. KV’s stock gap is9.120us original and-0.895us sealed; the median paired change is10.825us. These paired summaries need not equal differences of aggregate medians.

| All >2% launch-host losses | Cell | Loss |
|---|---|---:|
| fused-0_vs_stock-0 | experts, b16-balanced, 2_streams, total, graph | +2.392% |
| fused-0_vs_stock-0 | experts, b64-balanced, 2_streams, total, graph | +3.790% |
| fused-0_vs_d3-0 | experts, b16-balanced, 4_streams, total, graph | +5.258% |
| fused-0_vs_d3-0 | experts, b64-balanced, 2_streams, total, graph | +3.926% |
| fused-0_vs_d3-0 | experts, b64-balanced, 4_streams, total, graph | +3.855% |
| fused-0_vs_d3-0 | experts, b64-skewed, 4_streams, total, graph | +3.589% |
| fused-1_vs_d3-1 | experts, b64-balanced, 4_streams, total, graph | +2.111% |

Across172cells, sealed fused has no >2% launch-host loss versus stock and one2.111% loss versusd3 (b64 balanced four-stream). Original mode has two losses versusstock and four versusd3. A small residual therefore remains even when the incoming event is complete; pending dependence cannot be the sole explanation.

The next useful evidence is the actual entry dependency state at consumption and whether a wait packet is emitted. The earlier51871 observer sampled the predecessor before graph submission, not at this later point. WaitingSignal already filters ready signals, so adding a redundant check is not an optimization. Keep dependency, visibility and lifetime requirements while investigating that remaining interval; no further source change is selected by this result.

Raw remote root: `/workspace/home/sasha/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-fused-sealed-j52048`; local mirror: `/home/sashawork/dev/amd-runtime-production/iterations/stream-wait-calibration-20260918/entry-fused-sealed-j52048`. `contrasts.json` contains every metric, absolute median, per-round contrast and state interaction.
