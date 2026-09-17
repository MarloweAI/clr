# LLM stream microbenchmarks

See [the first-round results](RESULTS.md) for measured runtimes, the graph queue fix and package status.

One GPU, real arithmetic and data movement, eager HIP launches and captured graphs. This suite runs no model. It compares the same executable with stock ROCm 7.2.4, PR1 v8 disabled/enabled, the prior experimental c82cf08 package, and optionally a revised runtime.

## Workloads

| Case | Work and shapes | Schedules |
|---|---|---|
| `attention_fetch` | Resident attention plus scattered pinned-host KV restore, partial attention and stable softmax merge. 2,048 attended tokens; 32/128 heads; 32/128/256 misses. BF16 1,152-byte records; secondary 584-byte quantized records. | Serial versus two streams; 16-block, 1,024-thread gather versus one asynchronous copy per record. |
| `pipeline` | Eight/32 dependent layers with query feedback, two reusable restore buffers, known next-layer miss plan, 32/128 misses, and 1,152/4,608-byte D2H backups. | Serial, shared H2D/D2H stream, separate H2D and D2H streams. |
| `experts` | Four actual BF16 rocBLAS MLPs, 4,096-wide matrices, SiLU, top-2 routing and weighted merge; batches 16/64, balanced/skewed. | One/two/four streams; strided-batched GEMM control for balanced routing. |
| `mixed` | One 512-token matrix MLP plus an independent uniform-weight attention V reduction across eight requests with 65,536 tokens each; 604 MB KV allocation per scan. | Serial versus concurrent; two independent KV scans as a shared-resource control. |

The attention kernel implements QK, online softmax and weighted V, but is not a tuned FlashAttention replacement. Its grid is intentionally small because these decode shapes supply few independent heads. The MLP uses structured rank-one weights to enable an independent CPU reference, but executes full dense GEMMs. The bandwidth case omits QK and uses uniform weights explicitly; do not describe it as full attention. Byte counts for the scan count useful V data, excluding padding and intermediate traffic.

Sparse restore uses a GPU kernel reading mapped pinned host memory, like the retained HiSparse path. It consumes compute resources and is not equivalent to DMA. The per-record memcpy control has CPU-known addresses; it does not simulate GPU planning or a device-to-host planning round trip. All memory allocation, pinning, initialization, reference generation, graph instantiation and warmup are outside measured intervals.

## Run

Inside the authorized one-GPU allocation and ROCm 7.2.4 image:

```sh
/opt/rocm/bin/hipcc -O3 -std=c++17 --offload-arch=gfx950 main.cpp \
  -I/opt/rocm/include -L/opt/rocm/lib -lrocblas -ldl -o llm_streams
python3 run.py --binary ./llm_streams \
  --candidate-lib /path/to/exact-v8/lib \
  --experimental-lib /path/to/c82cf08/lib \
  --output /path/to/new-results --rounds 3 --trials 12
python3 analyze.py /path/to/new-results
```

An optional `--revised-lib` adds a fifth runtime, retaining exact v8 as a contemporaneous control. All library directories must contain HIP and HSA. The runner verifies actual mapped hashes and experimental API controls, retains failed attempts, requires an unused output directory and rotates runtime order across fresh processes. It does not change CPU affinity. The four explicit streams use the common `GPU_MAX_HW_QUEUES=4` setting. Record any queue-cap ablation separately.

## Correctness and timing

Full schedules alternate within each trial and check outputs against independent CPU arithmetic. Buffers and output are poisoned before replay; the pipeline checks query feedback and every layer's host backup. Reference files are generated once from deterministic inputs, then shared by every runtime. Keep them with their hashes; do not reuse references from a changed producer.

Primary timing is a GPU event interval including the complete join. Host submission and completion times are retained separately. Each row reports median of fresh-process medians; raw trials are never trimmed. Isolated stages use the same kernels and addresses, but their cache/clock state may differ from combined execution. Concurrent stage timing requires a separate profiler pass; profiling results must not replace unprofiled timing.

`expected_us` is an optimistic no-interference estimate from stock isolated stages and the actual dependency DAG. It is neither a calibrated runtime prediction nor a universal lower bound. For attention it is `max(resident, copy + missed_attention) + merge`; for experts, the longest assigned expert chain plus merge; for mixed work, the longer branch. The pipeline model includes two-buffer reuse and shared-copy-stream ordering. Batched GEMM changes kernel geometry and therefore has no estimate derived from the independent-expert DAG.

Bandwidth and compute contention can prevent ideal overlap. Two KV scans are a contention control, not proof that one scan saturates peak HBM. MI355X has 256 CUs, 256 MB last-level cache and 8 TB/s peak HBM bandwidth ([AMD datasheet](https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/product-briefs/amd-instinct-mi355x-gpu-brochure.pdf)); compare measured useful bandwidth with the hardware limit without treating peak as achieved.

The previous experimental runtime also changes graph scheduling, marker policy, spare queue selection and native-wait policy. Differences against it are whole-package comparisons. V8 on/off isolates native-wait enablement. A matching microbenchmark can identify a mechanism worth testing, but cannot establish the cause or size of the reported full-model regression.
