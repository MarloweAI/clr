#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")" && pwd)
: "${ROCM_PATH:=/opt/rocm}"
: "${HIP_ARCH:=gfx950}"
if [[ $# != 1 ]]; then echo 'Usage: build.sh NEW_OUTPUT_DIRECTORY' >&2; exit 2; fi
mkdir "$1"
out=$(cd "$1" && pwd)
"$ROCM_PATH/bin/hipcc" -O3 -std=c++17 --offload-arch="$HIP_ARCH" "$root/waiter/minimal_wait.cpp" -o "$out/waiter"
"$ROCM_PATH/bin/hipcc" -O3 -std=c++17 --offload-arch="$HIP_ARCH" "$root/attention_fork_join/attention_fork_join.cpp" -o "$out/attention_fork_join"
"$ROCM_PATH/bin/hipcc" -O3 -std=c++17 --offload-arch="$HIP_ARCH" "$root/attention_stream_chains/stream_chains.cpp" -o "$out/attention_stream_chains"
"$ROCM_PATH/bin/hipcc" -O3 -std=c++17 --offload-arch="$HIP_ARCH" "$root/llm_streams/main.cpp" -L"$ROCM_PATH/lib" -lrocblas -ldl -o "$out/llm_streams"
