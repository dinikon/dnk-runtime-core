FROM node:24-alpine AS accounts-ui
WORKDIR /build
COPY frontends ./frontends
COPY core/src/accounts/templates ./core/src/accounts/templates
RUN cd frontends && npm ci --ignore-scripts && npm run build:accounts

FROM python:3.13.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.10.4

COPY core/pyproject.toml core/uv.lock core/README.md ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

RUN groupadd --system core && useradd --system --gid core --home-dir /app core
COPY --chown=core:core core/src ./src
COPY --from=accounts-ui --chown=core:core /build/core/src/accounts/static/core/ui ./src/accounts/static/core/ui
RUN mkdir -p /app/staticfiles && chown core:core /app/staticfiles

USER core

# Collect only public assets. These temporary build settings are not runtime secrets.
RUN CORE_SECRET_KEY=static-build-only CORE_DEBUG=true \
    python src/manage.py collectstatic --noinput

EXPOSE 8001

# Schema preparation/migrations are explicit deployment steps; Compose runs them locally.
CMD ["gunicorn", "--chdir", "src", "dnk_core.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]
