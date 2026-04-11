# Shared Module

## Purpose

`shared` contains cross-cutting building blocks used by the business modules. It is not a business module by itself; it
hosts infrastructure, kernel concepts and utility abstractions.

## What Is Inside

- `db`
    - SQLAlchemy base, helper, unit of work, custom DB types and mixins
- `depends`
    - request-scoped FastAPI dependencies such as UoW, authentication and authorization
- `kernel`
    - request context, principal, access and time ports
- `infrastructure`
    - concrete implementations for access, time and token backends
- `http`
    - shared HTTP helpers such as host extraction
- `domain`
    - shared value objects and base domain errors

## Most Used Shared Primitives

- `EntityIdVO`
    - strongly typed entity identifier wrapper used across modules
- `RequestContext`
    - current request principal + request metadata
- `Principal`
    - authenticated session identity used by request context
- `UnitOfWork`
    - request/command transaction boundary
- `AuthenticatedRequestContextDep`
    - authentication guard for HTTP routes
- `AuthorizationServiceDep`
    - authorization boundary, currently backed by allow-all implementation
- `ClockPort` / `UtcClock`
    - time abstraction used by domain/application services

## Why It Matters

- keeps module code small and focused on business logic
- standardizes transaction, auth and request lifecycle behavior
- provides common contracts for domain/application code

## Tests Covering This Area

- shared authentication dependency tests
- DB and type tests
- architecture boundary tests that protect module layering

## Related

- [Dependency injection](../architecture/dependency-injection.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)
- [Constraints and conventions](../quality/constraints-and-conventions.md)

## Source Of Truth

- `src/modules/shared/db/`
- `src/modules/shared/depends/`
- `src/modules/shared/kernel/`
- `src/modules/shared/__init__.py`
