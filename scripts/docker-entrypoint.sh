#!/bin/sh
# Container start: boot a local GGUF if one is asked for, then serve the agent API.
set -e

if [ -n "${NOVA_GGUF}" ]; then
    echo "nova-entrypoint: serving ${NOVA_GGUF} on 127.0.0.1:8080 - the first start downloads the weights"
    llama-server \
        -hf "${NOVA_GGUF}" \
        --host 127.0.0.1 \
        --port 8080 \
        --ctx-size "${NOVA_CTX_SIZE}" \
        --threads "${NOVA_THREADS}" \
        --no-webui &
fi

exec nova serve --host "${NOVA_BIND:-0.0.0.0}" --port "${PORT:-10000}"
