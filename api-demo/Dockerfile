FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

RUN mkdir -p backend/app backend/tests \
    && touch backend/app/__init__.py backend/tests/__init__.py
COPY backend/pyproject.toml backend/
RUN uv pip install --system --no-cache-dir -e backend/

RUN mkdir -p api-demo/agents api-demo/lib \
    && touch api-demo/agents/__init__.py api-demo/lib/__init__.py
COPY api-demo/pyproject.toml api-demo/
RUN uv pip install --system --no-cache-dir -e api-demo/
RUN uv pip install --system --no-cache-dir -e "api-demo/[dev]"

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && rm -rf /var/lib/apt/lists/*
RUN adduser --disabled-password --gecos "" --uid 1000 observai

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY backend/ backend/
COPY api-demo/ api-demo/

USER observai
CMD ["python", "api-demo/run.py", "--help"]
