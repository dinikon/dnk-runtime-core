# dnk-runtime-core

Modular FastAPI backend with tenant onboarding, console authentication, and static tenant data models.

## Repository boundaries

This repository owns the FastAPI runtime, tenant data, workers, Console and Shortlink.
Django accounts and the Nuxt Core frontend live in
[dnk-control-plane](https://github.com/dinikon/dnk-control-plane).
Both projects build independently. Local PostgreSQL and Redis remain in this Compose
project; Control Plane connects through its external Docker network.

The standalone [Helm chart](helm/README.md) deploys Runtime directly from `helm/`.
Control Plane has its own independent root chart; there is no platform umbrella.
See the [repository transition guide](docs/repository-split.md) before switching an
existing local stack.

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
- Docker: copy `temaplate.env` to `.env`, then `docker compose up --build`.

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

- [CI/CD: release workflow and artifact publication](docs/plan/ci-cd.md)
- [CI/CD maintenance: modules, job logs and build cache](docs/operations/ci-cd.md)
- [Container images: build and publish to GitHub Packages](docs/container-images.md)
- [Documentation index](docs/index.md)
- [Architecture](docs/architecture/overview.md)
- [Inventory](docs/modules/inventory.md)
- [Tenant migrations](docs/data/tenant-migrations.md)
- [HTTP API](docs/interfaces/http-api.md)
- [Management CLI](docs/interfaces/management-cli.md)
