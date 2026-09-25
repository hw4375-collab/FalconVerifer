# FalconVerifier — FastAPI server + Lean 4/Mathlib kernel in one image.
# Build once (downloads ~5 GB of Mathlib oleans via `lake exe cache get`), run anywhere.
FROM python:3.12-slim-bookworm AS base

ENV DEBIAN_FRONTEND=noninteractive \
    ELAN_HOME=/opt/elan \
    PATH=/opt/elan/bin:/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl git ca-certificates build-essential && \
    rm -rf /var/lib/apt/lists/*

# Lean toolchain pinned by lean/lean-toolchain
COPY lean/lean-toolchain /tmp/lean-toolchain
RUN curl -sSfL https://github.com/leanprover/elan/releases/latest/download/elan-x86_64-unknown-linux-gnu.tar.gz \
        | tar xz -C /tmp && \
    /tmp/elan-init -y --no-modify-path --default-toolchain "$(cat /tmp/lean-toolchain)" && \
    rm /tmp/elan-init

WORKDIR /app

# Mathlib cache first so code edits do not invalidate the 5 GB layer
COPY lean/lakefile.toml lean/lean-toolchain lean/lake-manifest.json lean/
RUN cd lean && lake exe cache get && lake build --no-build 2>/dev/null || true
COPY lean/ lean/
RUN cd lean && lake build

# Python package
COPY pyproject.toml README.md ./
COPY falconverifier/ falconverifier/
COPY bench/ bench/
RUN pip install --no-cache-dir . && mkdir -p runs lean/scratch

EXPOSE 8000
ENV LEAN_PROJECT_DIR=/app/lean FV_MAX_CONCURRENT=2 FV_GITHUB_REF=main
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -sf http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "falconverifier.server:app", "--host", "0.0.0.0", "--port", "8000"]
