FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY docker_health_alerts ./docker_health_alerts

RUN uv sync --locked --no-dev --no-cache

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV CONFIG_FILE=/config/config.yaml

ENTRYPOINT ["uv", "run", "--no-dev", "docker-health-alerts"]
CMD ["run"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD ["uv", "run", "--no-dev", "docker-health-alerts", "healthcheck"]
