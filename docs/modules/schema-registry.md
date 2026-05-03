# Schema Registry Module

## Purpose

`schema_registry` manages tenant runtime schemas in PostgreSQL and stores a metadata snapshot of runtime objects and
fields. It is responsible for bootstrap from seed, schema diff against existing tenant schemas and config-time
object/field metadata plus targeted DDL changes.

## Public Functionality

- load seed manifests from Python modules
- create tenant runtime schema from seed
- diff existing tenant runtime schema against seed
- inspect physical PostgreSQL schema
- persist metadata snapshot for datasource, objects and fields
- expose config APIs for object list/schema/create/delete and custom field create/delete

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
- config-time schema mutations through `SchemaConfigRepository`

## Config API Rules

- `ObjectKind.SYSTEM` and `ObjectKind.VIEW` are read-only and still appear in list/schema responses.
- `ObjectKind.STANDARD` appears in list/schema, cannot be deleted, and can be extended with `custom` fields.
- `ObjectKind.CUSTOM` can be created, deleted and extended with `custom` fields.
- `FieldKind.SYSTEM` stays in metadata/descriptors but is hidden from config API responses.
- `FieldKind.STANDARD` is visible in config responses but cannot be deleted.
- `FieldKind.CUSTOM` can be created and hard-deleted.
- field update/type update, custom relations and custom indexes are not part of the config API.

## Domain Model

- `DataSourceEntity`
    - tenant-scoped runtime data source and schema identity
  - uses `DataSourceIdVO` and `EntityIdVO`
- `ObjectEntity`
    - tenant/data_source scoped runtime object metadata
  - uses `RuntimeObjectIdVO`, `EntityIdVO` and `DataSourceIdVO`
- `FieldEntity`
    - field metadata including logical type, label, nullability, default, options and settings
  - uses `RuntimeFieldIdVO` and `RuntimeObjectIdVO`

## Presentation / Entry Points

- HTTP router under `/api/config`:
    - `POST /api/config/objects/list`
    - `POST /api/config/objects/create`
    - `DELETE /api/config/objects/delete`
    - `POST /api/config/objects/schema`
    - `POST /api/config/objects/fields/create`
    - `DELETE /api/config/objects/fields/delete`
- management CLI:
    - `dnk-manage schema-registry diff <tenant_id> [--seed-path ...]`
- bootstrap adapter for `tenancy`:
    - `SchemaRegistryTenantSchemaBootstrapAdapter`

## Seed And Metadata Notes

- default seed module is `src.modules.schema_registry.seed.schema_seed`
- default seed declares CRM contacts plus inventory products and product categories
- management CLI and physical schema boundaries still accept UUID tenant ids, then convert them to `EntityIdVO` inside
  application/domain code
- test seed modules exist for diff experimentation
- seed loading returns a validated and normalized schema spec before planning
- `many_to_one` relations materialize as foreign keys
- `one_to_one` relations materialize as foreign keys plus a deterministic unique index on the owning/source field
- `one_to_many` and `many_to_many` are known relation types but are rejected as unsupported in the current MVP
- metadata graph in MVP stores only:
    - datasource
    - objects
    - fields
- diff metadata sync reconciles by stable natural keys:
    - objects by plural name
    - fields by field name inside the object
- no-op diff preserves matching metadata ids; rename is not inferred heuristically
- indexes, relations and constraints are inferred from seed and physical schema, not stored as full metadata graph

## Dependencies On Other Modules

- uses `shared` for UoW, identifiers and time
- exposes adapter to `tenancy` through tenancy-owned bootstrap port
- exposes schema config HTTP endpoints for authenticated tenant context

## Tests Covering This Module

- seed service tests
- schema config repository tests
- schema config HTTP router/controller tests
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
- `src/modules/schema_registry/application/config/`
- `src/modules/schema_registry/infrastructure/config/schema_config_repository.py`
- `src/modules/schema_registry/presentation/http/config/`
- `src/modules/schema_registry/application/migration/postgres_schema_plan_service.py`
- `src/modules/schema_registry/seed/schema_seed.py`
