# Runtime Schema: Техническая документация

## 1. Назначение модуля

`runtime_schema` — это control-plane модуль, который управляет метаданными runtime-объектов и полей, а также синхронизирует физическую схему БД под эти метаданные.

Что модуль делает:

- хранит и валидирует `object_metadata` и `field_metadata`;
- читает declarative-манифест системных моделей (`system_models.yaml`);
- компилирует manifest -> domain metadata;
- компилирует metadata -> expected SQL layout;
- сравнивает expected layout с фактической схемой БД;
- строит DDL-план и применяет его;
- ведет `schema_version` и `schema_migration_journal`;
- предоставляет CRUD для runtime-объектов и runtime-полей.

Что модуль не делает:

- не реализует CRUD бизнес-записей (data-plane);
- не содержит предметную логику CRM/Identity и т.д.

---

## 2. Структура модуля

Пакет: `src/modules/runtime_schema`

- `domain`: инварианты, сущности, value objects, ошибки.
- `application`: DTO и use-case фасады.
- `infrastructure`: реализации протоколов (SQLAlchemy, YAML reader, DDL pipeline).
- `system_models/system_models.yaml`: системный реестр объектов/полей.

Публичный экспорт пакета (`src/modules/runtime_schema/__init__.py`) отдает основные domain-типы:

- `DataSource`, `DataSource*VO`
- `ObjectMetadataEntity`, `Object*VO`
- `FieldMetadataEntity`, `Field*VO`

---

## 3. Сквозные сценарии

## 3.1 Bootstrap/Sync системной схемы

Вход:

- `BootstrapTenantSystemSchemaCommandDTO`
- `SyncTenantSystemSchemaCommandDTO`

Поток (`DdlOrchestratorService.sync_tenant_system_schema`):

1. Нормализация `tenant_id`, `data_source_id`, `schema`.
2. Захват schema-lock (`SchemaLockServiceProtocol`).
3. Чтение и валидация manifest (`YamlSystemModelRegistryReader`).
4. Компиляция manifest в domain metadata (`MetadataCompiler`).
5. Компиляция metadata в expected snapshot (`FieldLayoutCompiler`).
6. Интроспекция текущей схемы (`SqlAlchemySchemaIntrospector`).
7. Diff (`DdlDiffEngine`), план (`DdlPlanBuilder`), выполнение (`SqlAlchemyDdlExecutor`).
8. Upsert metadata в control-plane таблицы.
9. Обновление `schema_version`.
10. Запись migration journal.
11. Возврат `SyncTenantSystemSchemaResultDTO` с агрегированной статистикой операций.

Идемпотентность:

- повторный `sync` при совпадающем состоянии дает `applied_operations = 0`.

## 3.2 CRUD object/field definitions

### Object

- `create_object_definition`:
  - проверяет уникальность `name_singular` в рамках `(tenant_id, data_source_id)`;
  - создает `ObjectMetadataEntity`;
  - сохраняет metadata;
  - опционально вызывает layout sync при наличии `schema`.

- `update_object_definition`:
  - проверяет tenant ownership;
  - rename требует `allow_ddl_rename=True`;
  - при rename таблицы может выполнить отдельную DDL rename-операцию (если builder поддерживает `build_rename_table_operation`);
  - затем делает sync layout.

- `delete_object_definition`:
  - `allow_destructive=False`: soft delete (`is_active=False`);
  - `allow_destructive=True`: физическое удаление object + его fields и sync с destructive diff.

### Field

- `create_field_definition`:
  - проверяет существование объекта и tenant ownership;
  - проверяет уникальность field name внутри объекта;
  - парсит options/settings/default через deserialize;
  - валидирует relation target;
  - создает `FieldMetadataEntity`;
  - сохраняет и опционально sync.

- `update_field_definition`:
  - частичное обновление флагов/метаданных;
  - options/settings/default валидируются и применяются через setter-методы entity (с rollback при ошибке);
  - relation target валидируется;
  - доп. консистентность полей проверяется `_ensure_field_mutation_consistency`;
  - сохраняет и опционально sync.

- `delete_field_definition`:
  - `allow_destructive=False`: soft delete (`is_active=False`);
  - `allow_destructive=True`: физическое удаление и sync с destructive diff.

---

## 4. Доменная модель

## 4.1 Value Objects

### `domain/field/value_object.py`

- `FieldIdVO(EntityIdVO)` — UUID-идентификатор поля.
- `FieldTypeVO(StrEnum)` — типы runtime-полей:
  - `uuid`, `string`, `text`, `integer`, `boolean`, `date_time`, `json`,
  - `actor`, `address`, `array`, `currency`, `emails`, `full_name`, `links`, `phones`,
  - `select`, `multi_select`, `relation`.
- `FieldName`:
  - нормализует в `snake_case lower`;
  - валидирует regex `^[a-z][a-z0-9_]*$`;
  - бросает `FieldNameRequiredError`/`FieldNameInvalidFormatError`.

### `domain/object/value_object.py`

- `ObjectIdVO(EntityIdVO)` — UUID-идентификатор объекта.
- `ObjectNameVO`:
  - `name_singular/name_plural`, snake_case, lower;
  - фабрика `from_singular(...)` автогенерирует plural (`<singular>s`) если не задан.
- `ObjectLabelVO`:
  - хранит display labels;
  - `from_name(...)` humanize из snake_case в title-case.

### `domain/source/value_object.py`

- `DataSourceIdVO(EntityIdVO)`.
- `DataSourceTypeVO`:
  - поддерживаемые типы: `postgresql`, `mysql`, `sqlite`;
  - `from_value(...)` с нормализацией и проверкой.
- `DataSourceSchemaVO`:
  - lower-case schema name;
  - regex `^[a-z_][a-z0-9_]*$`, max 63.
- `DataSourceDsnVO`:
  - валидирует DSN через `urlparse`;
  - для `sqlite` требует path, для остальных — netloc.

## 4.2 Entity: `DataSource`

Файл: `domain/source/entity.py`

- Поля:
  - `tenant_id`, `type`, `schema`, `is_system`, `is_remote`, `dsn`.
- Инварианты:
  - `updated_at >= created_at`;
  - `is_remote=True` требует `dsn`.
- Методы:
  - `create(...)` — фабрика с нормализацией входных VO;
  - `set_dsn(...)` — обновляет DSN + `touch()`.

## 4.3 Entity: `ObjectMetadataEntity`

Файл: `domain/object/entity.py`

- Назначение: metadata runtime-объекта.
- Ключевые инварианты:
  - ровно один из `is_system/is_custom` должен быть true;
  - `updated_at >= created_at`;
  - `description/icon/shortcut` нормализуются и могут стать `None`.
- Методы:
  - `create(...)`;
  - `rename(...)` (меняет name+label и touch);
  - `activate()/deactivate()`;
  - `touch(...)`.

## 4.4 Entity: `FieldMetadataEntity`

Файл: `domain/field/entity.py`

- Назначение: metadata runtime-поля + его storage constraints.
- Встроенные contracts:
  - `_ALLOWED_SETTINGS_BY_TYPE` — какие settings допустимы для каждого `FieldTypeVO`;
  - `_EXPECTED_DEFAULT_BY_TYPE` — ожидаемый тип default value.
- Базовые инварианты:
  - `label` обязателен;
  - ровно один из `is_system/is_custom`;
  - `is_unique => is_index`;
  - relation-контракт:
    - `field_type=relation` требует `relation_target_object_id`;
    - другие типы не могут иметь relation target.
  - options-контракт:
    - `select` требует `SelectFieldOptions`;
    - `multi_select` требует `MultiSelectFieldOptions`;
    - другим типам options запрещены.
  - settings/default контракты проверяются по типу поля.

- Методы мутаций:
  - `set_options`, `set_settings`, `set_default_value`, `set_relation_target`;
  - при ошибке валидации состояние откатывается до предыдущего;
  - успешная мутация делает `touch()`.

- Дополнительная валидация default по типам:
  - `address`: обязательность частей адреса по settings;
  - `array`: `max_items`, duplicates, `item_type`;
  - `currency`: allowed currencies, scale;
  - `date_time`: timezone-aware/UTC rules;
  - `emails/links/phones`: лимиты и duplicates;
  - `full_name`: required name parts;
  - `select/multi_select`: code должен существовать в options;
  - `relation`: default target должен совпадать с relation target.

## 4.5 Field configuration model

Файл: `domain/field/configuration.py`

Содержит:

- опции:
  - `FieldOption`
  - `SelectFieldOptions`
  - `MultiSelectFieldOptions`
- settings:
  - `StringFieldSettings`, `IntegerFieldSettings`, `DateTimeFieldSettings`, `JsonFieldSettings`
  - `RelationFieldSettings`, `ActorFieldSettings`, `AddressFieldSettings`, `ArrayFieldSettings`
  - `CurrencyFieldSettings`, `EmailsFieldSettings`, `FullNameFieldSettings`, `LinksFieldSettings`, `PhonesFieldSettings`
- default values:
  - `StringDefaultValue`, `IntegerDefaultValue`, `BooleanDefaultValue`, `UuidDefaultValue`, `DateTimeDefaultValue`, `JsonDefaultValue`
  - `SelectDefaultValue`, `MultiSelectDefaultValue`, `RelationDefaultValue`
  - `ActorDefaultValue`, `AddressDefaultValue`, `ArrayDefaultValue`, `CurrencyDefaultValue`
  - `EmailsDefaultValue`, `FullNameDefaultValue`, `LinksDefaultValue`, `PhonesDefaultValue`
- type aliases:
  - `FieldOptions`, `FieldSettings`, `FieldDefaultValue`
- служебные нормализаторы:
  - email/phone/url checks, normalization, duplicate-code checks.

## 4.6 Domain errors

Файл: `domain/errors.py`

33 специализированных исключения-наследника `ValidationError`, сгруппированные по группам:

- field name/label;
- field flags/options/settings/default/relation/time;
- object name/label/flags/time;
- data source type/schema/dsn/time.

---

## 5. Application слой

## 5.1 DTO

### Objects

Файл: `application/object_definition/dto.py`

- `CreateObjectCommandDTO`
- `UpdateObjectCommandDTO`
- `DeleteObjectCommandDTO`
- `ObjectDefinitionDTO`

### Fields

Файл: `application/field_definition/dto.py`

- `CreateFieldCommandDTO`
- `UpdateFieldCommandDTO`
- `DeleteFieldCommandDTO`
- `FieldDefinitionDTO`

### Bootstrap/Sync

- `application/bootstrap_tenant_system_schema/dto.py`:
  - `BootstrapTenantSystemSchemaCommandDTO`
- `application/sync_tenant_system_schema/dto.py`:
  - `SyncTenantSystemSchemaCommandDTO`
  - `SyncTenantSystemSchemaResultDTO`

## 5.2 Use Cases

- `BootstrapTenantSystemSchemaUseCase`
- `SyncTenantSystemSchemaUseCase`
- `Create/Update/DeleteObjectDefinitionUseCase`
- `Create/Update/DeleteFieldDefinitionUseCase`

Все use cases — thin facade: делегируют вызов в `DdlOrchestratorServiceProtocol`.

## 5.3 Application port

Файл: `application/ports/orchestrator.py`

- `DdlOrchestratorServiceProtocol` задает контракт:
  - bootstrap/sync;
  - object CRUD;
  - field CRUD.

---

## 6. Infrastructure слой

## 6.1 Контракты

Файл: `infrastructure/contracts.py`

Ключевые протоколы:

- `SystemModelRegistryReaderProtocol`
- `MetadataCompilerProtocol`
- `FieldLayoutCompilerProtocol`
- `SchemaIntrospectorProtocol`
- `DdlDiffEngineProtocol`
- `DdlPlanBuilderProtocol`
- `DdlExecutorProtocol`
- `SchemaVersionRepositoryProtocol`
- `SchemaMigrationJournalRepositoryProtocol`
- `SchemaLockServiceProtocol`
- `ObjectMetadataRepositoryProtocol`
- `FieldMetadataRepositoryProtocol`

DTO уровня инфраструктуры:

- `SchemaVersionEntry`.

## 6.2 DDL/metadata модели

Файл: `infrastructure/ddl_models.py`

- manifest-модели:
  - `SystemFieldDefinition`
  - `SystemObjectDefinition`
  - `LoadedSystemManifest`
- compiled metadata:
  - `MetadataBundle`
- layout/snapshot:
  - `ColumnSpec`, `IndexSpec`, `TableSpec`, `SchemaSnapshot`
- diff:
  - `TableToCreate`, `ColumnToAdd`, `IndexToCreate`, `TableToDrop`, `ColumnToDrop`, `DdlDiff`
- plan:
  - `DdlOperationKind`, `DdlOperation`, `DdlPlan`
- journal/report:
  - `MigrationJournalEntry` (`applied()`/`failed()`)
  - `ExecutionReport`.

## 6.3 System manifest reader

Файл: `infrastructure/system_manifest_reader.py`

`YamlSystemModelRegistryReader`:

- читает YAML;
- валидирует обязательные части (`version`, `objects`, `name`, `label`, `fields`);
- проверяет дубль object keys;
- проверяет дубли field names внутри объекта (case-insensitive);
- для `default_value` поддерживает shorthand-строку: `"value"` конвертируется в `{"value": "value"}`;
- принимает alias `default_values` (как fallback к `default_value`);
- вычисляет `manifest_hash = sha256(raw_text)`.

## 6.4 Metadata compiler

Файл: `infrastructure/metadata_compiler.py`

`MetadataCompiler`:

- создает `ObjectMetadataEntity` для каждого объекта из manifest;
- создает `FieldMetadataEntity` для каждого поля;
- преобразует options/settings/default (через deserialize helpers);
- поддерживает deferred связывание `relation_target_field` через `_PendingRelationFieldTarget`;
- валидирует relation references и целостность target field.

## 6.5 Field serialization

Файл: `infrastructure/field_serialization.py`

- `serialize_field_options/settings/default`:
  - преобразуют dataclass/enum/UUID/datetime/tuple/list/dict в JSON-friendly payload.
- `deserialize_field_options/settings/default`:
  - создают строго типизированные domain-конфигурации по `FieldTypeVO`.

Примечания:

- для JSON default есть backward compatibility: payload может быть как `{"value": ...}`, так и "плоский" dict.
- для `date_time` поддерживается `{"value": "now"}` (резолвится в текущий UTC datetime).
- unsupported комбинации options/settings -> `ValueError`.

## 6.6 Field layout compiler

Файл: `infrastructure/field_layout_compiler.py`

`FieldLayoutCompiler.compile_layout(...)`:

- строит `SchemaSnapshot` из активных object+field metadata;
- гарантирует системную колонку `id` (если она не описана полем, добавляется как PK);
- строит индексы на основании `is_index`/`is_unique`.

Маппинг field type -> storage:

- `uuid` -> `uuid`
- `string/text` -> `varchar(...)` или `text`
- `integer` -> `bigint`
- `boolean` -> `boolean`
- `date_time` -> `timestamp_tz`
- `json` -> `json`
- `array/multi_select/emails/links/phones` -> `json`
- `select` -> `varchar(128)`
- `actor` -> `uuid`
- `address` -> 5 колонок (`*_country`, `*_region`, ...)
- `full_name` -> 3 колонки (`*_last_name`, ...)
- `currency` -> 2 колонки (`*_amount_minor`, `*_currency`)
- `relation`:
  - `max_links == 1` -> `uuid` колонка;
  - иначе virtual-only (физическая колонка не создается).

## 6.7 Diff engine

Файл: `infrastructure/ddl_diff_engine.py`

`DdlDiffEngine.diff(...)`:

- находит таблицы для создания;
- находит недостающие колонки и индексы;
- при `allow_destructive=True`:
  - находит лишние колонки (кроме `id`) для drop;
  - находит лишние таблицы для drop.

Важно:

- engine не делает alter типа/nullable;
- engine не удаляет индексы.

## 6.8 Plan builder

Файл: `infrastructure/ddl_plan_builder.py`

`DdlPlanBuilder`:

- строит SQL-операции из diff:
  - create table
  - add column
  - create index
  - drop column (кроме sqlite)
  - drop table
- поддерживает `build_rename_table_operation(...)` для rename object table.

Dialect-особенности:

- PostgreSQL:
  - qualified table `"schema"."table"`
  - `uuid -> UUID`, `timestamp_tz -> TIMESTAMP WITH TIME ZONE`, `json -> JSONB`.
- SQLite/non-postgres:
  - physical table name: `schema__table`
  - `uuid -> TEXT`, `bigint -> INTEGER`, `boolean -> INTEGER`, `timestamp_tz -> TEXT`.

## 6.9 DDL executor

Файл: `infrastructure/ddl_executor.py`

`SqlAlchemyDdlExecutor`:

- последовательно выполняет SQL операции в текущей `AsyncSession`;
- по каждой операции пишет `MigrationJournalEntry` в памяти отчета;
- при ошибке бросает `DdlExecutionError` с частично накопленным journal.

## 6.10 Schema introspector

Файл: `infrastructure/schema_introspector.py`

`SqlAlchemySchemaIntrospector`:

- через SQLAlchemy `inspect` собирает таблицы, колонки, PK и индексы;
- для non-postgres учитывает только таблицы с префиксом `schema__`;
- нормализует DB-специфичные типы в внутренние `sql_type`.

## 6.11 Schema lock

Файл: `infrastructure/schema_lock.py`

`SqlAlchemySchemaLockService`:

- PostgreSQL: транзакционный advisory lock `pg_advisory_xact_lock(lock_key)`;
- другие dialects: no-op;
- lock key вычисляется как signed 64-bit из `sha1(tenant_id:schema)`.

## 6.12 Repositories

Файл: `infrastructure/repositories.py`

- `SqlAlchemyObjectMetadataRepository`
- `SqlAlchemyFieldMetadataRepository`
- `SqlAlchemySchemaVersionRepository`
- `SqlAlchemySchemaMigrationJournalRepository`

Особенности:

- field repository сериализует/десериализует options/settings/default;
- `list_by_tenant` для полей возвращает все поля tenant, фильтрация по data source делается уровнем orchestrator;
- `schema_version` upsert keyed by `(tenant_id, schema)`.

## 6.13 SQLAlchemy persistence models

Файл: `infrastructure/persistence/models.py`

Таблицы control-plane:

- `ObjectMetadataModel` (`object_metadata`)
- `FieldMetadataModel` (`field_metadata`)
- `FieldStorageMetadataModel` (`field_storage_metadata`)
- `FieldOptionMetadataModel` (`field_option_metadata`)
- `SchemaVersionModel` (`schema_version`)
- `SchemaMigrationJournalModel` (`schema_migration_journal`)

## 6.14 Orchestrator service

Файл: `infrastructure/ddl_orchestrator_service.py`

`DdlOrchestratorService` — центральный сервис модуля.

Ключевые публичные методы:

- `bootstrap_tenant_system_schema`
- `sync_tenant_system_schema`
- `create_object_definition`
- `update_object_definition`
- `delete_object_definition`
- `create_field_definition`
- `update_field_definition`
- `delete_field_definition`

Внутренние helper-методы:

- `_apply_bundle_to_schema`
- `_sync_tenant_layout`
- `_upsert_system_metadata`
- `_validate_relation_target`
- `_execute_ddl_plan`
- `_sync_result`, `_object_to_dto`, `_field_to_dto`

Особенности:

- падение DDL преобразуется в `ValidationError("ddl execution failed: ...")`;
- в случае DDL ошибки failed journal пишется в репозиторий;
- при sync системных моделей IDs объектов/полей ремапятся на уже существующие записи, чтобы не терять ссылочную целостность relation targets.

## 6.15 Factory

Файл: `infrastructure/factory.py`

- `default_system_manifest_path()` -> `system_models/system_models.yaml`;
- `build_ddl_orchestrator(session, manifest_path=None)` собирает production wiring.

---

## 7. Системный manifest (`system_models.yaml`)

Файл: `src/modules/runtime_schema/system_models/system_models.yaml`

Текущие метаданные:

- `version: "2026.03.11"`
- `module: "crm"`
- объектов: `7`

Объекты и число полей:

- `crm_lead`: 6
- `crm_contact`: 3
- `crm_company`: 3
- `crm_deal`: 3
- `crm_contact_point`: 10
- `crm_contact_point_type`: 7
- `crm_product_row`: 20

Распределение типов полей:

- `string`: 11
- `uuid`: 10
- `relation`: 5
- `boolean`: 7
- `integer`: 6
- `currency`: 6
- `select`: 5
- `full_name`: 2

---

## 8. Интеграция с другими модулями

### Tenancy onboarding

- `src/modules/tenancy/application/admin_onboarding/ports/runtime_schema.py`:
  - `TenantRuntimeSchemaBootstrapperProtocol`
- `src/modules/tenancy/infrastructure/runtime_schema_bootstrapper.py`:
  - `RuntimeSchemaBootstrapperAdapter`
  - адаптирует tenancy flow к `BootstrapTenantSystemSchemaUseCase`.

---

## 9. Карта файлов и классов

Ниже — фактическая карта по файлам модуля (включая utility-`__init__`):

### Корень пакета

- `src/modules/runtime_schema/__init__.py`
  - экспорт основных domain-типов.

### `application`

- `src/modules/runtime_schema/application/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/services/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/ports/__init__.py`
  - экспорт `DdlOrchestratorServiceProtocol`.
- `src/modules/runtime_schema/application/ports/orchestrator.py`
  - `DdlOrchestratorServiceProtocol`.
- `src/modules/runtime_schema/application/bootstrap_tenant_system_schema/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/bootstrap_tenant_system_schema/dto.py`
  - `BootstrapTenantSystemSchemaCommandDTO`.
- `src/modules/runtime_schema/application/bootstrap_tenant_system_schema/use_case.py`
  - `BootstrapTenantSystemSchemaUseCase`.
- `src/modules/runtime_schema/application/sync_tenant_system_schema/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/sync_tenant_system_schema/dto.py`
  - `SyncTenantSystemSchemaCommandDTO`
  - `SyncTenantSystemSchemaResultDTO`.
- `src/modules/runtime_schema/application/sync_tenant_system_schema/use_case.py`
  - `SyncTenantSystemSchemaUseCase`.
- `src/modules/runtime_schema/application/object_definition/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/object_definition/dto.py`
  - `CreateObjectCommandDTO`
  - `UpdateObjectCommandDTO`
  - `DeleteObjectCommandDTO`
  - `ObjectDefinitionDTO`.
- `src/modules/runtime_schema/application/object_definition/use_cases.py`
  - `CreateObjectDefinitionUseCase`
  - `UpdateObjectDefinitionUseCase`
  - `DeleteObjectDefinitionUseCase`.
- `src/modules/runtime_schema/application/field_definition/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/application/field_definition/dto.py`
  - `CreateFieldCommandDTO`
  - `UpdateFieldCommandDTO`
  - `DeleteFieldCommandDTO`
  - `FieldDefinitionDTO`.
- `src/modules/runtime_schema/application/field_definition/use_cases.py`
  - `CreateFieldDefinitionUseCase`
  - `UpdateFieldDefinitionUseCase`
  - `DeleteFieldDefinitionUseCase`.

### `domain`

- `src/modules/runtime_schema/domain/__init__.py`
  - агрегированный экспорт domain-типов.
- `src/modules/runtime_schema/domain/errors.py`
  - 33 специализированных `ValidationError`.
- `src/modules/runtime_schema/domain/source/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/domain/source/value_object.py`
  - `DataSourceIdVO`
  - `DataSourceTypeVO`
  - `DataSourceSchemaVO`
  - `DataSourceDsnVO`.
- `src/modules/runtime_schema/domain/source/entity.py`
  - `DataSource`.
- `src/modules/runtime_schema/domain/object/__init__.py`
  - `__all__` placeholder.
- `src/modules/runtime_schema/domain/object/value_object.py`
  - `ObjectIdVO`
  - `ObjectNameVO`
  - `ObjectLabelVO`.
- `src/modules/runtime_schema/domain/object/entity.py`
  - `ObjectMetadataEntity`.
- `src/modules/runtime_schema/domain/field/__init__.py`
  - экспорт field configuration/entity/value objects.
- `src/modules/runtime_schema/domain/field/value_object.py`
  - `FieldIdVO`
  - `FieldTypeVO`
  - `FieldName`.
- `src/modules/runtime_schema/domain/field/configuration.py`
  - `FieldOption`, `SelectFieldOptions`, `MultiSelectFieldOptions`
  - `ArrayItemTypeVO`
  - 13 settings dataclass
  - 17 default-value dataclass
  - `FieldOptions`, `FieldSettings`, `FieldDefaultValue` aliases.
- `src/modules/runtime_schema/domain/field/entity.py`
  - `FieldMetadataEntity`.

### `infrastructure`

- `src/modules/runtime_schema/infrastructure/__init__.py`
  - экспорт `DdlOrchestratorService`, factory helpers.
- `src/modules/runtime_schema/infrastructure/contracts.py`
  - infra protocols + `SchemaVersionEntry`.
- `src/modules/runtime_schema/infrastructure/ddl_models.py`
  - manifest/layout/diff/plan/report dataclasses.
- `src/modules/runtime_schema/infrastructure/system_manifest_reader.py`
  - `YamlSystemModelRegistryReader`.
- `src/modules/runtime_schema/infrastructure/metadata_compiler.py`
  - `_PendingRelationFieldTarget`
  - `MetadataCompiler`.
- `src/modules/runtime_schema/infrastructure/field_serialization.py`
  - serialize/deserialize helpers.
- `src/modules/runtime_schema/infrastructure/field_layout_compiler.py`
  - `_CompiledColumns`
  - `FieldLayoutCompiler`.
- `src/modules/runtime_schema/infrastructure/ddl_diff_engine.py`
  - `DdlDiffEngine`.
- `src/modules/runtime_schema/infrastructure/ddl_plan_builder.py`
  - `DdlPlanBuilder`.
- `src/modules/runtime_schema/infrastructure/ddl_executor.py`
  - `SqlAlchemyDdlExecutor`
  - `DdlExecutionError`.
- `src/modules/runtime_schema/infrastructure/schema_introspector.py`
  - `SqlAlchemySchemaIntrospector`.
- `src/modules/runtime_schema/infrastructure/schema_lock.py`
  - `SqlAlchemySchemaLockService`.
- `src/modules/runtime_schema/infrastructure/repositories.py`
  - `SqlAlchemyObjectMetadataRepository`
  - `SqlAlchemyFieldMetadataRepository`
  - `SqlAlchemySchemaVersionRepository`
  - `SqlAlchemySchemaMigrationJournalRepository`
  - `utc_now()`.
- `src/modules/runtime_schema/infrastructure/persistence/__init__.py`
  - экспорт SQLAlchemy моделей.
- `src/modules/runtime_schema/infrastructure/persistence/models.py`
  - `ObjectMetadataModel`
  - `FieldMetadataModel`
  - `FieldStorageMetadataModel`
  - `FieldOptionMetadataModel`
  - `SchemaVersionModel`
  - `SchemaMigrationJournalModel`.
- `src/modules/runtime_schema/infrastructure/ddl_orchestrator_service.py`
  - `DdlOrchestratorService`.
- `src/modules/runtime_schema/infrastructure/factory.py`
  - `default_system_manifest_path`
  - `build_ddl_orchestrator`.

### Manifest

- `src/modules/runtime_schema/system_models/system_models.yaml`
  - declarative реестр системных CRM-объектов и полей.

---

## 10. Подтверждение поведения тестами

Покрытие ключевых блоков:

- domain VO/entities/configuration:
  - `test_runtime_schema_domain_value_objects.py`
  - `test_runtime_schema_domain_entities.py`
  - `test_runtime_schema_domain_field_entity_extended.py`
  - `test_runtime_schema_field_configuration.py`
- application delegation:
  - `test_runtime_schema_application_use_cases.py`
- infrastructure:
  - `test_runtime_schema_infra_manifest_and_compiler.py`
  - `test_runtime_schema_infra_field_serialization.py`
  - `test_runtime_schema_infra_layout_diff_plan.py`
  - `test_runtime_schema_infra_sqlalchemy_components.py`
  - `test_runtime_schema_infra_extended_components.py`
  - `test_runtime_schema_infra_ddl_models.py`
- orchestration e2e flow:
  - `test_runtime_schema_orchestrator_service.py`.

Это подтверждает:

- идемпотентный sync/bootstrap;
- CRUD metadata + soft/hard delete;
- relation target validation;
- DDL journaling при success/failure;
- покрытие dialect-веток sqlite/postgresql в critical местах.
