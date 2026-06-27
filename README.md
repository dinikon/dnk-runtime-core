# dnk-runtime-core

`dnk-runtime-core` is a modular FastAPI backend that combines tenant onboarding, console authentication, tenant runtime
schema management, and a small CRM surface for contacts.

## What Is In The Service

- `tenancy`: tenant onboarding and tenant resolution by host
- `identity`: email OTP + session-based console authentication
- `schema_registry`: runtime schema bootstrap and diff for tenant PostgreSQL schemas
- `runtime_data`: tenant-scoped runtime object persistence and querying
- `crm`: CRUD operations for contacts
- `communication`: provider connectors, templates, outbound messages and delivery state
- `workflow`: workflow application and definition/runtime foundations
- `shared`: database, unit of work, request context, auth and infrastructure helpers

## Quick Start

- Python: `>=3.12`
- Install dependencies: `uv sync`
- Run app: `uv run fastapi dev src/app.py`
- Run tests: `./.venv/bin/python -m unittest discover -s test -p 'test_*.py' -v`
- Docker:
    - `cp temaplate.env .env`
    - `docker compose up --build`
    - API docs: `http://localhost:8000/docs`
    - RabbitMQ management UI: `http://localhost:15672`
  - Communication worker logs: `docker compose logs -f communication-worker`
  - Debug integration events: `docker compose logs -f events-console-worker`
- Run schema diff command:
    - `dnk-manage schema-registry diff <tenant_id>`
  - `dnk-manage schema-registry diff --all`
    - `dnk-manage schema-registry diff <tenant_id> --seed-path src.modules.schema_registry.seed.schema_seed`

## Documentation

- [Documentation index](docs/index.md)
- [Architecture overview](docs/architecture/overview.md)
- [HTTP API](docs/interfaces/http-api.md)
- [Management CLI](docs/interfaces/management-cli.md)

## Source Of Truth

- `src/app_factory.py`
- `src/modules/router.py`
- `src/management/cli.py`
