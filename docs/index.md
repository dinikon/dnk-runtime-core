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
- [Inventory](modules/inventory.md)
- [Shared](modules/shared.md)

## Roadmap-границы модулей

Эти документы описывают планируемые границы bounded contexts. Это не документация текущей реализации, пока не добавлены
соответствующие пакеты `src/modules/*`.

- [Campaigns](modules/campaigns.md)
- [External Events](modules/external-events.md)

## Interfaces

- [HTTP API](interfaces/http-api.md)
- [Management CLI](interfaces/management-cli.md)
- [Configuration](interfaces/configuration.md)

## Frontends

- [Console frontend](frontends/console.md)

## Data Model

- [Domain models](data/domain-models.md)
- [Tenant migrations](data/tenant-migrations.md)
- [Historical dynamic modules](history/index.md)

## Quality And Constraints

- [Test map](quality/test-map.md)
- [Constraints and conventions](quality/constraints-and-conventions.md)
- [Develop style](develop-style.md)

## Operations

- [Minimal CI/CD: local development and automated deployment](plan/ci-cd.md)
- [Repository split and local transition](repository-split.md)
- [Standalone Helm deployment](../helm/README.md)

- [CRM removal runbook](operations/remove-crm.md)
- [Custom object module removal](operations/remove-custom-object.md)
- [Workflow and communication removal](operations/remove-workflow-communication.md)

## Related

- [README](../README.md)

## Source Of Truth

- `src/app_factory.py`
- `src/modules/router.py`
- `src/management/cli.py`
- `frontends/apps/console/src/`
