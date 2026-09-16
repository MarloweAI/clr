# Supply the qualified ROCm base by immutable registry digest.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG RUNTIME_RELEASE=marlowe-hip-7.2.4-native-wait-v7-rc4
ARG RUNTIME_SHA256
USER root
COPY runtime.tar.gz /tmp/marlowe-runtime.tar.gz
RUN test -n "$RUNTIME_SHA256" \
    && printf '%s  %s\n' "$RUNTIME_SHA256" /tmp/marlowe-runtime.tar.gz | sha256sum --check \
    && mkdir -p /opt/marlowe/runtime \
    && tar xzf /tmp/marlowe-runtime.tar.gz -C /opt/marlowe/runtime \
    && test -x "/opt/marlowe/runtime/$RUNTIME_RELEASE/run" \
    && MARLOWE_RUNTIME_ROOT="/opt/marlowe/runtime/$RUNTIME_RELEASE" python3 "/opt/marlowe/runtime/$RUNTIME_RELEASE/verify.py" --files-only \
    && rm /tmp/marlowe-runtime.tar.gz
ENV GPU_NATIVE_EVENT_WAIT=0
# Preserve the base entrypoint. Workload configuration explicitly invokes <release>/run.
LABEL org.opencontainers.image.source="https://github.com/MarloweAI/clr"
