# Schema Registry Module

## Purpose

`schema_registry` manages tenant runtime schemas in PostgreSQL and stores a metadata snapshot of runtime objects and
fields. It is responsible for bootstrap from seed and schema diff against existing tenant schemas.

## Public Functionality

- load seed manifests from Python modules
- create tenant runtime schema from seed
- diff existing tenant runtime schema against seed
- inspect physical PostgreSQL schema
- persist metadata snapshot for datasource, objects and fields

## Main Flows / Use Cases

- `CreateSchemaUseCase`
    - load seed
    - ensure schema is absent
    - build create plan
    - apply PostgreSQL DDL
    - write metadata snapshot
- `DiffSchemaUseCase`
    - load seed
    - read metadata snapshot
    - inspect physical schema
    - build diff plan
    - apply DDL
    - replace metadata snapshot

## Runtime Components

- seed loading through `SchemaSeedService`
- metadata orchestration through read/write services
- physical migration planning through `PostgresSchemaPlanService`
- physical execution through PostgreSQL inspector and executor

## Domain Model

- `DataSourceEntity`
    - tenant-scoped runtime data source and schema identity
- `ObjectEntity`
    - tenant/data_source scoped runtime object metadata
- `FieldEntity`
    - field metadata including logical type, label, nullability, default, options and settings

## Presentation / Entry Points

- no public HTTP router at the moment
- management CLI:
    - `dnk-manage schema-registry diff <tenant_id> [--seed-path ...]`
- bootstrap adapter for `tenancy`:
    - `SchemaRegistryTenantSchemaBootstrapAdapter`

## Seed And Metadata Notes

- default seed module is `src.modules.schema_registry.seed.schema_seed`
- test seed modules exist for diff experimentation
- metadata graph in MVP stores only:
    - datasource
    - objects
    - fields
- indexes, relations and constraints are inferred from seed and physical schema, not stored as full metadata graph

## Dependencies On Other Modules

- uses `shared` for UoW, identifiers and time
- exposes adapter to `tenancy` through tenancy-owned bootstrap port
- does not expose public HTTP API directly

## Tests Covering This Module

- seed service tests
- metadata read tests
- diff use case tests
- planning tests
- PostgreSQL executor tests
- repository/session-sharing tests
- management command tests

## Related

- [Management CLI](../interfaces/management-cli.md)
- [Runtime schema](../data/runtime-schema.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/schema_registry/application/use_case/create_schema_use_case.py`
- `src/modules/schema_registry/application/use_case/diff_schema_use_case.py`
- `src/modules/schema_registry/application/migration/postgres_schema_plan_service.py`
- `src/modules/schema_registry/seed/schema_seed.py`
