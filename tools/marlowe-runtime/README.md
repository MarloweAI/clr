# Marlowe HIP runtime overlay

Build and package the gfx950 event-wait backport as a userspace HIP/HSA overlay.
The package is independent of SGLang and HiSparse and uses unchanged HIP/PyTorch
APIs. This release candidate is opt-in and is not yet production-qualified.

The current implementation uses a [selective native-wait policy](NATIVE_WAIT_POLICY.md)
to avoid the short-chain and late-wait regressions of unconditional prewaits.
The source lock below identifies the packaged release; development benchmark
results do not qualify different packaged bytes.

[Qualification evidence and open promotion gates](QUALIFICATION.md) distinguish
the PyTorch wait result, isolated runtime toggle tests and stock-image comparisons.

Use a ROCm7.2.4 Linux build image with matching compiler, COMGR, headers and HSA,
CMake, Git, Python pip and setuptools. Pin and record the base image digest in
your build system. Set `RUNTIME_BUILD_BASE_IMAGE` to the immutable identity in
`source-lock.json`; assembly rejects missing or different identities and verifies
the actual HSA bytes against the lock. This identity is supplied by the build
orchestrator, not inferred or attested from inside the container. The tested development environment is the SGLang ROCm7.2.4
MI35x image; this overlay is not a complete standalone ROCm distribution.

```
RUNTIME_WORK_DIR=/build/native-wait bash tools/marlowe-runtime/build.sh
```

The build script fetches exact CLR and HIP commits from source-lock.json and
verifies them. It records binary, recipe and tool identity, includes the runtime
licenses, and produces a relocatable directory plus a tar archive and its digest.
Optional embedded HIP PCH is disabled, matching the qualified build configuration.
Runtime-compilation use cases need separate qualification.

For existing Slurm/Pyxis deployments, [use a pinned SQSH base plus the versioned
overlay](SLURM.md); an OCI registry is not required for that path. Alternatively,
copy the extracted release into `/opt/marlowe/runtime/<release>` in a derived
image. Preserve symlinks. Do not overwrite system ROCm libraries. The matching
base image supplies the remaining dependencies. Keep this layer identical in
control and candidate containers.

```
GPU_NATIVE_EVENT_WAIT=0 /opt/marlowe/runtime/<release>/run python app.py
GPU_NATIVE_EVENT_WAIT=1 /opt/marlowe/runtime/<release>/run python app.py
```

The launcher verifies packaged bytes and preload symlink targets before exec and
selects HIP and HSA together.
It preserves the base image's library search order after prepending only the
package directory. It deliberately preloads by library name: absolute preload paths allowed a second bundled HIP library to
load in the tested PyTorch image. Check the actual process with `verify.py` under
the same launcher; an independent probe is useful but is not a substitute for
worker-level runtime identity receipts in a distributed service.

The verifier refuses changed library bytes, duplicate HIP/HSA mappings, an
unexpected HIP version and non-gfx950 devices. The launcher remains usable with
non-Python HIP programs; PyTorch is needed only for the process verification probe.
Ordinary stream/graph APIs are unchanged. No per-model event wrappers are needed.

Rollback requires restarting workers with the feature disabled. Full rollback
selects the previous image, removing the entire overlay. Preserve the stock image
as a third qualification arm so replacing the bundled runtime is tested separately
from enabling native waits.

For production, complete model correctness/performance qualification and a bounded
canary, resolve sanitizer shutdown findings, and define ownership of the pinned
ROCr internal ABI. This fork's release backport is separate from a forward port
to ROCm/rocm-systems. When AMD ships a supported package, qualify it through the
same reproducer/workload suite and retire the overlay.


`bash build-image.sh BASE_IMAGE@sha256:DIGEST ARCHIVE ARCHIVE_SHA256 OUTPUT_TAG`
produces a local derived image from an existing release archive. It requires an
immutable base reference, checks the archive before building, and verifies the
installed library bytes during the image build without requiring a GPU. The
Dockerfile uses root and preserves the base entrypoint; set the service user in
your workload image as appropriate. Publishing is a separate step. The image
recipe is supplied for integration; OCI image build and canary validation remain
open until a matching registry base digest and release destination are configured.
