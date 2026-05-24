# Shared Module

## Purpose

`shared` contains cross-cutting building blocks used by the business modules. It is not a business module by itself; it
hosts infrastructure, kernel concepts and utility abstractions.

## What Is Inside

- `db`
    - SQLAlchemy base, helper, unit of work, custom DB types and mixins
- `depends`
  - request-scoped FastAPI dependencies such as UoW, authentication, authorization and email service resolution
- `kernel`
    - request context, principal, access, time, integration events and public email service contracts
- `infrastructure`
    - concrete implementations for access, time, token backends, event outbox/inbox, RabbitMQ event publication,
      rendered
      email builders and transports
- `http`
    - shared HTTP helpers such as host extraction
- `domain`
    - shared value objects and base domain errors

## Most Used Shared Primitives

- `EntityIdVO`
    - UUID value object used directly for tenant scope and as the base class for concrete identifiers such as
      `UserIdVO`, `ContactIdVO`, `ProductIdVO`, `RuntimeObjectIdVO` and `RuntimeFieldIdVO`
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
- `EmailServicePort` / `SystemEmailKind`
  - typed shared contract for system email delivery used by business modules
- `IntegrationEvent`
    - shared integration event contract persisted through PostgreSQL outbox and published asynchronously to RabbitMQ
- `EventPublisherPort` / `EventConsumerPort`
    - ports that keep business modules independent from concrete RabbitMQ adapters

## Event Bus, Outbox And Inbox

Shared integration events use at-least-once delivery:

- application use cases store `IntegrationEvent` through `SqlAlchemyOutboxRepository` in the active `UnitOfWork`
- `dnk-manage events publish-outbox` claims due `pending` outbox rows, publishes them to RabbitMQ and marks them
  `published`
- failed publish attempts return to `pending` with retry backoff until `max_attempts`, then become `failed`
- consumers use `SqlAlchemyInboxRepository` before invoking handlers, keyed by `(tenant_id, source, message_id)`, so a
  repeated broker delivery does not rerun business logic

Concrete module event schemas, campaign goal matching and workflow events are intentionally outside the shared
foundation.

## Why It Matters

- keeps module code small and focused on business logic
- standardizes transaction, auth and request lifecycle behavior
- centralizes email provider selection and SMTP transport wiring
- provides common contracts for domain/application code
- keeps id handling consistent: public APIs and persistence can expose UUIDs, while domain/application code uses
  `EntityIdVO` for tenant scope and concrete `EntityIdVO` subclasses for entity ids

## Tests Covering This Area

- shared authentication dependency tests
- shared email service tests
- DB and type tests
- architecture boundary tests that protect module layering
- shared event tests for serialization, publish retry, RabbitMQ publication and inbox idempotency

## Related

- [Dependency injection](../architecture/dependency-injection.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)
- [Constraints and conventions](../quality/constraints-and-conventions.md)

## Source Of Truth

- `src/modules/shared/db/`
- `src/modules/shared/depends/`
- `src/modules/shared/kernel/`
- `src/modules/shared/application/events/`
- `src/modules/shared/infrastructure/events/`
- `src/modules/shared/infrastructure/outbox/`
- `src/modules/shared/infrastructure/inbox/`
- `src/modules/shared/__init__.py`
