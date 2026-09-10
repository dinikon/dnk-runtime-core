# Architecture Overview

The backend follows modular DDD and Clean Architecture.

- `tenancy`: tenant lifecycle, host resolution and transactional tenant-schema bootstrap.
- `identity`: email OTP, sessions, user profile and administrator provisioning.
- `inventory`: Warehouse domain and persistence model, with no application/HTTP operations yet.
- `shared`: identifiers, audit fields, UoW, tenant naming and migrations, authentication, messaging and jobs.

## Layering

- `domain`: entities, value objects, domain errors and repository protocols.
- `application`: use cases, commands, DTOs and ports.
- `infrastructure`: persistence and external-service adapters.
- `presentation`: HTTP/CLI entrypoints and dependency composition.

Domain dependencies point inward to shared primitives. One UoW session owns an onboarding transaction. The tenancy-owned bootstrap port is implemented by a PostgreSQL/Alembic adapter; the application layer does not import Alembic.

Global models use `Base`. Static tenant models use `TenantBase` and Alembic. Dynamic modules were removed; see [history](../history/index.md).

## Entry points

- HTTP: `src/app_factory.py` and `src/modules/router.py`.
- CLI: `src/management/cli.py`.
- Tenant revisions: `migrations/tenant/versions/`.

## Related

- [Project structure](project-structure.md)
- [Persistence and UoW](persistence-and-uow.md)
- [Dependency injection](dependency-injection.md)
- [Tenant migrations](../data/tenant-migrations.md)
