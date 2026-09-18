# Direct HSA packet wait microbenchmark

Standalone gfx950 diagnostic for producer progress, consumer handoff and independent-queue progress. See [RESULTS.md](RESULTS.md) for the completed pilot, limits and counter plan. These are benchmark sources; they do not change the runtime.

The checked pilot uses one assigned GPU, pinned ROCr 7.2.4 and the existing node2 gpu-profile route from [Slurm PR5](https://github.com/MarloweAI/slurm/pull/5). The helper grants counter access but does not collect counters automatically. This pilot has no counter collector.

Build probes.cpp with hipcc --genco -O2 --offload-arch=gfx950. Use clang-offload-bundler --list and --unbundle to extract the sole gfx950 ELF; hipcc's outer output is an offload bundle. Build packet_wait.cpp with clang++ -O2 -std=c++17, ROCm include/library paths, -lhsa-runtime64 and -pthread. Run packet_wait probes.hsaco OUTPUT_DIRECTORY inside the allocation, then python3 audit.py OUTPUT_DIRECTORY. The directory must exist and be fresh. The frozen launch/build/identity scripts and all source hashes are retained in the v4 path recorded in RESULTS.md.

No HIP runtime should be loaded into the host program. The indirect native instruction buffer requires executable fine-grained host allocation. Keep the original full-width AQL dependency and fences after the native prefix. This is not a portable PM4 API or a firmware modification.
