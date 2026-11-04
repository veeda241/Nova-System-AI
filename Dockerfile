# Nova as a web service: the CLI's agent behind `nova serve`.
#
# One image, two brains:
#   NOVA_GGUF set   -> llama-server loads that GGUF inside this container (~4 GB RAM needed)
#   NOVA_GGUF empty -> Nova talks to whatever LLAMA_CPP_URL / API key env vars point at
#
# Build:  docker build -t nova .
# Run:    docker run -e NOVA_API_TOKEN=secret -p 8000:10000 -i -t nova

FROM python:3.11-slim

# libgomp1 is what the prebuilt ubuntu llama.cpp binaries need for OpenMP.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 xz-utils \
    && rm -rf /var/lib/apt/lists/*

# 23 MB of CPU-only llama.cpp - no CUDA runtime, so the image runs on any plan.
# The tarball is flat (binaries and .so files side by side under one folder), so it
# goes to its own prefix rather than into /usr/local.
ADD https://github.com/ggml-org/llama.cpp/releases/download/b12098/llama-b12098-bin-ubuntu-x64.tar.gz /tmp/llama.tar.gz
RUN mkdir -p /opt/llama.cpp \
    && tar -xzf /tmp/llama.tar.gz -C /opt/llama.cpp --strip-components=1 \
    && rm -f /tmp/llama.tar.gz \
    && echo /opt/llama.cpp > /etc/ld.so.conf.d/llama.cpp.conf \
    && ldconfig \
    && /opt/llama.cpp/llama-server --version
ENV PATH="/opt/llama.cpp:${PATH}" \
    LD_LIBRARY_PATH=/opt/llama.cpp

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[system]"

RUN useradd --create-home --shell /bin/sh nova \
    && mkdir -p /app/workspace /app/.nova \
    && chown -R nova:nova /app
COPY scripts/docker-entrypoint.sh /usr/local/bin/nova-entrypoint
RUN chmod +x /usr/local/bin/nova-entrypoint

USER nova
ENV NOVA_HOME=/app \
    NOVA_WORKSPACE=/app/workspace \
    LLAMA_CPP_URL=http://127.0.0.1:8080 \
    NOVA_GGUF="" \
    NOVA_CTX_SIZE=4096 \
    NOVA_THREADS=2 \
    PORT=10000

WORKDIR /app
EXPOSE 10000
ENTRYPOINT ["nova-entrypoint"]
