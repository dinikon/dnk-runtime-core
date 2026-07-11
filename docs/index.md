# Documentation Index

This documentation describes the current implementation of `dnk-runtime-core` as it exists in `src/`, `test/` and
`frontends/`.

## Architecture

- [Overview](architecture/overview.md)
- [Project structure](architecture/project-structure.md)
- [Request lifecycle](architecture/request-lifecycle.md)
- [Dependency injection](architecture/dependency-injection.md)
- [Persistence and Unit of Work](architecture/persistence-and-uow.md)

## Modules

- [Tenancy](modules/tenancy.md)
- [Identity](modules/identity.md)
- [Communication](modules/communication.md)
- [Schema Registry](modules/schema-registry.md)
- [Shared](modules/shared.md)
- [Workflow](modules/workflow.md)

## Roadmap-границы модулей

Эти документы описывают планируемые границы bounded contexts. Это не документация текущей реализации, пока не добавлены
соответствующие пакеты `src/modules/*`.

- [Campaigns](modules/campaigns.md)
- [External Events](modules/external-events.md)

## Implementation Plans

- [Control Plane](../control_plane/docs/IMPLEMENTATION_PLAN.md)

## Interfaces

- [HTTP API](interfaces/http-api.md)
- [Management CLI](interfaces/management-cli.md)
- [Configuration](interfaces/configuration.md)

## Frontends

- [Console frontend](frontends/console.md)

## Data And Runtime Model

- [Domain models](data/domain-models.md)
- [Runtime schema](data/runtime-schema.md)

## Quality And Constraints

- [Test map](quality/test-map.md)
- [Constraints and conventions](quality/constraints-and-conventions.md)
- [Develop style](develop-style.md)

## Operations

- [CRM removal runbook](operations/remove-crm.md)
- [Custom object module removal](operations/remove-custom-object.md)

## Related

- [README](../README.md)

## Source Of Truth

- `src/app_factory.py`
- `src/modules/router.py`
- `src/management/cli.py`
- `frontends/apps/console/src/`
