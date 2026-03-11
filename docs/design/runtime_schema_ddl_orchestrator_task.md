# Runtime Schema: ТЗ на DDL Orchestrator

## 1. Контекст и цель

Нужно реализовать сервис-оркестратор DDL в `runtime_schema`, который:

1. При создании нового Tenant поднимает системную схему.
2. Поддерживает CRUD пользовательских моделей и полей.
3. Синхронизирует системные модели при обновлении версии приложения (`sync` по diff).

Это **control-plane** модуль: он управляет metadata, layout и DDL, но не владеет runtime CRUD данных записей.

## 2. Что должно быть реализовано

### 2.1 Сценарий bootstrap нового Tenant

Новый tenant должен пройти полный bootstrap схемы:

1. Сгенерировать имя schema.
2. Создать запись в `DataSource`.
3. Создать schema в БД.
4. Прочитать из файла описание системных моделей.
5. Скомпилировать metadata + DDL план.
6. Применить DDL (таблицы, поля, связи, ограничения, индексы).
7. Зафиксировать версию и журнал миграций.

### 2.2 CRUD пользовательских моделей

Пользователь должен иметь возможность:

1. Создать модель.
2. Обновить модель.
3. Удалить модель.
4. Создать поле в модели.
5. Обновить поле.
6. Удалить поле.

Каждая операция должна приводить к:

1. Валидации metadata-команды.
2. Пересборке layout.
3. Генерации DDL diff.
4. Применению DDL в рамках транзакции/единицы работы.
5. Обновлению metadata.

### 2.3 Sync системных моделей при релизе

Нужен метод `sync`, который:

1. Сравнивает желаемое состояние системных моделей (из файла текущей версии приложения) с фактическим состоянием tenant schema.
2. Строит diff.
3. Применяет недостающие изменения в безопасном порядке.
4. Обновляет версию схемы и журнал.

## 3. Границы ответственности

### `runtime_schema` делает

1. Хранение object/field metadata.
2. Компиляцию field layout.
3. Генерацию DDL операций.
4. Применение DDL операций.
5. Синхронизацию схем.

### `runtime_schema` не делает

1. CRUD runtime-записей бизнес-данных.
2. Бизнес-логику owner-модулей (`crm`, `identity` и т.д.).

## 4. Источник описания системных моделей

Нужен файл-реестр, например:

`src/modules/runtime_schema/system_models/system_models.yaml`

Минимальная структура:

```yaml
version: "2026.03.11"
objects:
  - key: lead
    name:
      singular: lead
      plural: leads
    label:
      singular: Lead
      plural: Leads
    is_system: true
    is_custom: false
    fields:
      - name: status
        type: select
        is_nullable: false
        is_index: true
        options:
          - code: new
            label: New
          - code: won
            label: Won
```

Требование: файл должен быть детерминированным, валидироваться схемой (pydantic/jsonschema), и version обязателен.

## 5. Компоненты оркестратора

Нужно добавить следующие части.

### 5.1 Application Use Cases

1. `BootstrapTenantSystemSchemaUseCase`
2. `CreateObjectDefinitionUseCase`
3. `UpdateObjectDefinitionUseCase`
4. `DeleteObjectDefinitionUseCase`
5. `CreateFieldDefinitionUseCase`
6. `UpdateFieldDefinitionUseCase`
7. `DeleteFieldDefinitionUseCase`
8. `SyncTenantSystemSchemaUseCase`

### 5.2 Domain/Service компоненты

1. `SystemModelRegistryReader`  
   Читает и валидирует файл системных моделей.
2. `MetadataCompiler`  
   Преобразует manifest в `ObjectMetadataEntity` и `FieldMetadataEntity`.
3. `FieldLayoutCompiler`  
   Строит physical layout по logical fields.
4. `SchemaIntrospector`  
   Читает текущее состояние schema из БД.
5. `DdlDiffEngine`  
   Считает diff: expected vs actual.
6. `DdlPlanBuilder`  
   Формирует упорядоченный план операций.
7. `DdlExecutor`  
   Применяет DDL операции.
8. `SchemaVersionRepository`  
   Хранит version/hash для sync.
9. `SchemaMigrationJournalRepository`  
   Хранит примененные шаги и их статусы.
10. `SchemaLockService`  
    Блокировка на уровень tenant schema (чтобы не было гонок).

### 5.3 Infrastructure компоненты

1. `SqlAlchemySchemaIntrospector`
2. `SqlAlchemyDdlExecutor`
3. `SqlAlchemySchemaVersionRepository`
4. `SqlAlchemySchemaMigrationJournalRepository`
5. `PgAdvisorySchemaLockService`

## 6. Контракты сервисов (минимум)

```python
class DdlOrchestratorService(Protocol):
    async def bootstrap_tenant_system_schema(
        self, *, tenant_id: UUID, data_source_id: UUID, schema: str
    ) -> None: ...

    async def create_object_definition(self, cmd: CreateObjectCommand) -> ObjectDTO: ...
    async def update_object_definition(self, cmd: UpdateObjectCommand) -> ObjectDTO: ...
    async def delete_object_definition(self, cmd: DeleteObjectCommand) -> None: ...

    async def create_field_definition(self, cmd: CreateFieldCommand) -> FieldDTO: ...
    async def update_field_definition(self, cmd: UpdateFieldCommand) -> FieldDTO: ...
    async def delete_field_definition(self, cmd: DeleteFieldCommand) -> None: ...

    async def sync_tenant_system_schema(
        self, *, tenant_id: UUID, data_source_id: UUID, schema: str
    ) -> SyncResultDTO: ...
```

```python
class DdlDiffEngine(Protocol):
    def diff(self, *, expected: SchemaSnapshot, actual: SchemaSnapshot) -> DdlDiff: ...

class DdlPlanBuilder(Protocol):
    def build(self, *, diff: DdlDiff) -> DdlPlan: ...

class DdlExecutor(Protocol):
    async def execute(self, *, schema: str, plan: DdlPlan) -> ExecutionReport: ...
```

## 7. Данные и таблицы metadata (минимум)

Нужны control-plane таблицы:

1. `object_metadata`
2. `field_metadata`
3. `field_storage_metadata`
4. `field_option_metadata`
5. `schema_version`
6. `schema_migration_journal`

`schema_version` минимум:

1. `tenant_id`
2. `schema`
3. `version`
4. `manifest_hash`
5. `updated_at`

`schema_migration_journal` минимум:

1. `id`
2. `tenant_id`
3. `schema`
4. `operation_key`
5. `operation_sql` (или payload)
6. `status` (`PENDING`, `APPLIED`, `FAILED`)
7. `error_message`
8. `created_at`
9. `applied_at`

## 8. Детальный flow: bootstrap нового Tenant

`BootstrapTenantSystemSchemaUseCase.execute(cmd)`

1. Взять lock по `(tenant_id, schema)`.
2. Проверить idempotency (если version уже актуален и tables существуют, выйти без ошибок).
3. Прочитать manifest системных моделей из файла.
4. Валидировать manifest.
5. Скомпилировать target metadata/layout.
6. Считать actual snapshot schema через introspector.
7. Построить diff.
8. Построить упорядоченный DDL plan:
   1. create tables
   2. add columns
   3. constraints/fk
   4. indexes
9. Применить plan.
10. Записать metadata в репозитории.
11. Обновить `schema_version`.
12. Записать journal.
13. Освободить lock.

## 9. Детальный flow: CRUD моделей и полей

Каждый use-case выполняет общий pipeline:

1. Проверка прав/доступа.
2. Валидация команды.
3. Загрузка текущего metadata состояния.
4. Применение изменения в domain model.
5. Пересборка target layout.
6. Introspect actual schema.
7. Diff и plan.
8. Применение DDL.
9. Сохранение metadata.
10. Обновление version/journal.

### Важные проверки при CRUD

1. Нельзя удалять/ломать системные критичные поля без explicit flag `allow_destructive`.
2. Нельзя делать destructive изменения по умолчанию в production (`drop`, `type narrowing`) без отдельного режима.
3. Для `SELECT/MULTI_SELECT` изменения опций должны быть согласованы с value storage политикой (soft-disable вместо hard-delete).

## 10. Детальный flow: sync при обновлении приложения

`SyncTenantSystemSchemaUseCase.execute(cmd)`

1. Lock `(tenant_id, schema)`.
2. Прочитать актуальный manifest из файла текущей версии приложения.
3. Считать `schema_version` и `manifest_hash`.
4. Если hash совпадает и forced_sync=False, вернуть `NO_CHANGES`.
5. Introspect actual schema.
6. Скомпилировать expected snapshot.
7. Построить diff.
8. Классифицировать diff:
   1. additive safe
   2. risky
   3. destructive
9. Если есть destructive и режим не разрешает, вернуть `BLOCKED` с деталями.
10. Построить и применить plan.
11. Обновить `schema_version` + journal.
12. Вернуть `SyncResultDTO` со списком операций.

## 11. DDL операции, которые поддержать в первой версии

1. `CreateTable`
2. `AddColumn`
3. `AlterColumnNullability`
4. `AddUniqueConstraint`
5. `AddForeignKey`
6. `CreateIndex`
7. `DropIndex` (опционально V1.1)
8. `DropConstraint` (опционально V1.1)

Destructive операции (`DropTable`, `DropColumn`, `AlterType` с потерей данных) в V1 только под флагом.

## 12. Требования к надежности

1. Идемпотентность bootstrap/sync.
2. Защита от конкурентных запусков через lock.
3. Журналирование каждого шага.
4. Явные коды ошибок и recoverability.
5. Таймауты на DDL и retry policy (только для безопасных этапов).

## 13. Интеграция с текущим tenancy flow

Сейчас `CreateTenantUseCase` уже вызывает:

1. генерацию schema name,
2. `create_schema`,
3. создание data source,
4. `runtime_schema_bootstrapper.bootstrap_tenant_system_schema(...)`.

Новый DDL orchestration должен быть реализацией этого bootstrapper (через текущий порт), без слома внешнего контракта:

`TenantRuntimeSchemaBootstrapperProtocol.bootstrap_tenant_system_schema(...)`.

## 14. Набор обязательных методов (чек-лист)

### Bootstrap

1. `load_system_manifest(version?)`
2. `compile_system_schema(manifest)`
3. `introspect_schema(schema)`
4. `build_diff(expected, actual)`
5. `build_plan(diff)`
6. `apply_plan(schema, plan)`
7. `save_schema_version(...)`
8. `append_journal(...)`

### CRUD objects/fields

1. `create_object(...)`
2. `update_object(...)`
3. `delete_object(...)`
4. `create_field(...)`
5. `update_field(...)`
6. `delete_field(...)`
7. `recompile_layout_for_object(...)`

### Sync

1. `sync_schema(...)`
2. `classify_diff(...)`
3. `validate_destructive_policy(...)`

## 15. Acceptance criteria

1. Новый tenant получает полностью созданную системную schema без ручных SQL.
2. CRUD моделей и полей меняет и metadata, и physical schema.
3. `sync` обнаруживает и применяет недостающие изменения.
4. Повторный запуск bootstrap/sync идемпотентен.
5. Все операции логируются в migration journal.
6. На destructive diff без разрешения сервис возвращает блокирующую ошибку.

## 16. План реализации (итерации)

### Итерация 1

1. Manifest reader.
2. Schema introspector.
3. DDL diff + plan для additive операций.
4. Bootstrap use case.
5. `schema_version` + `migration_journal`.

### Итерация 2

1. CRUD объектов.
2. CRUD полей.
3. Partial sync.

### Итерация 3

1. Полноценный sync.
2. Политики destructive миграций.
3. Расширение diff движка.

