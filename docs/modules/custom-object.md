# Custom Object Module

## Purpose

`custom_object` exposes tenant-scoped custom runtime objects, their fields and their records. It uses
`schema_registry` metadata plus targeted PostgreSQL DDL and reads/writes rows through `runtime_data`.

## Public Functionality

- list custom objects
- create custom object with automatic system fields
- hard-delete custom object and its physical table
- get object schema and fields
- add and delete custom fields
- create, read, list, update and delete records for custom objects

## Main Flows / Use Cases

- `CreateCustomObjectUseCase`
- `DescribeCustomObjectUseCase`
- `ListCustomObjectsUseCase`
- `DeleteCustomObjectUseCase`
- `AddCustomFieldUseCase`
- `DeleteCustomFieldUseCase`
- `CreateCustomRecordUseCase`
- `GetCustomRecordUseCase`
- `ListCustomRecordsUseCase`
- `UpdateCustomRecordUseCase`
- `DeleteCustomRecordUseCase`

## Domain Model

- custom objects are stored as `schema_registry.ObjectEntity` with `kind=custom`
- custom fields are stored as `schema_registry.FieldEntity` with `kind=custom`
- every custom object gets system fields:
    - `id`
    - `created_at`
    - `updated_at`
- records are tenant runtime rows in the physical tenant schema

## Infrastructure / Persistence

- metadata operations use the existing schema registry object repository and datasource service
- object and field schema mutations are implemented by `CustomObjectSchemaRepository`
- record operations are implemented by `CustomRecordRuntimeRepository`
- physical schema mutations use targeted migration operations:
    - create/drop table
    - add/drop column
    - automatic unique index on `id`
- record CRUD uses `PostgresRuntimeGateway`
- adding a required field to an existing object without a default is rejected as unsafe
- object and field delete operations are hard deletes and physically remove data

## Presentation / Entry Points

All current custom object routes live under `/api/custom-objects`.

All read endpoints use `POST` request bodies instead of `GET`, including list/detail/schema endpoints.
All routes require authenticated request context.

## Dependencies On Other Modules

- uses `shared` authentication, generic tenant scope ids, UoW and clock dependencies
- uses `schema_registry` metadata, field type catalog and DDL executor
- uses `runtime_data` for dynamic record CRUD and filtering

## Tests Covering This Module

- custom object schema store tests
- custom object record use case tests
- custom object controller error tests
- custom object router tests
- runtime data nested filter tests

## Related

- [HTTP API](../interfaces/http-api.md)
- [Runtime schema](../data/runtime-schema.md)
- [Schema Registry module](schema-registry.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/custom_object/application/object/`
- `src/modules/custom_object/application/field/`
- `src/modules/custom_object/application/record/`
- `src/modules/custom_object/infrastructure/custom_object_schema_repository.py`
- `src/modules/custom_object/infrastructure/custom_record_runtime_repository.py`
- `src/modules/custom_object/presentation/http/object/controller/`
- `src/modules/custom_object/presentation/http/field/controller/`
- `src/modules/custom_object/presentation/http/record/controller/`
