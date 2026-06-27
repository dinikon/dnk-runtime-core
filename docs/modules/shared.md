# Shared Module

## Purpose

`shared` contains cross-cutting building blocks used by the business modules. It is not a business module by itself; it
hosts shared contracts, small domain primitives, infrastructure adapters and presentation wiring.

## Layout Rule

`shared` follows the same strict four-layer layout as business modules:

- `domain/<feature_aggregate>/`
- `application/<feature_aggregate>/`
- `infrastructure/<feature_aggregate>/`
- `presentation/<feature_aggregate>/`

Layer roots contain only `__init__.py`. Every class, protocol, dataclass or enum lives inside a feature aggregate such
as `events`, `jobs`, `persistence`, `identity_context`, `email`, `tokens`, `time`, `uuid`, `access`, `errors`,
`value_object` or `http`. Old internal paths such as `shared/kernel`, `shared/db`, `shared/depends` and
`shared/http` are removed.

## What Is Inside

- `domain`
    - shared value objects, request identity context, event/job records and statuses, email/tokens primitives and base
      errors
- `application`
    - ports, protocols, token manager, event use cases and scheduled job use cases
- `infrastructure`
    - SQLAlchemy base/helper/UoW/types/mixins, token backends, clocks, UUID generators, email transports, outbox/inbox,
      scheduled job repository, shared RabbitMQ messaging publisher and RabbitMQ event publisher
- `presentation`
    - FastAPI dependency wiring, HTTP host helpers and management wiring builders

## Most Used Shared Primitives

- `EntityIdVO`
    - UUID value object used directly for tenant scope and as the base class for concrete identifiers such as
      `UserIdVO`, `ContactIdVO`, `CompanyIdVO`, `RuntimeObjectIdVO` and `RuntimeFieldIdVO`
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
- `BrokerMessage` / `MessagePublisherPort`
    - low-level messaging contract used by infrastructure adapters; business modules should still expose semantic ports
- `ScheduledJob`
    - shared scheduled work contract persisted through PostgreSQL and processed by at-least-once workers
- `ScheduledJobHandlerPort`
    - handler contract implemented by future workflow, bulk-send or polling modules

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

## Messaging

Shared messaging provides broker-neutral primitives below module-specific ports:

- `BrokerMessage` stores JSON-compatible body and broker metadata such as headers, message id and correlation id
- `MessagePublisherPort` publishes a broker message to an exchange and routing key
- `RabbitMQMessagePublisher` owns shared RabbitMQ lifecycle and publish mechanics

`shared.events` and `communication` use this foundation through their own adapters. Queue names, exchanges, routing keys
and payload semantics remain owned by each module.

## Scheduled Jobs

Shared scheduled jobs provide at-least-once execution for deferred, timer and polling work:

- application use cases schedule `ScheduledJob` rows through the shared repository in the active `UnitOfWork`
- `dnk-manage jobs process-due` claims due `scheduled` rows using `FOR UPDATE SKIP LOCKED`, marks them `running` and
  dispatches them by `job_type`
- successful handlers mark jobs `done`
- failed handlers return jobs to `scheduled` with retry backoff until `max_attempts`, then jobs become `failed`
- `dnk-manage jobs recover-stuck` returns expired `running` jobs to `scheduled` or marks exhausted jobs `failed`
- `cancel` moves only non-terminal jobs to `canceled`

No concrete workflow, campaign, bulk-send or external polling handlers live in this foundation. Business modules should
depend on the application ports and presentation wiring, not on `shared.infrastructure.jobs`.

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
- shared scheduled job tests for scheduling, claiming, retry, stuck recovery, CLI wiring and optional PostgreSQL
  concurrent claims

## Related

- [Dependency injection](../architecture/dependency-injection.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)
- [Constraints and conventions](../quality/constraints-and-conventions.md)

## Source Of Truth

- `src/modules/shared/domain/`
- `src/modules/shared/application/events/`
- `src/modules/shared/application/jobs/`
- `src/modules/shared/infrastructure/events/`
- `src/modules/shared/infrastructure/jobs/`
- `src/modules/shared/infrastructure/persistence/`
- `src/modules/shared/presentation/`
- `src/modules/shared/__init__.py`
