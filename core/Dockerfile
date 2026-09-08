FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.10.4

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

RUN groupadd --system core && useradd --system --gid core --home-dir /app core
COPY --chown=core:core src ./src

USER core

EXPOSE 8001

# Local Compose creates the core schema and migrates before starting this server.
CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8001", "--noreload"]
