# Deployment through an existing Slurm/Pyxis image

Marlowe's qualification jobs already use the runtime overlay with an unchanged,
pinned SQSH base. This is an available interim distribution path; building or
publishing an OCI image is optional. It does not bypass the model, soak, canary,
owner and rollback gates in QUALIFICATION.md.

The RC4 qualification identities are:

- SQSH base SHA256: `43b9e7ae1e56863cd48be7af67958b8dd7ff833a907f13763883cd668a13ce06`.
- Runtime archive SHA256: `728378b9e86f8318260c05ed6caa252633c51363a02143b1efa69c815b197c9d`.
- Release: `marlowe-hip-7.2.4-native-wait-v7-rc4`.
- Runtime source: `85b0432bde51e66f8f79615de1022697ad59c5cf`.

These are two different file identities, not an OCI manifest digest. A different
base or runtime archive needs a new qualified release record.

Before scheduling workers, verify both file hashes against that record. Extract
the archive once into a new versioned shared directory, preserving symlinks. Make
that installation read-only to workers, and retain the archive and its manifest.
Do not overwrite a release directory while any worker uses it. Do not replace
host ROCm libraries or kernel modules.

The job uses the verified SQSH with Pyxis, mounts the versioned runtime directory,
and starts its usual application through the package's `run` launcher. For example,
inside the allocated container:

```bash
GPU_NATIVE_EVENT_WAIT=1 /runtime/marlowe-hip-7.2.4-native-wait-v7-rc4/run \
  /opt/venv/bin/python /app/service.py
```

Here `/runtime` and `/app` are deployment mount locations. Keep Slurm's GPU
visibility and existing application/model arguments. Start with one serving worker
per GPU and no unrelated co-located GPU workloads. Do not use the qualification
benchmark as a production service entrypoint.

The launcher checks library bytes and preload aliases, then selects both HIP and
HSA. Call the package's `verify()` from `verify.py` in each actual GPU worker after
its imports and device initialization, and record its returned identity with the
worker PID. A successful separate probe is not proof that distributed workers use
the same runtime. Keep normal readiness and model-output health checks.

First compare feature-off and feature-on worker pools with the same image, runtime
archive, model and application source. Also retain a stock pool that starts in a
fresh base container without the overlay launcher. The full stock comparison
includes transitive library selection; flipping the feature flag isolates native
waits within the same replacement stack.

For immediate mitigation, restart the worker through the same launcher with
`GPU_NATIVE_EVENT_WAIT=0`. The variable is read at process startup. For full
rollback, launch a fresh worker from the original base image and original job
environment without the overlay launcher or inherited overlay preload/search-path
settings. This restores the stock HIP/HSA and their dependencies; changing only
the feature flag does not restore those libraries.

The current qualification uses this overlay/container mechanism, but it is not a
production-traffic canary or a rollback rehearsal. Record the release owner,
canary/control job templates, SLO gates and rollback procedure before promotion.
An immutable derived OCI image remains a separate option using `build-image.sh`.
