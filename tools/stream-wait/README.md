# gfx950 stream-wait candidate

This branch recovers the fused RC1 runtime in ten C++ source/header files. It is
experimental and defaults both optional policies off. Its core source matches the
recovered HiSparse candidate; rebuilding changes library identity and needs a new
qualification. Fresh GLM and rebuilt-byte qualification are pending.

The implementation runs in the host HIP/CLR runtime. For eligible cross-queue waits
it emits a native command-processor prewait followed by the ordinary AQL barrier.
The original barrier retains the full signal condition, fences and notification.
No application kernels, driver or firmware are replaced. The prewait requires at
least 24 actual pending independent producer kernels, checks current queue progress,
and falls back on unavailable instruction storage or a contended queue-pool lock.
Its signal ABI and packet encoding are specific to gfx950 and ROCr 7.2.4.

Segmented graphs also preserve the launch-stream predecessor at side roots, join
actual submitted tails, and retire published work on partial errors. Eligible flat
kernel graphs import the predecessor into their first packet batch, avoiding a
separate entry marker. A bounded spare stream helps avoid launch-queue collisions.
These graph changes apply with either setting of the optional flags. Node-count
placement is a separate opt-in policy and changes assignment, not submission order.
Device-changing setters invalidate its cached eligibility and fused-entry eligibility.

| Comparison arm | Libraries | Native prewait | Node-count placement |
| --- | --- | ---: | ---: |
| Stock | Original container libraries | Original implementation | Original implementation |
| Candidate off | This package | 0 | 0 |
| Candidate on | This package | 1 | 1 |

The off arm retains the graph correctness and entry changes above. Only restoring
the original container libraries is a complete runtime rollback.

## Build and package

Use the ROCm 7.2.4 toolchain with matching HIP headers at
`bc9af25177f96c0fea93198b89cf4c3cf08f3ea3`. The recovered build environment is
`lmsysorg_sglang-rocm_v0.5.18-rocm724-mi35x-20260903.sqsh`, SHA256
`43b9e7ae1e56863cd48be7af67958b8dd7ff833a907f13763883cd668a13ce06`.
The packager requires ROCr SHA256
`b8cdfe93d343649a35c1daf73a0a3a6840f09379ebeee9be65670461ffea43f4`.
It copies libraries, records their hashes and source identities, and leaves the host
installation untouched. Supply a clean, committed source checkout and a new work path:

```sh
export HIP_COMMON_DIR=/absolute/path/to/pinned/HIP
export RUNTIME_WORK_DIR=/absolute/path/to/new/build-work
export RUNTIME_BUILD_BASE_IMAGE=squashfs:sha256:43b9e7ae1e56863cd48be7af67958b8dd7ff833a907f13763883cd668a13ce06
bash tools/stream-wait/build.sh
```

Start every serving process through the package wrapper before importing PyTorch:

```sh
AMD_DIRECT_DISPATCH=1 GPU_NATIVE_EVENT_WAIT=1 GPU_GRAPH_NODE_COUNT_PLACEMENT=1 \
GPU_NATIVE_EVENT_TRACE=0 GPU_MAX_HW_QUEUES=4 GPU_STREAMOPS_CP_WAIT=0 \
/absolute/path/to/build-work/package/run python your_server.py
```

The wrapper verifies packaged files, preloads the matching HIP/HSA pair, and preserves
the command arguments. `package/run python package/verify.py` checks actual PyTorch
mappings and gfx950 devices; `python package/verify.py --files-only` needs no GPU.
Runtime selection and both flags must be inherited by every worker. Trace stays off
for timing. Remove the wrapper and overlay environment to restore container stock.

## Qualification and scope

Correctness fixtures live in `tests/stream_wait`; workload kernels and runners are
separate under `microbenchmarks/stream_wait`. The latter includes Hassan's unchanged
Q/K kernels and scheduler. Source equivalence, successful compilation and passing
microbenchmarks do not prove model qualification. Require matched HiSparse C1/C4,
standard resident GLM without HiSparse, correctness, and actual mapped-library audits
before deployment. Preserve all trials and label historical evidence separately.

The newer V10 graph-frontier experiment is a different implementation and is absent
from this branch. Its performance results do not qualify this recovered runtime.
