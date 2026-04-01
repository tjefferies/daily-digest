# backend.Dockerfile - Multistage build for FastAPI backend
# Build: docker build -f backend.Dockerfile -t evercurrent-backend .

# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code, config, and readme (required by hatchling build)
COPY README.md ./
COPY src/ src/
COPY config/ config/
COPY data/ data/

# Install the project itself
RUN uv sync --frozen --no-dev

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/config /app/config
COPY --from=builder /app/data /app/data
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "evercurrent.app:app", "--host", "0.0.0.0", "--port", "8000"]
