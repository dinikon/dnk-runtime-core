# dnk-runtime-core

Modular FastAPI backend with tenant onboarding, console authentication, and static tenant data models.

## Django Core

[Core](core/README.md) is a separate Django scaffold with its own dependencies
and environment. It uses the `core` schema in the existing PostgreSQL database.
The planned tenant control plane, global
identity, tenant OIDC, DNS and system email flows are described in its
[architecture proposal](core/ARCHITECTURE.md); those flows are not implemented yet.

For the local Docker stack, configure Core as described in its
[Docker instructions](core/README.md#локальный-стенд-в-docker-compose), then run
`docker compose up --build -d`.
Django starts with the existing stack and shares its PostgreSQL service;
admin is available
at [127.0.0.1:8001/admin/](http://127.0.0.1:8001/admin/).

## Modules

- `tenancy`: tenant lifecycle, domains, and transactional schema bootstrap.
- `identity`: email OTP, sessions, and tenant administrator provisioning.
- `inventory`: Warehouse domain model and tenant-scoped persistence model; no HTTP API yet.
- `shared`: database/UoW, tenant migrations, identifiers, audit fields, messaging, and jobs.

Dynamic object modules are removed. Their earlier documentation is in [history](docs/history/index.md).

## Development

- Python: `3.13.9`; PostgreSQL: `16`.
- Install: `uv sync`.
- Run: `uv run fastapi dev src/app.py`.
- Tests: `uv run python -m unittest discover -s test -p 'test_*.py' -v`.
- For PostgreSQL integration tests set `TEST_POSTGRES_URL` to a **disposable** PostgreSQL database URL using `postgresql+asyncpg://`.
- Format: `uv run black --check src test migrations`.
- Docker: copy `temaplate.env` to `.env`, configure `core/.env` using the
  [Core instructions](core/README.md#локальный-стенд-в-docker-compose), then `docker compose up --build`.

## Tenant migrations

A new tenant gets its schema and Alembic `head` within the onboarding transaction. Existing tenants are upgraded explicitly:

```sh
dnk-manage tenant-migrations upgrade <tenant_id>
dnk-manage tenant-migrations upgrade --all
dnk-manage tenant-migrations current --all
dnk-manage tenant-migrations revision --autogenerate --tenant-id <tenant_id> -m "Describe the change"
```

Review generated revisions before applying them. Global tables still use startup `create_all`. Users and emails are tenant-local from revision `0002_identity_users`; the transition from shared users requires recreating test databases and repeating onboarding, without copying existing user data.

## Documentation

- [Documentation index](docs/index.md)
- [Architecture](docs/architecture/overview.md)
- [Inventory](docs/modules/inventory.md)
- [Tenant migrations](docs/data/tenant-migrations.md)
- [HTTP API](docs/interfaces/http-api.md)
- [Management CLI](docs/interfaces/management-cli.md)
