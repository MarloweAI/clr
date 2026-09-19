# Stream synchronization microbenchmarks

The workload kernels are preserved from the stream investigation. Each experiment
uses one GPU, fresh processes with rotated stock/off/on order, deterministic inputs,
independent numerical checks and retained raw samples. No full model is loaded.

| Suite | Workload | Comparison |
| --- | --- | --- |
| `waiter` | 2,048 dependent tiny kernels | No waiter, pending event waiter, ready waiter |
| `attention_fork_join` | Data-dependent query, two partial attention branches, softmax merge | Serial, two streams, wider single launch |
| `attention_stream_chains` | Balanced/uneven attention with dependent continuations | Serial, two/four streams, wider single launch |
| `attention_fetch` | Resident attention plus small scattered host KV restores | Serial/two streams; mapped-host gather/per-record copies |
| `pipeline` | Dependent layers, two restore buffers and small D2H backups | Serial/shared/separate transfer streams |
| `experts` | Four BF16 MLPs and weighted merge | One/two/four streams and batched GEMM |
| `mixed` | MLP alongside a KV scan; two scans as contention control | Serial/concurrent |
| `grouped_prefetch` | GPU planning anchor followed by three KV prefetches | Prefetch off/on with real dependencies |
| `hassan` | Original BF16 Q/K GEMMs and event scheduler | Serial/two streams; warm one-pair and synthetic 50-pair graphs |

Hassan's projection shapes, strides, split-K choices and FlyDSL solutions are pinned
in `hassan/projection-dispatch.json`; original source provenance is in
`hassan/provenance.json`. Q uses 16 KiB input, 16 MiB weights and 32 KiB output;
K uses 48 KiB input, 1.5 MiB weights and 1 KiB output. The actual capture stream is
warmed, matching serving and excluding lazy buffer fills. The exact AITER Python
source hashes must match `hassan/workload.json`. This is a projection extraction;
it does not measure Hassan's entire serving application. Kernels are unchanged.

## Run

Inside a one-GPU gfx950 allocation with ROCm 7.2.4 and the pinned AITER environment:

```sh
bash microbenchmarks/stream_wait/build.sh /absolute/path/to/new-binaries
python microbenchmarks/stream_wait/run.py \
  --candidate-lib /absolute/path/to/candidate/lib \
  --stock-lib /opt/rocm/lib --bin /absolute/path/to/new-binaries \
  --output /absolute/path/to/new-results
```

`--reference-lib /path/to/recovered/lib --rounds 4` adds the exact recovered
runtime as an enabled fourth arm, to check rebuilt-byte preservation.
`--cases` selects suites explicitly. `--cases hassan` does not require `--bin`.
The runner fixes both optional runtime flags to 0/0 or 1/1, uses queue cap four,
keeps runtime traces off, verifies actual mapped libraries, and records source,
binary, input and reference identities. It leaves CPU affinity inherited. Three
rounds are independent processes, not three samples from one process. Observation
timeouts request inspection and keep waiting for the same process.

GPU event intervals include joins and device idle intervals. Host completion and
submission times remain separate where provided. Embedded attention timestamps
measure execution envelopes rather than CU utilization. Sparse mapped-host restore
uses GPU compute resources; it is distinct from DMA. Wide/batched controls change
launch geometry and should not be attributed solely to stream synchronization.

`COMPLETE` establishes requested process coverage, identities and numerical checks.
It is not a performance verdict. Compare medians of per-process medians, preserve
all raw trials, and report stock-relative regressions as well as improvements.
The microbenchmark stock library path is recorded explicitly; the PyTorch libraries
in a serving image can be different and require their own matched control.

Fresh recovered-runtime results and the separate historical checkpoint will be
recorded after the qualification runs. No V10 gain is attributed to this branch.
