# Runtime Schema

`schema_registry` works with three related representations of runtime data structure.

## 1. Seed

Seed is the desired logical model declared in Python module form and exported as `SCHEMA_SEED`.

Main seed types:

- `SchemaSeed`
- `ObjectSeed`
- `FieldSeed`
- `IndexSeed`
- `RelationSeed`

Default seed module:

- `src.modules.schema_registry.seed.schema_seed`

The default seed currently declares CRM contacts plus inventory products and product categories.

## 2. Metadata Snapshot

Metadata snapshot is stored in system tables and represents the registry view of tenant runtime schema.

Current MVP scope:

- datasource
- objects
- fields

Not stored as full metadata graph in MVP:

- indexes
- relations
- constraints

## 3. Physical Tenant Schema

This is the actual PostgreSQL schema for a tenant:

- schema name like `dnk_<tenant_id_hex>`
- runtime tables
- columns
- indexes
- foreign keys

Client runtime rows do not carry a `tenant_id` column/key. Tenant isolation comes from host/domain resolution plus the
physical tenant schema selected for the request. Application code still passes the resolved `tenant_id` internally so
metadata resolution and runtime gateways can target the correct tenant schema.

Inside domain/application code that tenant scope is represented as `EntityIdVO`. Runtime metadata entities use concrete
`EntityIdVO` subclasses (`DataSourceIdVO`, `RuntimeObjectIdVO`, `RuntimeFieldIdVO`), while physical schema columns and
HTTP/CLI interfaces continue to use UUID values.

`schema_registry` inspects this physical schema and compares it with the seed.

## Seed Model

### `SchemaSeed`

- top-level manifest
- contains code, label and object list
- loaded as raw input, then normalized and semantically validated before planning

### `ObjectSeed`

- logical object definition
- contains singular/plural names, labels, description, fields, indexes and relations
- `plural_name` is used as physical table name
- `c_` is reserved for custom objects; system/standard/view seed objects must not use that prefix

### `FieldSeed`

- logical field definition
- type, label, description, nullability, default, options, settings

### `IndexSeed`

- named index with list of fields and uniqueness flag

### `RelationSeed`

- named relation that maps one source field to target object field
- used to build foreign keys in PostgreSQL planning
- `many_to_one` is supported as a source-owned foreign key
- `one_to_one` is supported as a source-owned foreign key plus unique source-field index
- `one_to_many` and `many_to_many` are rejected as unsupported in the current MVP

## Create Flow

`CreateSchemaUseCase`:

1. loads seed
2. validates seed
3. builds create plan
4. applies PostgreSQL DDL
5. writes metadata snapshot

## Diff Flow

`DiffSchemaUseCase`:

1. loads seed
2. reads existing metadata snapshot
3. inspects current PostgreSQL tenant schema
4. builds diff plan
5. applies DDL
6. reconciles metadata snapshot while preserving matching object and field ids

## Current MVP Constraints

- seed is the source of desired structure
- backend is PostgreSQL-only
- metadata graph is intentionally incomplete
- retained column type/nullability changes are restricted
- adding a required column to an existing table without a default is rejected as unsafe
- default changes for retained columns are supported through explicit migration operation
- metadata rename is not inferred heuristically; renamed natural keys behave as remove/add until explicit rename support
  exists
- custom object tables use `c_`-prefixed physical names and are preserved by seed diff when they are absent from seed
- nested bootstrap and diff must work in one active `UoW / AsyncSession`

## Related

- [Schema Registry module](../modules/schema-registry.md)
- [Management CLI](../interfaces/management-cli.md)
- [Domain models](domain-models.md)

## Source Of Truth

- `src/modules/schema_registry/domain/seed/`
- `src/modules/schema_registry/application/use_case/create_schema_use_case.py`
- `src/modules/schema_registry/application/use_case/diff_schema_use_case.py`
- `src/modules/schema_registry/application/migration/`
