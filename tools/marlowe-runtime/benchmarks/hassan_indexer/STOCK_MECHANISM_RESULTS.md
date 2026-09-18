# Why stock gets no Q/K stream speedup — 2026-09-18

The completed [warm timeline follow-up, job 53817](WARM_TIMELINE_RESULTS.md), shows that grouped stock Q/K does overlap, but the larger interval before the next pair cancels the saving.

Stock-only job53773 completed and passed independent local audit:48fresh processes,384retained timing rows,3,024numerical checks, four reversed/rotated orders. The fixed original AITER/FlyDSL kernels, dispatch, tensor dimensions/strides, scheduler and stock HIP/HSA bytes are unchanged. This controlled diagnostic varies capture-stream warmup and graph grouping; it is a separate protocol from the historical benchmark gate.

## A real extraction artifact, but not the missing-speedup explanation

The original extraction warms kernels on ordinary main/side streams, then captures on a fresh stream. AITER caches split-K semaphore and signal tensors by `(device,stream)`; its first use of the new capture stream executes two `torch.zeros((256,),int32)` initializations inside capture. DOT confirms two integer fill kernels preceding Q, while K's side stream is already initialized. They replay on every graph invocation. Prewarming the actual capture stream removes both fills, verified for every process, without changing either projection kernel. Initial and changed-input numerical checks pass.

Hassan's original SGLang capture path behaves differently. At the frozen base commit [fb91baed](https://github.com/sgl-project/sglang/tree/fb91baedab3e1de668d6e8f391ccd81cab9e9acd), `DecodeCudaGraphRunner.capture()` enters `graph_capture(stream=...)`; `GroupCoordinator.graph_capture()` sets that stream current; `FullCudaGraphBackend.capture_one()` performs two forward warmups before capturing on the same stream. His patch preserves those warmups. Source therefore predicts the initialization occurs before capture in serving. The two-fill artifact belongs to our extraction; it is not evidence of this defect in Hassan's serving run. No original serving graph census was collected in this diagnostic.

| Stock setup | Serial Q+K us | Two-stream Q+K us | Two-stream change |
|---|---:|---:|---:|
|Original cold capture,1pair/graph|19.320126|19.945755|+3.238%|
|Prewarmed capture,1pair/graph|13.630045|14.201861|+4.195%|
|Prewarmed capture,10pairs/graph|9.236500|11.728781|+26.983%|
|Prewarmed capture,50pairs/graph|8.857987|10.057577|+13.542%|

Warm capture cuts the event graph28.80% (19.946→14.202us), but still loses4.20% to serial. All four process rounds lose; grouping10or50pairs also loses in every round. Both GPU-event and total-host metrics agree. Grouping changes output buffers and graph dependencies as well as host launch count, so it is not a clean subtraction of host-launch cost. Every timed window contains200projection units, eight retained trials; repeated weights remain warm and are not a full-model cache-working-set reproduction.

Q-only and K-only warm single-kernel graphs are9.166500and9.212152us. These include their own graph entry/completion overhead; summing them or calling their difference “kernel time” would be misleading. The follow-up warm timeline additionally groups isolated Q/K50times and calibrates the existing wave probe to study actual overlap.

## First-principles constraints

The actual workload is four-row Q/K projection, not an entire large attention kernel. Q reads a16MiB weight matrix and K1.5MiB; both compute from BF16 inputs with16-row kernel tiles. Q has256CTAs, K24; both use128threads/CTA,61,440LDS bytes and no scratch. Exact-ELF SDK checks53002 permit two blocks/CU on the measured256-CU MI355X. This allows co-residency; it does not establish actual simultaneous issue or bandwidth headroom. [AMD's hardware specifications](https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x.html) confirm256CUs.

Both kernels use matrix instructions, shared-memory staging, memory loads, split-K coordination and output atomics. The source includes a signal spin before atomic output accumulation. They share resource types rather than offering compute-versus-DMA complementarity. Nevertheless, Q having10.67times K's arithmetic is not a valid10% speedup ceiling: split-K parallelism and fixed latency make durations much closer. A large idealized overlap benefit must be assessed from measured duration and critical path.

Previous [calibrated cold-graph traces](TIMESTAMP_RESULTS.md) showed K advancing across replay ordinals on stock and longer Q/K envelopes when the corrected runtime aligned execution. Those results are not a warm-graph explanation; probe perturbation and captured fills remain material. Hassan's archived serving traces report0/32positive overlaps of selected Q/K dispatch intervals, a limited selection rather than a whole-model census.

## Provenance and limits

Job53773 uses stock HIP f1043337461c8e54ee135e95fa979a7d0e4344676ad5b0554652f844f8f098ac and HSA b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4. Spec SHA256:211a62d495a71ce2957c235fe677f9dcb8edf2e21657db904eda7eaa22b578da; manifest SHA256:2c94e73e43489a25d8f7c66247cc95a47421b89b08f87e3ea2da83bfdf80ac0d. All sources, graph node/grids, library/control/data identities and artifacts are audited. Correctness is bounded synthetic-input NRMS/NMAX screening, not full-model certification.

Local raw/source root:`/home/sashawork/dev/amd-runtime-production/iterations/hassan-stock-mechanism-20260918`; remote mirror has `/workspace/home/sasha/amd-runtime-production/iterations/` prefix. `run.py --out results-j53773 --audit` independently rechecks artifacts. The `original-context/` directory retains the frozen SGLang sources and Hassan patch used for source analysis. Existing cold-capture benchmarks and results remain unchanged; this report does not silently replace their baselines. No runtime build, promotion, original model rerun or production gap investigation occurred.
