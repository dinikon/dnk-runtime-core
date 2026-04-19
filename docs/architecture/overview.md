# Architecture Overview

`dnk-runtime-core` is a modular backend organized around domain-focused modules under `src/modules/`. The service
exposes HTTP endpoints through FastAPI and management commands through `dnk-manage`.

## Main Modules

- `tenancy`: creates tenants, creates primary console domains, resolves tenant by host, and owns tenant onboarding flow.
- `identity`: handles email OTP request/confirmation, session authentication, current user profile and logout.
- `runtime_data`: provides tenant-scoped persistence/query primitives for runtime objects described by metadata.
- `crm`: currently exposes contact CRUD for authenticated users.
- `schema_registry`: loads seed manifests, creates or diffs tenant runtime schemas in PostgreSQL, and stores metadata
  snapshot for runtime objects and fields.
- `shared`: cross-cutting infrastructure such as database helper, unit of work, request context, authentication,
  authorization, time and token helpers.

## Layering

- `domain`: entities, value objects, domain errors, repository contracts and domain-local services.
- `application`: commands, queries, DTOs, orchestration use cases and application services.
- `infrastructure`: SQLAlchemy repositories, persistence models, PostgreSQL adapters and external integrations.
- `presentation`: HTTP routers and dependency composition for FastAPI; management-specific builders live close to module
  composition.

## Entry Points

- HTTP app is created in `src/app_factory.py`.
- Root API router is assembled in `src/modules/router.py`.
- Management CLI is assembled in `src/management/cli.py`.

## Related

- [Project structure](project-structure.md)
- [Request lifecycle](request-lifecycle.md)
- [Dependency injection](dependency-injection.md)
- [HTTP API](../interfaces/http-api.md)

## Source Of Truth

- `src/app_factory.py`
- `src/modules/router.py`
- `src/management/cli.py`
