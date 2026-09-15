#!/usr/bin/env bash
set -euo pipefail
if (( $# != 4 )); then
  echo 'usage: build-image.sh BASE_IMAGE@sha256:DIGEST RUNTIME_ARCHIVE ARCHIVE_SHA256 OUTPUT_TAG' >&2
  exit 2
fi
base_image=$1
runtime_archive=$2
archive_sha256=$3
output_tag=$4
[[ $base_image =~ @sha256:[a-f0-9]{64}$ ]] || { echo 'Base image must use an immutable digest' >&2; exit 2; }
[[ $archive_sha256 =~ ^[a-f0-9]{64}$ ]] || { echo 'Expected a SHA256 archive digest' >&2; exit 2; }
printf '%s  %s\n' "$archive_sha256" "$runtime_archive" | sha256sum --check
recipe_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
release=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["release"])' "$recipe_dir/source-lock.json")
build_context=$(mktemp -d)
trap 'rm -rf -- "$build_context"' EXIT
cp -- "$runtime_archive" "$build_context/runtime.tar.gz"
cp -- "$recipe_dir/Dockerfile" "$build_context/Dockerfile"
docker build --build-arg "BASE_IMAGE=$base_image" --build-arg "RUNTIME_RELEASE=$release" \
  --build-arg "RUNTIME_SHA256=$archive_sha256" --tag "$output_tag" "$build_context"
# Publishing and rollout are separate from producing a local, reviewable image.
