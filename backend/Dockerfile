# syntax=docker/dockerfile:1
# Production: multi-stage, venv, без dev-зависимостей.
# BuildKit + кэш uv/apt. Зависимости: uv pip (быстрее pip).

FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.2 /uv /uvx /bin/

ARG PIP_INDEX_URL=
ARG PIP_TRUSTED_HOST=
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG NO_PROXY=

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    no_proxy=${NO_PROXY} \
    DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_CONNECT_TIMEOUT=60 \
    UV_HTTP_TIMEOUT=120 \
    UV_HTTP_RETRIES=6 \
    UV_CONCURRENT_DOWNLOADS=4 \
    PYTHONDONTWRITEBYTECODE=1

# Образ python:slim уже содержит ca-certificates; отдельный apt в builder не нужен
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV=/opt/venv

WORKDIR /app
COPY requirements.txt ./

RUN --mount=type=cache,target=/root/.cache/uv \
    set -e; \
    UV_OPTS=""; \
    if [ -n "${PIP_INDEX_URL}" ]; then UV_OPTS="${UV_OPTS} --index-url ${PIP_INDEX_URL}"; fi; \
    if [ -n "${PIP_TRUSTED_HOST}" ]; then UV_OPTS="${UV_OPTS} --allow-insecure-host ${PIP_TRUSTED_HOST}"; fi; \
    uv pip install ${UV_OPTS} --requirement requirements.txt

# --- runtime ---
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/opt/venv/bin:$PATH"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends libpq5 libffi8 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN groupadd -r django && useradd -r -g django django

WORKDIR /app
COPY --chown=django:django . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=5)" || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
