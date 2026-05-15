# Модуль `schema_registry`

`schema_registry` управляет runtime-схемами tenant-данных: загружает seed-описание, создает физическую PostgreSQL
schema, сравнивает фактическую структуру с желаемой, хранит metadata-граф объектов/полей/связей и отдает runtime
descriptors для модулей, которые читают и пишут tenant data.

Модуль является владельцем metadata и DDL для runtime objects. CRUD самих записей находится в `runtime_data`,
`crm`, `inventory`, `custom_object` и других потребителях.

## Основные обязанности

- bootstrap новой tenant-схемы из seed-модуля через `CreateSchemaUseCase`;
- diff существующей tenant-схемы против seed через `DiffSchemaUseCase`;
- PostgreSQL inspection/execution для tenant schemas;
- хранение metadata snapshot: datasource, objects, fields, relations;
- config API для custom objects, custom fields и custom relations;
- runtime resolver, который превращает metadata в `RuntimeObjectDescriptor`;
- adapter для `tenancy` через `SchemaRegistryTenantSchemaBootstrapAdapter`.

## Три слоя runtime-схемы

### 1. Seed и validated spec

Seed - это Python-модуль, экспортирующий `SCHEMA_SEED`.

Основные raw-типы:

- `SchemaSeed` - top-level manifest с `version`, `code`, `label`, `objects`;
- `ObjectSeed` - runtime object: singular/plural names, labels, fields, indexes, relations, kind;
- `FieldSeed` - runtime field: name, type, label, nullability, default, options, settings, kind;
- `IndexSeed` - physical index по списку полей;
- `RelationSeed` - связь между runtime objects.

`SchemaSeedService` загружает raw seed через `SeedReaderPort`, нормализует его и возвращает `ValidatedSchemaSpec`.
Планирование relations требует именно validated spec: raw seed с relations не должен напрямую идти в
`PostgresSchemaPlanService`.

Default seed:

- `src.modules.schema_registry.seed.schema_seed`

Он содержит CRM, inventory, company/contact M2M и communication runtime objects.

### 2. Metadata snapshot

Metadata хранится в системных таблицах приложения и является registry-представлением tenant runtime schema.

Текущий metadata graph:

- `data_sources` / `DataSourceEntity`
    - tenant-scoped datasource;
    - хранит `tenant_id`, `schema_name`, datasource id;
- `objects` / `ObjectEntity`
    - runtime object metadata;
    - хранит `tenant_id`, `data_source_id`, `kind`, singular/plural names, labels, description;
- `fields` / `FieldEntity`
    - runtime field metadata внутри object;
    - хранит field name, type, kind, label, nullable, default, options, settings;
- `relations` / `RelationEntity`
    - relation metadata между runtime objects;
    - хранит source/target objects, physical owner side, FK field, referenced field, API names, M2M table/columns,
      `on_delete`, `is_required`, `is_unique`, `kind`, `settings`.

`SchemaRegistryMetadataReadService` собирает snapshot и проверяет связность: tenant/data_source должны совпадать у
objects/relations, relation object ids должны ссылаться на известные objects, relation field ids - на известные fields.

`SchemaRegistryMetadataWriteService` записывает metadata после create/diff и синхронизирует objects/relations с
validated spec.

### 3. Physical tenant schema

Физический слой - PostgreSQL schema tenant-а, например `dnk_<tenant_id_hex>`.

В ней находятся:

- runtime tables;
- columns;
- primary keys;
- indexes;
- foreign keys;
- M2M join tables.

Runtime rows не несут `tenant_id`: isolation достигается выбором tenant schema после host/domain/auth resolution.
Внутри application/domain tenant scope передается как `EntityIdVO`, а HTTP/CLI boundary работает с UUID.

## Seed contract

### Object naming и `kind`

`ObjectSeed` задает `singular_name` и `plural_name`.

- `plural_name` используется как физическое имя таблицы.
- `singular_name` используется как runtime object/model name.
- Имена объектов должны быть уникальны отдельно по singular и plural.
- `ObjectKind.CUSTOM` автоматически нормализуется в namespace `c_`.
- `ObjectKind.STANDARD`, `ObjectKind.SYSTEM`, `ObjectKind.VIEW` не имеют права использовать `c_` prefix.
- `c_` зарезервирован под пользовательские objects и physical custom tables.

Object kinds:

| Kind       | Поведение                                                                                                  |
|------------|------------------------------------------------------------------------------------------------------------|
| `system`   | Системный объект. Read-only для config API. Не должен использоваться как custom relation side.             |
| `standard` | Seed-defined объект. Видим в config API, не удаляется, может расширяться custom fields и custom relations. |
| `custom`   | Пользовательский объект. Может создаваться/удаляться через config API, расширяться fields/relations.       |
| `view`     | Metadata-only/read-only режим для будущих view-объектов. Не используется как physical side relation.       |

### Field types

Поддержанные seed field types:

| Seed type     | SQL preset                    |
|---------------|-------------------------------|
| `uuid`        | `uuid`                        |
| `text`        | `text`                        |
| `int`         | `integer`                     |
| `decimal`     | `numeric(14,2)`               |
| `bool`        | `boolean`                     |
| `date`        | `date`                        |
| `datetime`    | `timestamp without time zone` |
| `json`        | `jsonb`                       |
| `select`      | `text`                        |
| `multiselect` | `jsonb`                       |
| `reference`   | `uuid`                        |

Rules:

- тип нормализуется через `FieldTypeCatalog.from_seed_type`;
- `options` разрешены только для `select` и `multiselect`;
- `default` trim-ится, пустая строка становится `None`;
- PostgreSQL default канонизируется перед diff-сравнением;
- изменение типа существующего поля запрещено в MVP;
- `FieldKind.SYSTEM` не patch-ится как обычное runtime field и не показывается в config API responses.

Field kinds:

| Kind       | Поведение                                                                                                                |
|------------|--------------------------------------------------------------------------------------------------------------------------|
| `system`   | Системное поле, например `id`, `created_at`, `updated_at`. Хранится в metadata и descriptors, скрыто в config responses. |
| `standard` | Seed-defined поле. Видимо в config responses, не удаляется через config API.                                             |
| `custom`   | Пользовательское поле. Может создаваться и hard-delete-иться через config API.                                           |

### Indexes

`IndexSeed` содержит `name`, `fields`, `is_unique`.

Rules:

- имя индекса валидируется как PostgreSQL identifier;
- имена индексов должны быть глобально уникальны в tenant schema;
- поля индекса должны существовать в object;
- duplicate fields внутри одного index запрещены;
- relation planning может добавить generated indexes, если нужного индекса еще нет.

### PostgreSQL identifier rules

Внешние identifiers валидируются `SchemaNamingStrategy.validate_identifier`.

Rules:

- значение обязательно и trim-ится;
- максимальная длина - 63 символа;
- формат - `^[a-z][a-z0-9_]*$`;
- generated identifiers при overflow получают deterministic hash suffix.

Generated names:

| Артефакт                | Pattern                                               |
|-------------------------|-------------------------------------------------------|
| Primary key             | `pk_{table_name}`                                     |
| FK constraint           | `fk_{source_table}_{source_column}_{target_table}`    |
| FK index                | `idx_{table}_{column}`                                |
| One-to-one unique index | `uq_{table}_{column}`                                 |
| M2M unique pair index   | `uq_{relation_table}_{source_column}_{target_column}` |

### Defaults canonicalization

`PostgresFieldCanonicalizer` приводит seed defaults и PostgreSQL catalog defaults к стабильной строке.

Важные правила:

- `now()` и `current_timestamp` для timestamp становятся `CURRENT_TIMESTAMP`;
- строки SQL-quote-ятся стабильно;
- UUID functions `gen_random_uuid()` и `uuid_generate_v4()` сохраняются как functions;
- date/timestamp literals получают явный cast;
- boolean `1`/`'1'` становится `true`, `0`/`'0'` становится `false`;
- integer/numeric приводятся к canonical numeric string;
- jsonb сериализуется с sorted keys и compact separators.

Unsupported default для типа приводит к `SeedValidationError` при seed load или `UnsupportedSchemaChangeError` при
inspection/diff.

## Relations

Relations являются отдельной metadata-моделью, а не только полями типа `reference`.

`RelationEntity` хранит:

- `name`, `label`, `relation_type`;
- `source_object_id`, `target_object_id`;
- `owning_object_id`, `fk_field_id`;
- `referenced_object_id`, `referenced_field_id`;
- `source_relation_name`, `target_relation_name`;
- `relation_table_name`, `source_join_column_name`, `target_join_column_name`;
- `on_delete`, `is_required`, `is_unique`, `kind`, `settings`.

`source_relation_name` и `target_relation_name` - API names на соответствующих сторонах descriptor-а. Они уникальны
внутри стороны object-а.

### Relation types

| Type           | Physical shape                                                                              | Collection side        |
|----------------|---------------------------------------------------------------------------------------------|------------------------|
| `many_to_one`  | FK column на source/owning object, FK на target/referenced object, обычный FK index         | target side            |
| `one_to_one`   | FK column на source/owning object, FK на target/referenced object, unique index на FK field | нет collection side    |
| `one_to_many`  | FK column на target/owning object, FK на source/referenced object, обычный FK index         | source side            |
| `many_to_many` | отдельная join table с двумя FK, unique pair index и индексами по каждой join column        | обе стороны collection |

### FK-based relations

FK-based types: `many_to_one`, `one_to_one`, `one_to_many`.

Rules:

- `fk_field` обязателен и должен иметь seed type `reference`;
- `referenced_field` обязателен, default - `id`;
- referenced field должен быть `id` с `is_nullable=False` или иметь unique index;
- `many_to_one` и `one_to_one`: owning object должен быть source, referenced object - target;
- `one_to_many`: owning object должен быть target, referenced object - source;
- `ObjectKind.VIEW` нельзя использовать как physical owning/referenced side;
- `one_to_one` добавляет/требует unique index на FK field;
- `many_to_one` и `one_to_many` добавляют/требуют обычный FK index;
- `on_delete` нормализуется в `restrict`, `cascade`, `set_null`, `no_action`.

Default API names:

- `many_to_one` / `one_to_one`:
    - source side: target singular;
    - target side: source plural;
- `one_to_many`:
    - source side: target plural;
    - target side: source singular.

### Many-to-many relations

`many_to_many` хранится через отдельную physical join table.

Rules:

- self `many_to_many` запрещен в MVP;
- source и target objects не должны быть `view`;
- `relation_table_name` можно передать явно, иначе default - `{source_plural}_{target_plural}`;
- `source_join_column_name` default - `{source_singular}_id`;
- `target_join_column_name` default - `{target_singular}_id`;
- join column names должны отличаться;
- relation table name не должен конфликтовать с object table name или другой relation table;
- join table получает `id uuid not null default gen_random_uuid()`;
- join table получает `created_at timestamp not null default CURRENT_TIMESTAMP`;
- обе join columns имеют SQL type `uuid`, `not null`;
- создается primary key по `id`;
- создается unique index по pair `(source_join_column, target_join_column)`;
- создаются обычные indexes по каждой join column;
- создаются два FK на source/target object `id`;
- `on_delete` применяется к обоим FK.

Default API names:

- source side: target plural;
- target side: source plural.

### Relation diff preservation

Seed diff не должен автоматически удалять custom relation artifacts, которые уже есть в metadata.

`DiffSchemaUseCase._build_preserved_artifacts` собирает из metadata:

- M2M relation tables;
- M2M unique/FK indexes;
- M2M FK constraints;
- FK-based relation index;
- FK-based FK constraint.

Эти artifacts передаются в `PostgresSchemaPlanService` как `PreservedSchemaArtifacts`, чтобы diff не удалял их как
"лишние" только потому, что они отсутствуют в seed.

Relation metadata reconcile:

- seed relations синхронизируются по стабильному `name`;
- matching relation сохраняет id и `created_at`;
- изменение physical shape existing seed relation запрещено;
- relations, которых нет в seed, сохраняются только если все их referenced objects/fields еще существуют;
- если relation ссылается на удаленный object/field, она не сохраняется при reconcile.

## Create и diff flows

### `CreateSchemaUseCase`

Flow:

1. загрузить и валидировать seed;
2. проверить, что physical schema отсутствует;
3. построить create plan;
4. применить PostgreSQL DDL;
5. записать datasource/object/field/relation metadata.

Create plan порядок:

1. `CreateSchemaOperation`;
2. `CreateTableOperation` для всех object tables и M2M tables;
3. `AddColumnOperation`;
4. `AddPrimaryKeyOperation`;
5. `CreateIndexOperation`;
6. `AddForeignKeyOperation`.

### `DiffSchemaUseCase`

Flow:

1. загрузить и валидировать seed;
2. прочитать metadata snapshot;
3. проинспектировать physical PostgreSQL schema;
4. собрать preserved artifacts из metadata relations;
5. построить diff plan;
6. применить DDL;
7. reconcile metadata из validated spec;
8. вернуть `DiffSchemaResultDTO` со статистикой операций.

Diff result содержит:

- `tenant_id`;
- `schema_name`;
- `seed_path`;
- `total_operations`;
- `destructive_operations`;
- `non_destructive_operations`;
- `has_changes`;
- `has_destructive_changes`.

## Migration/diff rules

`PostgresSchemaPlanService` сравнивает desired physical snapshot с actual PostgreSQL snapshot.

Destructive operations:

- `DropTableOperation`;
- `DropColumnOperation`;
- `DropIndexOperation`;
- `DropForeignKeyOperation`;
- `DropPrimaryKeyOperation`.

Ordering rules:

- сначала удаляются FK, которые могут блокировать изменения;
- затем удаляются indexes;
- затем primary key changes;
- затем лишние columns/tables;
- затем создаются missing tables/columns/PK;
- nullable/default alters идут до создания indexes/FK;
- indexes создаются до FK, чтобы referenced unique constraints существовали до FK creation.

Safe/unsafe rules:

- custom physical tables с `c_` prefix не удаляются seed diff-ом, если их нет в seed;
- tables из `PreservedSchemaArtifacts` не удаляются;
- retained column type mismatch запрещен;
- retained column default changes разрешены через `AlterColumnDefaultOperation`;
- retained column `not null -> nullable` разрешен;
- retained column `nullable -> not null` запрещен;
- добавление required column в существующую table без default запрещено;
- required columns для новой table разрешены;
- retained primary key shape change запрещен, кроме удаления PK при отсутствии desired PK и если table не preserved;
- unsupported PostgreSQL column types при inspection приводят к `UnsupportedSchemaChangeError`;
- backend должен быть PostgreSQL, иначе PostgreSQL adapters поднимают `UnsupportedSchemaBackendError`.

## Config API

Все config routes монтируются под `/api/config` и используют authenticated request context. Tenant id берется из
principal, а не из request body.

Read routes используют `POST` bodies вместо `GET`.

### Object routes

| Method   | Path                         | Request                           | Response                            |
|----------|------------------------------|-----------------------------------|-------------------------------------|
| `POST`   | `/api/config/objects/list`   | none                              | `ListCustomObjectsResponseSchema`   |
| `POST`   | `/api/config/objects/create` | `CreateCustomObjectRequestSchema` | `CustomObjectResponseSchema`, `201` |
| `DELETE` | `/api/config/objects/delete` | body `object_id`                  | empty `204`                         |
| `POST`   | `/api/config/objects/schema` | body `object_id`                  | `CustomObjectResponseSchema`        |

`CreateCustomObjectRequestSchema`:

- `singular_name`;
- `plural_name`;
- `singular_label`;
- `plural_label`;
- `description`;
- `fields`.

Create object rules:

- создается только `ObjectKind.CUSTOM`;
- `singular_name` и `plural_name` автоматически получают `c_` prefix;
- singular/plural names должны быть свободны в tenant metadata;
- physical table создается сразу;
- системные поля создаются автоматически:
    - `id uuid not null default gen_random_uuid()`;
    - `created_at datetime not null default CURRENT_TIMESTAMP`;
    - `updated_at datetime not null default CURRENT_TIMESTAMP`;
- для custom object initial fields разрешены required fields без default, потому что table еще новая;
- создается unique index по `id` через `c_<plural>_id_uq` или hash-shortened fallback.

Delete object rules:

- удалить можно только `ObjectKind.CUSTOM`;
- удаление hard-delete-ит physical table;
- metadata objects пересобираются через reconcile без удаленного object;
- `standard`, `system`, `view` objects не удаляются.

Config response object:

- `id`, timestamps;
- `singular_name`, `plural_name`;
- labels, description;
- `kind`;
- `fields`.

Системные поля в object config responses не возвращаются.

### Field routes

| Method   | Path                                | Request                 | Response                     |
|----------|-------------------------------------|-------------------------|------------------------------|
| `POST`   | `/api/config/objects/fields/create` | `object_id`, `field`    | `CustomObjectResponseSchema` |
| `DELETE` | `/api/config/objects/fields/delete` | `object_id`, `field_id` | `CustomObjectResponseSchema` |

`CustomFieldRequestSchema`:

- `field_name`;
- `type`;
- `label`;
- `description`;
- `is_nullable`;
- `default_value`;
- `options`;
- `settings`.

Create field rules:

- object должен быть `standard` или `custom`;
- `system`/`view` objects не расширяются custom fields;
- добавляется `FieldKind.CUSTOM`;
- physical column создается сразу;
- добавление required field без default в существующий object запрещено как unsafe;
- type должен быть поддержан `FieldTypeCatalog`;
- `options` разрешены только для `select`/`multiselect`;
- duplicate field name внутри object запрещен.

Delete field rules:

- удалить можно только `FieldKind.CUSTOM`;
- physical column удаляется hard-delete-ом;
- metadata field удаляется из object;
- `system` и `standard` fields не удаляются.

### Relation routes

| Method   | Path                                   | Request                       | Response                        |
|----------|----------------------------------------|-------------------------------|---------------------------------|
| `POST`   | `/api/config/objects/relations/create` | `CreateRelationRequestSchema` | `RelationResponseSchema`, `201` |
| `DELETE` | `/api/config/objects/relations/delete` | body `relation_id`            | empty `204`                     |
| `POST`   | `/api/config/objects/relations/list`   | body `object_id`              | `ListRelationsResponseSchema`   |
| `POST`   | `/api/config/objects/relations/schema` | body `object_id`              | `ListRelationsResponseSchema`   |

`RelationRequestSchema`:

- `name`;
- `relation_type`;
- `source_object_id`;
- `target_object_id`;
- optional `label`;
- optional `owning_object_id`;
- optional `fk_field_name`;
- optional `referenced_object_id`;
- `referenced_field_name`, default `id`;
- optional `source_relation_name`;
- optional `target_relation_name`;
- optional `relation_table_name`;
- optional `source_join_column_name`;
- optional `target_join_column_name`;
- `on_delete`, default `restrict`;
- `is_required`, default `false`;
- `settings`.

Create relation rules:

- relation name - PostgreSQL identifier and unique within tenant;
- source/target objects must exist and belong to tenant;
- source/target/owning/referenced objects must be `standard` or `custom`;
- `system`/`view` objects нельзя использовать для custom relation;
- created relation всегда получает `kind="custom"`;
- API names должны быть уникальны на соответствующей стороне object-а;
- `on_delete` поддерживает `restrict`, `cascade`, `set_null`, `no_action` и варианты с пробелом.

Config-created FK relation rules:

- `referenced_field_name` в MVP может ссылаться только на primary `id`;
- если FK field отсутствует, он создается как `custom` field типа `reference`;
- если создается required FK field на non-empty table, операция запрещается;
- если FK field уже существует, он должен быть `reference`, не `system`, и не должен быть bound к другой relation;
- создается FK index или unique index для `one_to_one`;
- создается FK constraint;
- если был создан новый FK field, object metadata сохраняется вместе с новым field.

Config-created M2M rules:

- self M2M запрещен;
- relation table name не должен совпадать с object table и существующей relation table;
- создаются join table, columns, PK, unique pair index, two FK indexes, two FK constraints;
- duplicate pair предотвращается physical unique index-ом.

Delete relation rules:

- удалить можно только `kind="custom"`;
- system/standard seed relations не удаляются через config API;
- для M2M relation table должна быть пустой, иначе удаление запрещено;
- для FK-based relation FK column должна не иметь non-null values, иначе удаление запрещено;
- удаляются FK constraint и index;
- если FK field был `custom`, удаляется physical column и field metadata;
- после physical DDL удаляется relation metadata.

### Error mapping

HTTP controllers используют стандартную FastAPI error body с `detail`.

Основные статусы:

- `401` - нет authenticated principal или tenant id;
- `404` - object/field/relation не найден;
- `409` - physical schema/backend/metadata inconsistency/runtime descriptor conflicts;
- `422` - domain/schema validation errors и invalid operation errors.

## Runtime resolver

`SchemaRegistryRuntimeObjectResolver` строит immutable runtime descriptors из metadata.

Public methods:

- `resolve(tenant_id, object_name)` - ищет object по singular name;
- `resolve_by_id(tenant_id, object_id)` - ищет object по id.

Resolver rules:

- object tenant id должен совпадать с requested tenant;
- object data_source id должен совпадать с datasource tenant;
- descriptor обязан иметь field `id`;
- если object не найден или tenant mismatch - `RuntimeObjectNotFoundError`;
- если metadata datasource mismatch - `SchemaRegistryMetadataInconsistentError`;
- если нет `id` field - `RuntimeObjectDescriptorError`;
- если `relation_service` не передан, `relations=()`.

`RuntimeObjectDescriptor`:

- `schema_name`;
- `object_name` - singular name;
- `table_name` - plural/physical table name;
- `pk` - всегда `id`;
- `title_field` - сейчас `id`;
- `fields`;
- `relations`;
- `kind`.

`RuntimeFieldDescriptor`:

- `name`;
- `type_code`;
- `is_nullable`;
- `default_value`;
- `options`;
- `settings`;
- `kind`.

`RuntimeRelationDescriptor`:

- relation identity/name/type;
- source/target objects as plural names;
- source/target API names;
- owning/referenced object names;
- FK field and referenced field;
- M2M table/join columns;
- `on_delete`;
- `is_required`;
- `is_collection`;
- `is_virtual`;
- `is_unique`;
- `kind`;
- `settings`.

`is_collection`:

- `many_to_many` - `true` на обеих сторонах;
- `one_to_many` - `true` на source side;
- `many_to_one` - `true` на target side;
- `one_to_one` - `false` на обеих сторонах.

`is_virtual`:

- `many_to_many` - всегда `true`;
- FK-based relation - `true`, если текущий object не является `owning_object`;
- FK-based relation - `false`, если текущий object физически хранит FK column.

## Management CLI и bootstrap

Management command:

```bash
dnk-manage schema-registry diff <tenant_id> [--seed-path ...]
```

Default `seed_path` берется из runtime schema config:

```text
src.modules.schema_registry.seed.schema_seed
```

CLI печатает summary `DiffSchemaResultDTO` и возвращает non-zero exit code для ожидаемых `SchemaRegistryError`.

Tenant bootstrap:

- `tenancy` не импортирует application layer `schema_registry` напрямую;
- интеграция идет через tenancy-owned `TenantSchemaBootstrapPort`;
- adapter в `schema_registry` транслирует tenant onboarding context в `CreateSchemaCommand`.

Nested bootstrap и diff должны работать в одной активной `UoW / AsyncSession`.

## PostgreSQL adapters

`PostgresTenantSchemaInspector` читает фактическую схему через `information_schema` и `pg_catalog`:

- schema exists;
- base tables;
- columns и canonical SQL type/default;
- primary keys;
- non-primary indexes;
- foreign keys и `on_delete`;
- table has rows;
- column has non-null values.

`PostgresTenantSchemaExecutor` исполняет `MigrationPlan` последовательно:

- create/drop schema/table/column;
- alter default/nullability;
- add/drop primary key;
- create/drop index;
- add/drop foreign key.

Оба adapters требуют PostgreSQL dialect.

## Правила совместимости и ограничения

- PostgreSQL-only backend для physical schema operations.
- Rename objects/fields/relations не infer-ится эвристически: смена natural key считается remove/add.
- Изменение field type существующего поля запрещено.
- Изменение physical shape существующей seed relation через diff запрещено.
- `settings` хранятся как свободный metadata dict, но physical DDL зависит только от явных полей spec/relation.
- `one_to_many` и `many_to_many` поддержаны в seed planning, metadata и runtime descriptors.
- Config-created relations поддерживают FK-based и M2M сценарии, но referenced field для FK relation ограничен `id` в
  MVP.
- `custom_object` module не проксирует schema/DDL операции: metadata и DDL остаются в `/api/config/...`.

## Тестовое покрытие

Основные тестовые группы:

- `test_schema_registry_seed_service.py` - seed validation/normalization;
- `test_schema_registry_planning.py` - create/diff planning, FK/M2M/index/default/nullability rules;
- `test_schema_registry_metadata_read_service.py` - metadata consistency;
- `test_schema_registry_metadata_write_service.py` - metadata create/reconcile;
- `test_schema_registry_runtime_resolver.py` - runtime descriptors и relation descriptors;
- `test_schema_registry_repositories.py` - persistence repositories, включая relations;
- `test_schema_config_http_router.py` - config routes registration;
- `test_schema_config_repository.py` - config-time object/field behavior;
- `test_schema_registry_postgres_executor.py` - PostgreSQL DDL rendering/execution;
- `test_management_schema_registry_command.py` - CLI behavior;
- `test_inventory_schema_seed.py` - default seed objects, indexes, FKs, M2M.

## Связанные документы

- [Management CLI](../interfaces/management-cli.md)
- [Runtime schema](../data/runtime-schema.md)
- [Persistence and Unit of Work](../architecture/persistence-and-uow.md)
- [Test map](../quality/test-map.md)

## Source of truth

- `src/modules/schema_registry/application/service/schema_seed_service.py`
- `src/modules/schema_registry/application/use_case/create_schema_use_case.py`
- `src/modules/schema_registry/application/use_case/diff_schema_use_case.py`
- `src/modules/schema_registry/application/migration/postgres_schema_plan_service.py`
- `src/modules/schema_registry/infrastructure/config/schema_config_repository.py`
- `src/modules/schema_registry/runtime/resolver.py`
- `src/modules/schema_registry/domain/relation/entity.py`
- `src/modules/schema_registry/seed/schema_seed.py`
