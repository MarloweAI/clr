# Initial stock/current comparison — job 52868

The extracted workload catches a clear current-runtime regression: event-based Q/K graph replay is **11.61% slower than stock**, while serial replay is neutral. The performance screen fails. This candidate is not qualified for this workload.

Job52868 completed on node2/one GPU. Four Williams rounds, four treatments, eight trials, 200 invocations per trial, both eager and graph: 16 processes and 256 retained timing rows. All 320 numerical/changed-input/burst checks passed. Independent audit reproduced every contrast and verified all source/artifact hashes, 16 unique PIDs, all three HIP/HSA mapping phases per process, exact dispatch configurations and identical tensor bytes. Every current event-graph trial exceeds every stock event-graph trial (32 trials per runtime).

Amortized time per Q/K pair, microseconds; lower is better. GPU span includes submission-induced device idle time.

| Invocation | Schedule | Stock GPU | Current GPU | Change | Stock host | Current host |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Graph | Serial | 19.096984 | 19.106085 | +0.048% | 19.136405 | 19.146005 |
| Graph | Events | 19.833929 | 22.136983 | **+11.612%** | 19.878605 | 22.178643 |
| Eager | Serial | 32.783136 | 32.216816 | −1.727% | 32.820258 | 32.254819 |
| Eager | Events | 50.642661 | 50.625476 | −0.034% | 50.683488 | 50.666061 |

Graph-events GPU losses per round: 11.8851%, 11.0371%, 11.2793%, 11.5035%. Host loss is 11.5704%; submission is effectively unchanged (stock4.608613/current4.605714us). The matching GPU/host penalty favors investigating completion behavior over total CPU enqueue cost, but does not identify native waits, physical overlap, or a particular correctness repair. Eager spans track CPU submission closely and can hide shorter device penalties.

Events also lose to serial within both runtimes: stock+3.859%, current+15.864% for graph replay. The test does not establish that these two GEMMs overlap physically or ought to be faster with streams. The required runtime comparison remains current versus stock for each fixed schedule.

Stock HIP SHA256: `f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac`.
Current qualified-spare diagnostic HIP: `cab16effd6d3b4af9205437fb0e1249e68cf87cb4379d77c737d12786c7bd6ff`.
Both use HSA `b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
Current has native wait, node-count placement and selective spare enabled; stock native/placement controls are off. No older experimental runtime was tested.

The scheduler is copied unchanged from Hassan's pinned repository. Tensor shapes, strides, BF16 types and exact FlyDSL choices match its contract. Values are seeded synthetic tensors. This is an extracted projection-pair test, not the original TP8 serving endpoint; no full-model result or match to the magnitude of Hassan's serving regression is claimed.

Frozen spec SHA256: `6ddfd7171b7cb3291db517955440d22ca4c3e2013622e105e5bfa9d31c22891b`.
Frozen source and raw data: `iterations/hassan-qk-micro-20260918/bench`, `spec.json`, `results-j52868`.
`passed` in the saved summary denotes the data audit; the separate `performance_screen.passed` is false. All trials are retained. No runtime is promoted.

## Same-byte native/placement attribution — job 52887

The exact same benchmark and cab16 runtime were tested with native wait and node-count placement toggled independently, events schedule throughout. All16processes/256timingrows/320checks passed local and independent artifact/identity/correctness audit.

| Native wait | Placement | Graph GPU us | Graph host us |
| --- | --- | ---: | ---: |
| Off | Off | 22.134085 | 22.175755 |
| Off | On | 22.116285 | 22.158493 |
| On | Off | 22.136234 | 22.177230 |
| On | On | 22.148484 | 22.191668 |

Aggregate GPU spread is0.0322us; every registered graph contrast stays below0.63% absolute in every round. Neither toggle removes the22.1us behavior. Both-off retains candidate-common code and enabled selective-spare controls; it is not stock. This run has no contemporaneous stock arm and does not independently establish the stock gap or attribute it to either correctness repair. Permission to emit native waits does not prove actual native emission.

The private diagnostic runner only generalizes treatment labels/comparison terms; benchmark.py is byte-identical to52868. Data and external-source identities match. Frozen spec `2825f05a2bd700e1fcf5ce0a7cf684611f22dbafad2cee0c8563da8c0a6d0336`; raw `iterations/hassan-qk-micro-20260918/controls-j52887`. No performance qualification is claimed.

## Calibrated execution timeline

[Timestamp calibration and resource report](TIMESTAMP_RESULTS.md) records a repeatable scheduling difference in the instrumented 200-replay burst: stock K runs ahead across invocations, whereas current Q/K remain aligned. Probe overhead is measurable and runtime-dependent; this does not quantitatively explain the original gap or transfer to the expert single-replay benchmark. The unchanged original kernels still regress in the new matched comparison.

[Physical queue-cap control](QUEUE_CAP_RESULTS.md) rejects cap1 as a remedy: it retains two logical streams and worsens current graph replay from22.16 to31.65us. A separate logical-stream mapping diagnostic is required to test whether removing unnecessary graph dependencies helps.
