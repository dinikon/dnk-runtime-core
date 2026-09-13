# dnk-runtime-core

Modular FastAPI backend with tenant onboarding, console authentication, and static tenant data models.

## Repository boundaries

This repository owns the FastAPI runtime, tenant data, workers, Console and Shortlink.
Django accounts and the Nuxt Core frontend live in
[dnk-control-plane](https://github.com/dinikon/dnk-control-plane).
Both projects build independently and communicate through HTTPS. Runtime owns its
PostgreSQL, Redis and worker broker; Core does not share that database or broker.

The standalone [Helm chart](helm/README.md) deploys Runtime directly from `helm/`.
Control Plane has its own independent root chart; there is no platform umbrella.
See the [repository transition guide](docs/repository-split.md) before switching an
existing local stack.

## Modules

- `tenancy`: tenant lifecycle, domains, and transactional schema bootstrap.
- `identity`: email OTP, sessions, and tenant administrator provisioning.
- `control_plane`: Runtime v1 provisioning, mTLS integration, readiness and access projection delivery.
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

Review generated revisions before applying them. Public tables now have a separate
Alembic track. Run `dnk-manage database upgrade` on a fresh database before starting
the API; startup checks the installed revision without creating tables. Existing
unversioned databases are rejected without adoption or data deletion. Users, emails,
cloud identities and invitations remain tenant-local. See the
[Runtime v1 deployment guide](docs/deployment/control-plane-v1.md).

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
