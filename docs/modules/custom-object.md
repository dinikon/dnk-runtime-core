# Custom Object Module

## Purpose

`custom_object` owns tenant-scoped record CRUD for objects whose schema descriptor has `kind=custom`.
Schema metadata, object/field configuration and physical DDL belong to `schema_registry` config APIs.

## Public Functionality

- create custom-object records
- get a custom-object record by `object_id` and `row_id`
- list custom-object records with recursive filter DSL and ordered sort map
- patch/put custom-object records
- delete custom-object records

## Main Flows / Use Cases

- `CreateCustomRecordUseCase`
- `GetCustomRecordUseCase`
- `ListCustomRecordsUseCase`
- `UpdateCustomRecordUseCase`
- `DeleteCustomRecordUseCase`

## Domain Model

- `object_id` is a `schema_registry.RuntimeObjectIdVO`
- records are generic runtime rows returned as `{ object_id, row_id, values }`
- system fields such as `id`, `created_at` and `updated_at` are immutable in write payloads
- non-custom descriptors are rejected; standard CRM records and future standard modules are handled by their owning
  modules

## Infrastructure / Persistence

- `CustomRecordRuntimeRepository` resolves descriptors through `schema_registry` by `object_id`
- record CRUD uses `PostgresRuntimeGateway`
- filters and sorting are delegated to `runtime_data`
- the module does not use schema DDL ports, object metadata repositories or schema config use cases

## Presentation / Entry Points

All current custom object routes live under `/api/custom-objects/records`.

All read endpoints use `POST` request bodies instead of `GET`.
All routes require authenticated request context.

## Dependencies On Other Modules

- uses `shared` authentication, generic tenant scope ids and UoW dependencies
- uses `schema_registry` runtime descriptor resolver
- uses `runtime_data` for dynamic record CRUD, filtering and sorting

## Tests Covering This Module

- custom object record use case tests
- custom object controller error tests
- custom object router tests
- runtime data nested filter tests
- architecture guard that `custom_object` does not own schema config or DDL

## Related

- [HTTP API](../interfaces/http-api.md)
- [Runtime schema](../data/runtime-schema.md)
- [Schema Registry module](schema-registry.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/custom_object/application/record/`
- `src/modules/custom_object/infrastructure/custom_record_runtime_repository.py`
- `src/modules/custom_object/presentation/http/record/controller/`
