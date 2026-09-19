#!/usr/bin/env bash
set -euo pipefail
recipe=$(cd "$(dirname "$0")" && pwd)
source=$(git -C "$recipe" rev-parse --show-toplevel)
: "${RUNTIME_WORK_DIR:?Use a new build directory outside the checkout}"
: "${HIP_COMMON_DIR:?Supply clean HIP headers at bc9af25177f96c0fea93198b89cf4c3cf08f3ea3}"
: "${RUNTIME_BUILD_BASE_IMAGE:?Record the immutable ROCm build image identity}"
: "${ROCM_PATH:=/opt/rocm}"
: "${RUNTIME_BUILD_JOBS:=8}"
export RUNTIME_BUILD_BASE_IMAGE
[[ -z "$(git -C "$source" status --porcelain)" ]]
[[ "$(git -C "$HIP_COMMON_DIR" rev-parse HEAD)" == bc9af25177f96c0fea93198b89cf4c3cf08f3ea3 ]]
[[ -z "$(git -C "$HIP_COMMON_DIR" status --porcelain)" ]]
mkdir "$RUNTIME_WORK_DIR"
work=$(cd "$RUNTIME_WORK_DIR" && pwd)
python3 -m pip install --no-build-isolation --require-hashes --target "$work/python-deps" -r "$recipe/requirements-build.txt"
export PYTHONPATH="$work/python-deps${PYTHONPATH:+:$PYTHONPATH}"
cmake -S "$source" -B "$work/build" -DCLR_BUILD_HIP=ON -DCLR_BUILD_OCL=OFF \
 -DHIP_PLATFORM=amd -D__HIP_ENABLE_PCH=OFF -DHIP_COMMON_DIR="$HIP_COMMON_DIR" \
 -DCMAKE_PREFIX_PATH="$ROCM_PATH" -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
 -DCMAKE_C_COMPILER="$ROCM_PATH/llvm/bin/clang" -DCMAKE_CXX_COMPILER="$ROCM_PATH/llvm/bin/clang++"
cmake --build "$work/build" -j "$RUNTIME_BUILD_JOBS"
python3 "$recipe/package.py" --source "$source" --hip "$HIP_COMMON_DIR" --build "$work/build" \
 --rocm "$ROCM_PATH" --output "$work/package"
