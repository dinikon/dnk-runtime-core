# Persistence And Unit Of Work

## Database Helper

`DatabaseHelper` owns:

- SQLAlchemy async engine
- async session factory
- metadata `create_all()`
- engine disposal on shutdown

It is initialized in `src/modules/shared/db/helper.py` and attached to app state in `src/app_factory.py`.

## Unit Of Work

`UnitOfWork` in `src/modules/shared/db/uow.py` is request-scoped and session-scoped.

Behavior:

- `__aenter__` creates an `AsyncSession`
- `__aexit__` commits if no exception happened
- `__aexit__` rolls back if an exception happened
- session is always closed on exit

## HTTP Usage

- `src/modules/shared/depends/uow.py` creates one `UnitOfWork` per HTTP request.
- Controllers and dependency builders consume repositories assembled from `uow.session`.

## Management Usage

- CLI handlers explicitly open `async with UnitOfWork(...) as uow`.
- Builders then assemble repositories/adapters from `uow.session`.

## Session-Bound Repositories And Adapters

Examples:

- SQLAlchemy repositories in `identity`, `tenancy`, `crm`, `schema_registry`
- PostgreSQL schema inspector and executor in `schema_registry`
- nested schema bootstrap adapter used from tenant creation flow

## Why It Matters

- Ensures one transaction boundary for each request or command
- Keeps nested schema bootstrap in the same active transaction
- Allows rollback of onboarding + schema work together on failure

## Related

- [Dependency injection](dependency-injection.md)
- [Schema Registry module](../modules/schema-registry.md)
- [Shared module](../modules/shared.md)

## Source Of Truth

- `src/modules/shared/db/helper.py`
- `src/modules/shared/db/uow.py`
- `src/modules/shared/depends/uow.py`
