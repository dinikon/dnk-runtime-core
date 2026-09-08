> Historical documentation. The dynamic modules have been removed; this page is not the current architecture. See [tenant migrations](../../data/tenant-migrations.md).

# Schema Registry Module

## Purpose

`schema_registry` владеет описанием runtime-схем tenant-данных: загружает seed-манифест, валидирует его в
`ValidatedSchemaSpec`, строит и применяет PostgreSQL DDL, хранит metadata-граф datasource/object/field/relation и
отдает runtime descriptors потребителям runtime data.

Модуль управляет структурой runtime objects, но не выполняет CRUD runtime-записей. Чтение и запись строк находятся в
`runtime_data` и будущих потребителях descriptors.

## Current Scope

Текущая реализация покрывает несколько связанных subdomain внутри одного bounded context:

- bootstrap новой tenant PostgreSQL schema из Python seed-модуля через `CreateSchemaUseCase`;
- diff существующей tenant schema против seed/spec через `DiffSchemaUseCase`;
- metadata storage для `data_sources`, `objects`, `fields`, `relations`;
- config API для custom objects, custom fields и custom relations;
- runtime descriptor resolver для gateway/use case потребителей;
- adapter для `tenancy` onboarding через `SchemaRegistryTenantSchemaBootstrapAdapter`;
- management CLI `dnk-manage schema-registry diff`.

В текущей реализации не найдено:

- CRUD runtime-записей внутри `schema_registry`;
- background jobs, scheduled jobs, message consumers, outbox/inbox;
- эвристический rename объектов/полей/relations при diff.

## Public Functionality

- создать физическую PostgreSQL schema tenant и записать initial metadata из default или custom seed;
- применить diff seed/spec к уже существующей tenant schema;
- получить runtime object description по singular name;
- resolve runtime object descriptor по singular name или object id;
- создать, описать, перечислить и удалить custom object;
- добавить и удалить custom field у `standard` или `custom` object;
- создать, удалить и перечислить custom relations для object;
- проинспектировать PostgreSQL schema и применить migration plan;
- запустить schema diff из management CLI.

## Main Flows / Use Cases

| Use Case                           | Input                              | Output                        | Description                                                                                                                                                   |
|------------------------------------|------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CreateSchemaUseCase`              | `CreateSchemaCommand`              | `None`                        | Загружает seed, проверяет отсутствие physical schema, строит create plan, применяет DDL и записывает datasource/object/field/relation metadata.               |
| `DiffSchemaUseCase`                | `DiffSchemaCommand`                | `DiffSchemaResultDTO`         | Загружает seed, читает metadata snapshot, инспектирует physical schema, строит diff plan с preserved relation artifacts, применяет DDL и reconciles metadata. |
| `DescribeRuntimeObjectUseCase`     | `tenant_id`, `object_name`         | `RuntimeObjectDescriptionDTO` | Проверяет datasource/object consistency и возвращает описание fields; при наличии relation service добавляет relation descriptions через resolver.            |
| `ListCustomObjectsUseCase`         | `ListCustomObjectsQuery`           | `list[CustomObjectDTO]`       | Возвращает runtime objects tenant для config API через `SchemaConfigRepositoryProtocol`.                                                                      |
| `CreateCustomObjectUseCase`        | `CreateCustomObjectCommand`        | `CustomObjectDTO`             | Создает custom object metadata, system fields и physical table через config repository.                                                                       |
| `DescribeCustomObjectUseCase`      | `CustomObjectByIdQuery`            | `CustomObjectDTO`             | Возвращает config-схему runtime object по id.                                                                                                                 |
| `DeleteCustomObjectUseCase`        | `DeleteCustomObjectCommand`        | `None`                        | Hard-delete custom object table и metadata.                                                                                                                   |
| `AddCustomFieldUseCase`            | `AddCustomFieldCommand`            | `CustomObjectDTO`             | Добавляет custom field metadata и physical column.                                                                                                            |
| `DeleteCustomFieldUseCase`         | `DeleteCustomFieldCommand`         | `CustomObjectDTO`             | Удаляет custom field metadata и physical column.                                                                                                              |
| `CreateRelationUseCase`            | `CreateRelationCommand`            | `RelationDTO`                 | Создает custom FK-based или M2M relation, сначала применяя targeted DDL.                                                                                      |
| `DeleteRelationUseCase`            | `DeleteRelationCommand`            | `None`                        | Удаляет custom relation и physical artifacts после safety checks по данным.                                                                                   |
| `ListObjectRelationsUseCase`       | `ListObjectRelationsQuery`         | `list[RelationDTO]`           | Возвращает relations, где object является source или target.                                                                                                  |

## Domain Model

### `DataSourceEntity`

- ID: `DataSourceIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO`.
- Fields: `id`, `created_at`, `updated_at`, `tenant_id`, `data_source_type`, `schema_name`, optional
  `connection_dsn`.
- Value Objects: `DataSourceIdVO`, `SchemaNameVO`, `DataSourceTypeVO`, `ConnectionDsnVO`.
- Factory methods: `DataSourceEntity.create(...)` выставляет timestamps и default `POSTGRES`.
- Update methods: в entity не найдено.
- Domain errors: `DataSourceAlreadyExistsError`, `DataSourceNotFoundError`.
- Invariants: `SchemaNameVO` требует lowercase PostgreSQL identifier до 63 символов.

### `ObjectEntity`

- ID: `RuntimeObjectIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO` и `data_source_id: DataSourceIdVO`.
- Fields: timestamps, `kind`, `object_name`, `object_label`, `description`, `fields`.
- Value Objects: `ObjectNameVO`, `ObjectLabelVO`, `ObjectKind`, `RuntimeObjectIdVO`.
- Factory methods: `ObjectEntity.create(...)`, `add_field(...)`, `add_fields_from_seed(...)`.
- Update methods: `rename(...)`, `rename_field(...)`, `remove_field(...)`, `replace_field_settings(...)`,
  `merge_field_settings(...)`, `replace_field_options(...)`.
- Domain errors: `FieldAlreadyExistsError`, `FieldNotFoundError`, `ObjectNameAlreadyExistsError`,
  `InvalidObjectOperationError`.
- Invariants: singular/plural names are PostgreSQL identifiers; plural name must end with `s`; field names are unique
  inside object; only `custom` objects can be deleted; `standard` and `custom` can accept custom fields.

### `FieldEntity`

- ID: `RuntimeFieldIdVO`.
- Tenant scope: indirect через owning `ObjectEntity.object_id`.
- Fields: timestamps, `object_id`, `kind`, `field_name`, `field_type`, `label`, `description`, `is_nullable`,
  `default_value`, `options`, `settings`.
- Value Objects: `FieldNameVO`, `FieldLabelVO`, `FieldTypeVO`, `FieldKind`, `RuntimeFieldIdVO`.
- Factory methods: `FieldEntity.create(...)`.
- Update methods: `rename(...)`, `replace_settings(...)`, `merge_settings(...)`, `replace_options(...)`,
  `clear_options(...)`, `update_from_spec(...)`.
- Domain errors: `InvalidFieldOperationError`, `FieldAlreadyExistsError`, `FieldNotFoundError`.
- Invariants: `options` разрешены только для `select`/`multiselect`; изменение типа существующего поля запрещено через
  `change_type(...)`; удалить можно только `FieldKind.CUSTOM`; system fields не patch-ятся как обычные runtime fields.

### `RelationEntity`

- ID: `RuntimeRelationIdVO`.
- Tenant scope: хранит `tenant_id: EntityIdVO` и `data_source_id: DataSourceIdVO`.
- Fields: source/target object ids, owning/referenced sides, optional FK field ids, relation API names, optional M2M
  table/join column names, `on_delete`, `is_required`, `is_unique`, `kind`, `settings`.
- Value Objects: `RuntimeRelationIdVO`, `RuntimeObjectIdVO`, `RuntimeFieldIdVO`, `RelationTypeEnum`.
- Factory methods: `RelationEntity.create(...)`.
- Update methods: в entity не найдено.
- Domain errors: `RelationNotFoundError`, `InvalidRelationOperationError`, `UnsupportedSchemaChangeError`.
- Invariants: `RelationService` preserves existing relation ids by name during reconcile, forbids changing physical
  shape of existing seed relation, and preserves non-seed relations only while referenced objects/fields still exist.

### Seed And Runtime Descriptor Models

- Raw seed dataclasses: `SchemaSeed`, `ObjectSeed`, `FieldSeed`, `IndexSeed`, `RelationSeed`.
- Validated spec dataclasses: `ValidatedSchemaSpec`, `ValidatedObjectSpec`, `ValidatedFieldSpec`,
  `ValidatedIndexSpec`, `ValidatedRelationSpec`.
- Runtime descriptors: `RuntimeObjectDescriptor`, `RuntimeFieldDescriptor`, `RuntimeRelationDescriptor`.
- Supported seed field types: `uuid`, `text`, `int`, `decimal`, `bool`, `date`, `datetime`, `json`, `select`,
  `multiselect`, `reference`.
- Supported relation types: `many_to_one`, `one_to_one`, `one_to_many`, `many_to_many`.

## Application Layer

### Commands

Все command/input dataclasses оформлены как `@dataclass(frozen=True, slots=True)`:

- `CreateSchemaCommand`: `tenant_id`, `schema_name`, `seed_path`;
- `DiffSchemaCommand`: `tenant_id`, `seed_path`;
- `CreateCustomObjectCommand`: tenant id, singular/plural names, labels, description, initial `CustomFieldInput`;
- `DeleteCustomObjectCommand`: `tenant_id`, `object_id`;
- `AddCustomFieldCommand`: `tenant_id`, `object_id`, `CustomFieldInput`;
- `DeleteCustomFieldCommand`: `tenant_id`, `object_id`, `field_id`;
- `CreateRelationCommand`: `tenant_id`, `RelationInput`;
- `DeleteRelationCommand`: `tenant_id`, `relation_id`.

### Queries

- `ListCustomObjectsQuery`: `tenant_id`.
- `CustomObjectByIdQuery`: `tenant_id`, `object_id`.
- `ListObjectRelationsQuery`: `tenant_id`, `object_id`.

### DTOs

- `DiffSchemaResultDTO`: статистика diff plan и destructive/non-destructive операций.
- `RuntimeObjectDescriptionDTO`, `RuntimeFieldDescriptionDTO`, `RuntimeRelationDescriptionDTO`: application DTO для
  model/schema descriptions.
- `CustomObjectDTO`, `CustomFieldDTO`: config API object/field result.
- `RelationDTO`: config API relation result with object/field ids, physical names and settings.

### Services

- `SchemaSeedService` читает seed через `SeedReaderPort`, нормализует names/kinds/defaults/options/indexes/relations и
  возвращает `ValidatedSchemaSpec`.
- `PostgresSchemaService` координирует `TenantSchemaInspectorPort` и `TenantSchemaExecutorPort`.
- `SchemaRegistryMetadataReadService` собирает `SchemaRegistryMetadataSnapshot` и проверяет tenant/data_source/object/
  field consistency.
- `SchemaRegistryMetadataWriteService` создает, заменяет или reconciles datasource/object/field/relation metadata.
- `PostgresSchemaPlanService` строит create/diff `MigrationPlan`.
- `PostgresFieldCanonicalizer` мапит field types в SQL presets и канонизирует seed/PostgreSQL defaults.

### Runtime Resolver

- `SchemaRegistryRuntimeObjectResolver.resolve(tenant_id, object_name)` ищет object по singular name.
- `resolve_by_id(tenant_id, object_id)` ищет object по id.
- Resolver проверяет tenant/data_source consistency, требует наличие field `id`, строит immutable
  `RuntimeObjectDescriptor` и возвращает `relations=()` без `RelationService`.
- Field capabilities берутся из defaults by type и могут переопределяться через `settings` keys `is_filterable`,
  `filterable`, `is_sortable`, `sortable`.
- Relation descriptors вычисляют `is_collection`: `many_to_many` на обеих сторонах, `one_to_many` на source side,
  `many_to_one` на target side, `one_to_one` never collection.
- Relation descriptors вычисляют `is_virtual`: `many_to_many` всегда virtual; FK-based relation virtual, если текущий
  object не является owning object.

### Seed And Migration Rules

- `ObjectKind.CUSTOM` нормализуется в `c_` namespace; non-custom objects не могут использовать `c_` prefix.
- `FieldTypeCatalog` поддерживает seed types `uuid`, `text`, `int`, `decimal`, `bool`, `date`, `datetime`, `json`,
  `select`, `multiselect`, `reference`.
- `PostgresFieldCanonicalizer` maps seed types to SQL presets: `reference` and `uuid` to `uuid`, `decimal` to
  `numeric(14,2)`, `datetime` to `timestamp with time zone`, `json`/`multiselect` to `jsonb`.
- Defaults canonicalization нормализует `now()`/`current_timestamp` в `CURRENT_TIMESTAMP`, SQL strings, UUID functions,
  booleans, numbers and jsonb literals.
- `SchemaNamingStrategy` validates PostgreSQL identifiers with `^[a-z][a-z0-9_]*$`, max length 63, and shortens
  generated identifiers with deterministic hash suffix.
- Create plan order: create schema, create tables, add columns, add primary keys, create indexes, add foreign keys.
- Diff plan protects custom `c_` tables and custom relation artifacts while all referenced objects/fields survive.
  Relations that reference retired seed objects are removed before those objects, including join tables and custom FK
  columns. Retained column type changes and unsafe
  `nullable -> not null` changes are rejected.
- FK-based relations require `reference` FK field and referenced field `id` or another unique field in seed planning.
- `many_to_many` relations create join table with `id`, `created_at`, two UUID join columns, primary key, unique pair
  index, FK indexes and two FK constraints.

### Repository Protocols

- `DataSourceRepositoryProtocol`: `get_by_tenant_id`, `add`, `update`.
- `ObjectRepositoryProtocol`: read by singular/plural/id, `save`, `list_by_tenant_id`, `replace_all_for_tenant`,
  `reconcile_for_tenant`.
- `RelationRepositoryProtocol`: read by id/name/object/tenant, `add`, `delete`, `replace_all_for_tenant`,
  `clear_for_tenant`, `reconcile_for_tenant`.
- `SchemaConfigRepositoryProtocol`: config object list/describe/create/delete.
- `SchemaConfigFieldRepositoryProtocol`: config field add/delete.
- `SchemaConfigRelationRepositoryProtocol`: config relation create/delete/list.
- `SeedReaderPort`, `TenantSchemaInspectorPort`, `TenantSchemaExecutorPort`.

## Infrastructure / Persistence

### `SqlAlchemyDataSourceRepository`

- File: `src/modules/schema_registry/infrastructure/repository/data_source_repository.py`.
- Implements: `DataSourceRepositoryProtocol`.
- Storage: SQLAlchemy ORM table `data_sources`.
- Runtime object: не используется.
- Tenant handling: repository не хранит tenant; методы принимают `EntityIdVO`.
- Mapping: `_to_model` и `_map_model` явно конвертируют `UUID` в `DataSourceIdVO`/`EntityIdVO`.
- Errors: not-found возвращается как `None`; domain errors поднимает service layer.

### `SqlAlchemyObjectRepository`

- File: `src/modules/schema_registry/infrastructure/repository/object_repository.py`.
- Implements: `ObjectRepositoryProtocol`.
- Storage: SQLAlchemy ORM tables `objects` и `fields`.
- Runtime object: не используется.
- Tenant handling: repository не хранит tenant; tenant передается в query/reconcile methods.
- Mapping: `_map_model` строит `ObjectEntity`, `_map_field_model` строит `FieldEntity`; `save` заменяет field rows для
  одного object.
- Errors: not-found возвращается как `None`.

### `SqlAlchemyRelationRepository`

- File: `src/modules/schema_registry/infrastructure/repository/relation_repository.py`.
- Implements: `RelationRepositoryProtocol`.
- Storage: SQLAlchemy ORM table `relations`.
- Runtime object: не используется.
- Tenant handling: repository не хранит tenant; list/delete/reconcile фильтруются по `tenant_id`.
- Mapping: `_to_model` и `_map_model` конвертируют relation ids, object ids, field ids и `RelationTypeEnum`.
- Errors: not-found возвращается как `None`.

### `SchemaConfigRepository`

- File: `src/modules/schema_registry/infrastructure/config/schema_config_repository.py`.
- Implements: `SchemaConfigRepositoryProtocol`, `SchemaConfigFieldRepositoryProtocol`,
  `SchemaConfigRelationRepositoryProtocol`.
- Storage: metadata через object/relation repositories; physical DDL через `TenantSchemaExecutorPort`; safety checks
  through `TenantSchemaInspectorPort`.
- Runtime object: создает physical tables/columns/indexes/FK для custom config, но не работает с runtime rows.
- Tenant handling: каждый command/query содержит `tenant_id`; datasource schema name читается через `DataSourceService`.
- Mapping: `_to_object_dto`, `_to_field_dto`, `_to_relation_dto`; system fields скрываются из object config responses.
- Errors: `ObjectNotFoundError`, `FieldNotFoundError`, `RelationNotFoundError`, `Invalid*OperationError`,
  `UnsupportedSchemaChangeError`, `ObjectNameAlreadyExistsError`.
- Key behavior:
  - custom object names нормализуются в `c_` namespace;
  - new custom object получает system fields `id`, `created_at`, `updated_at`;
  - required field without default запрещен для existing object;
  - delete relation запрещен, если M2M table has rows или FK column has non-null values;
  - config-created FK relations в MVP могут ссылаться только на referenced field `id`.

### `PythonModuleSeedReader`

- File: `src/modules/schema_registry/infrastructure/seed/python_module_seed_reader.py`.
- Implements: `SeedReaderPort`.
- Storage: импортирует Python module path и читает `SCHEMA_SEED`.
- Errors: `SeedValidationError`, если path пустой, module не найден, `SCHEMA_SEED` отсутствует или имеет неверный тип.

### PostgreSQL Adapters

- `PostgresTenantSchemaInspector` читает physical schema через `information_schema` и `pg_catalog`, включая tables,
  columns, primary keys, non-primary indexes, foreign keys, `table_has_rows`, `column_has_non_null_values`.
- `PostgresTenantSchemaExecutor` последовательно рендерит и выполняет DDL operations из `MigrationPlan`.
- Оба adapters требуют SQLAlchemy bind с dialect `postgresql`; иначе поднимают `UnsupportedSchemaBackendError`.

### `SchemaRegistryTenantSchemaBootstrapAdapter`

- File: `src/modules/schema_registry/infrastructure/tenancy_schema_bootstrap_adapter.py`.
- Implements: tenancy-owned `TenantSchemaBootstrapPort`.
- Behavior: переводит `TenantSchemaBootstrapContext` в `CreateSchemaCommand` и вызывает `CreateSchemaUseCase.execute`.

## Presentation / HTTP API

Base prefix:

```text
/api
```

`src/modules/router.py` подключает `schema_registry` router under `/api`; сам router не добавляет отдельный module
prefix. Все HTTP endpoints требуют `AuthenticatedRequestContextDep`; `tenant_id` берется из principal, не из payload.

| Method   | Path                                   | Controller               | Use Case                      | Request                            | Response                            |
|----------|----------------------------------------|--------------------------|-------------------------------|------------------------------------|-------------------------------------|
| `POST`   | `/api/config/objects/list`             | `list_custom_objects`    | `ListCustomObjectsUseCase`    | none                               | `ListCustomObjectsResponseSchema`   |
| `POST`   | `/api/config/objects/create`           | `create_custom_object`   | `CreateCustomObjectUseCase`   | `CreateCustomObjectRequestSchema`  | `CustomObjectResponseSchema`, `201` |
| `DELETE` | `/api/config/objects/delete`           | `delete_custom_object`   | `DeleteCustomObjectUseCase`   | `ObjectIdRequestSchema`            | empty `204`                         |
| `POST`   | `/api/config/objects/schema`           | `describe_custom_object` | `DescribeCustomObjectUseCase` | `ObjectIdRequestSchema`            | `CustomObjectResponseSchema`        |
| `POST`   | `/api/config/objects/fields/create`    | `create_custom_field`    | `AddCustomFieldUseCase`       | `CreateCustomFieldRequestSchema`   | `CustomObjectResponseSchema`        |
| `DELETE` | `/api/config/objects/fields/delete`    | `delete_custom_field`    | `DeleteCustomFieldUseCase`    | `DeleteCustomFieldRequestSchema`   | `CustomObjectResponseSchema`        |
| `POST`   | `/api/config/objects/relations/create` | `create_relation`        | `CreateRelationUseCase`       | `CreateRelationRequestSchema`      | `RelationResponseSchema`, `201`     |
| `DELETE` | `/api/config/objects/relations/delete` | `delete_relation`        | `DeleteRelationUseCase`       | `DeleteRelationRequestSchema`      | empty `204`                         |
| `POST`   | `/api/config/objects/relations/list`   | `list_relations`         | `ListObjectRelationsUseCase`  | `ListObjectRelationsRequestSchema` | `ListRelationsResponseSchema`       |
| `POST`   | `/api/config/objects/relations/schema` | `relation_schema`        | `ListObjectRelationsUseCase`  | `ListObjectRelationsRequestSchema` | `ListRelationsResponseSchema`       |

HTTP error mapping:

- `401`: missing principal or tenant id.
- `404`: `ObjectNotFoundError`, `FieldNotFoundError`, `RelationNotFoundError` in endpoints that catch them.
- `409`: `PhysicalSchemaNotFoundError`, `RuntimeObjectDescriptorError`, `SchemaRegistryMetadataInconsistentError`,
  `UnsupportedSchemaBackendError`.
- `422`: remaining `SchemaRegistryError` and shared `DomainError`.

## Dependency Injection

- Infrastructure dependencies:
  - `presentation/depends/infrastructure.py` creates `PythonModuleSeedReader`, PostgreSQL inspector/executor,
    SQLAlchemy repositories, id providers, `FieldTypeCatalog`, `PostgresFieldCanonicalizer`, domain services.
  - Repositories/adapters share current `UoWDep.session`.
- Application dependencies:
  - `presentation/depends/application.py` creates seed/schema/metadata services, `CreateSchemaUseCase`,
    `DiffSchemaUseCase`, `DescribeRuntimeObjectUseCase`, `SchemaRegistryRuntimeObjectResolver`.
- Config dependencies:
  - `presentation/depends/config.py` creates one `SchemaConfigRepository` and exposes it under object/field/relation
    Protocol aliases, then wires config use cases.
- Management dependencies:
  - `presentation/depends/management.py` builds `DiffSchemaUseCase` outside FastAPI from explicit `UnitOfWorkProtocol`
    and `ClockPort`.
- Shared dependencies:
  - `UoWDep`, `ClockDep`, `AuthenticatedRequestContextDep`, `EntityIdVO`, `UnitOfWork`, `UtcClock`.

## Dependencies On Other Modules

| Module          | Layer                                                    | Used For                                                                                                       |
|-----------------|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `shared`        | all layers                                               | `EntityIdVO`, `DomainError`, clock ports, UoW/session, DB base/types, authentication dependency.               |
| `tenancy`       | infrastructure/presentation DI                           | `TenantSchemaBootstrapPort` and `TenantSchemaBootstrapContext` adapter for tenant onboarding.                  |
| `runtime_data`  | consumer dependency, not imported by module code for DDL | Consumers use `RuntimeObjectDescriptor`; schema_registry itself does not do runtime row CRUD.                  |
| `config`        | management/bootstrap                                     | `dnk_config.DEFAULT_SEED_MODULE` and `SCHEMA_PREFIX`.                                                          |

## Events / Background Processing

В текущей реализации не найдено event handlers, message consumers, scheduled jobs, queues, outbox или inbox.

Найден management command:

```bash
dnk-manage schema-registry diff <tenant_id> [--seed-path ...]
dnk-manage schema-registry diff --all [--seed-path ...]
```

Command зарегистрирован в `src/management/commands/schema_registry.py`. Default `seed_path` берется из
`dnk_config.DEFAULT_SEED_MODULE`, который указывает на `src.modules.schema_registry.seed.schema_seed`.
Режим `--all` проходит по всем tenants без status-фильтрации, использует savepoint на tenant и откатывает весь batch,
если хотя бы один tenant завершился ожидаемой `SchemaRegistryError`.

## Tests Covering This Module

Тесты находятся в каталоге `test/`. Каталог `tests/` в текущем workspace не найден.

- Domain:
  - `test/test_schema_registry_object_label.py`;
  - `test/test_schema_registry_field_type_service.py`;
  - relation/seed/domain validation scenarios in `test/test_schema_registry_seed_service.py`.
- Application:
  - `test/test_schema_registry_use_case.py`;
  - `test/test_schema_registry_diff_use_case.py`;
  - `test/test_schema_registry_describe_runtime_object_use_case.py`;
  - `test/test_schema_registry_metadata_read_service.py`;
  - `test/test_schema_registry_metadata_write_service.py`;
  - `test/test_schema_registry_planning.py`.
- Infrastructure:
  - `test/test_schema_registry_repositories.py`;
  - `test/test_schema_registry_postgres_executor.py`;
  - `test/test_schema_config_repository.py`;
  - `test/test_schema_registry_depends.py`.
- Presentation:
  - `test/test_schema_config_http_router.py`;
  - `test/test_management_schema_registry_command.py`.
- Integration / boundary:
  - `test/test_tenant_schema_bootstrap_boundary.py`;
  - `test/test_architecture_boundaries.py`;
  - `test/test_default_schema_seed.py` covers the empty default runtime manifest;
  - runtime descriptor usage is also covered by runtime_data tests.

Important gaps:

- `test/test_schema_config_http_router.py` currently checks object/field config routes but does not assert relation
  config routes.
- HTTP controller error mapping is tested indirectly in consumers more than directly for every schema_registry config
  route.

## Known Gaps / Technical Debt

- Текущее отклонение от prompt path convention: canonical file is `docs/modules/schema-registry.md`; requested
  underscore path is not used because existing docs link to the hyphen path.
- Тестовый каталог называется `test/`, not `tests/`.
- `SchemaConfigRepository` combines object/field/relation metadata operations and targeted PostgreSQL DDL in one large
  infrastructure adapter.
- `CreateSchemaUseCase` and `DiffSchemaUseCase` expose `execute(...)`, while `docs/develop-style.md` prefers async
  `__call__(...)` for use cases.
- Several HTTP controllers repeat error-mapping blocks; some object/field controllers include duplicated
  `SchemaRegistryError` entries in `except` tuples.
- `SchemaConfigRepository` type hints use a few broad/internal types, for example untyped `data_source_id` and
  `command` parameters in private relation helpers.
- `ObjectORM` has unique constraint only for `(tenant_id, plural_name)`; singular uniqueness is enforced by service/
  repository logic, not by DB constraint.

## Related Documentation

- [Develop Style](../../develop-style.md)
- [Runtime Schema](../data/runtime-schema.md)
- [HTTP API](../../interfaces/http-api.md)
- [Management CLI](../../interfaces/management-cli.md)
- [Persistence and Unit of Work](../../architecture/persistence-and-uow.md)
- [Test Map](../../quality/test-map.md)

## Source Of Truth

- `src/modules/schema_registry/domain/`
- `src/modules/schema_registry/application/`
- `src/modules/schema_registry/infrastructure/`
- `src/modules/schema_registry/presentation/`
- `src/modules/schema_registry/runtime/`
- `src/modules/schema_registry/seed/schema_seed.py`
- `src/modules/schema_registry/seed/common.py`
- `src/modules/schema_registry/seed/contexts/`
- `src/management/commands/schema_registry.py`
- `test/test_schema_registry_*.py`
- `test/test_schema_config_*.py`
- `test/test_management_schema_registry_command.py`
- `test/test_tenant_schema_bootstrap_boundary.py`
