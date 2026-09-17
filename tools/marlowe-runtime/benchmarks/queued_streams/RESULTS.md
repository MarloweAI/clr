# V9 RC2 queued-work results

Final HIP 43104e17679d8700f1d3f5a66160b63ba3cbd26fba2f46cab5802a58d4bb2115; implementation cab5670.

| Consumers | Off ms | On ms | Change |
|---:|---:|---:|---:|
| 1 | 5.318 | 3.411 | -35.9% |
| 2 | 6.863 | 3.502 | -49.0% |
| 3 | 9.899 | 3.572 | -63.9% |

Three fresh-process rounds. All 5,904 measured operations and their output/dependency checks and the declared headline screen passed. Balanced two-stream depth 16 is 3.159 ms off versus 3.165 ms on. The initially rejected history candidate took 5.941 ms. The final separate traces contain zero queued-attention native packets and 72 fanout packets. Fanout handoff increases while producer/total time falls. Queue-cap 8 and delayed-consumer controls are in the full campaign analysis.
