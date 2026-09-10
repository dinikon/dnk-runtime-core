# Constraints And Conventions

## Architecture Rules

- Modules are organized by bounded context under `src/modules/`.
- Business modules should keep the standard layering:
    - `domain`
    - `application`
    - `infrastructure`
    - `presentation`
- `shared` hosts reusable primitives and infrastructure, not business workflows.

## Dependency Rules

- `presentation` may depend on `application`.
- `application` may depend on `domain` and ports.
- `infrastructure` implements ports and repositories used by `application`.
- `tenancy.application` must not import Alembic or SQLAlchemy implementations; schema bootstrap goes through a tenancy-owned port.

## Persistence Rules

- One active `UnitOfWork` owns one `AsyncSession`.
- HTTP requests and management commands must assemble session-bound repositories/adapters from the same active session.
- Nested schema bootstrap must not open a second `UoW`.

## Request/Auth Rules

- HTTP business routes use request context from shared authentication dependency.
- Console auth is host-aware and session-cookie based.
- Control-plane protected routes use bearer API key validation.
- Client data routes must not accept `tenant_id` from public payloads,
  query params or
  path
  params. Controllers read tenant from the authenticated request context, put it into application command/query DTOs and
  pass it through use cases, services and repository method calls where tenant data access needs it. Wiring
  files must stay tenant-agnostic and must not resolve or bind repositories to a tenant.

## Identifier Rules

- `EntityIdVO` is the single shared UUID primitive and the base class for concrete domain identifiers.
- Tenant scope uses `EntityIdVO` directly. Concrete domain entities use concrete subclasses: for example `UserIdVO`,
  `DataSourceIdVO`, `RuntimeObjectIdVO` and `RuntimeFieldIdVO`.
- Transport, token and persistence boundaries may use `UUID` or `str`, but values are converted to `EntityIdVO` or a
  concrete id subclass before entering domain/application behavior and converted back with `.uuid` when leaving it.
- Concrete id classes are intentionally not interchangeable, even when they wrap the same UUID.

## Tenant Migration Rules

- Static tenant models inherit shared TenantBase and use Alembic revisions.
- Global Base models retain startup create_all.
- Bootstrap DDL shares the onboarding transaction and never commits internally.
- Schema names use the shared naming strategy and a stable SCHEMA_PREFIX.
- Autogenerate uses a separate engine and a metadata copy; shared engine state is not changed.
- Legacy unregistered tables are excluded from generated changes.

## Documentation Rules

- docs should describe only current implemented behavior
- internal links should be relative Markdown links
- each module page should include:
    - purpose
    - public functionality
    - main flows
    - domain model
    - infrastructure/persistence
    - presentation/entrypoints
    - dependencies
    - tests
    - related links

## Related

- [Develop style](../develop-style.md)
- [Architecture overview](../architecture/overview.md)
- [Project structure](../architecture/project-structure.md)
- [Test map](test-map.md)

## Source Of Truth

- `src/modules/`
- `test/test_architecture_boundaries.py`
