# Schema Registry: создание схемы и миграция схемы (diff)

Этот документ описывает, как работает участок кода `schema_registry`, отвечающий за:

1. **Создание новой runtime-схемы** (`CreateSchemaUseCase`)
2. **Миграцию/синхронизацию существующей схемы с seed-описанием** (`DiffSchemaUseCase`)

> Важно: в текущем коде миграция реализована как **diff + apply** (построение плана изменений и его применение), а не как классические версионированные SQL-файлы.

---

## 1) Классы и методы: зоны ответственности

Ниже перечислены ключевые классы и методы именно для двух use case.

## Application layer

### `CreateSchemaUseCase`
- `__init__(...)` — получает зависимости: загрузка seed, построение миграционного плана, применение плана в PostgreSQL, запись метаданных в schema_registry.
- `execute(command)` — сценарий создания схемы:
  1) валидирует `tenant_id` через `EntityIdVO`,
  2) загружает/нормализует seed,
  3) проверяет, что физическая schema ещё не существует,
  4) строит create-план,
  5) применяет его,
  6) создаёт metadata-записи datasource/objects/fields.

### `DiffSchemaUseCase`
- `__init__(...)` — получает зависимости: seed, чтение metadata, planner, инспектор/исполнитель PostgreSQL, reconciliation metadata.
- `execute(command)` — сценарий миграции:
  1) валидирует `tenant_id`,
  2) загружает seed,
  3) читает текущий metadata snapshot по tenant,
  4) инспектирует реальную физическую схему,
  5) строит diff-план,
  6) применяет план,
  7) reconciles metadata,
  8) возвращает DTO со статистикой (сколько операций, сколько destructive).

### `CreateSchemaCommand`, `DiffSchemaCommand`
- Простые immutable-команды (вход в use case).

### `DiffSchemaResultDTO`
- DTO результата diff-выполнения (агрегированная статистика по операциям).

---

## Seed и валидация

### `SchemaSeedService`
- `load(seed_path)` — читает seed через порт `SeedReaderPort`, затем нормализует/валидирует.
- `_normalize(seed)` — ключевая бизнес-валидация seed:
  - уникальность имён объектов,
  - уникальность полей в объекте,
  - корректность индексов (существование полей, уникальность имени индекса глобально),
  - корректность relations (source/target поля и объекты),
  - нормализация relation_type / on_delete,
  - автогенерация уникального индекса для `one_to_one`.
- `_validate_identifier(...)` — валидация postgres-friendly identifier через `SchemaNamingStrategy`.
- `_normalize_relation_type(...)` — приводит relation_type к enum и проверяет допустимость.
- `_normalize_on_delete(...)` — нормализует стратегию delete.
- `_normalize_default(...)` — trim/normalization default значений.
- `_ensure_global_index_name_is_unique(...)` — защищает от конфликтов индексов между таблицами.

### `PythonModuleSeedReader`
- `read(seed_path)` — импортирует python-модуль и читает `SCHEMA_SEED`.
  - Проверяет, что модуль существует,
  - что атрибут `SCHEMA_SEED` есть,
  - и что он типа `SchemaSeed`.

---

## Планирование миграций

### `PostgresSchemaPlanService`
- `build_create_plan(schema_name, seed)` — строит полный план “с нуля”:
  - `CREATE SCHEMA`,
  - `CREATE TABLE`,
  - `ADD COLUMN`,
  - `CREATE INDEX`,
  - `ADD FOREIGN KEY`.
- `build_diff_plan(schema_name, seed, actual_schema)` — строит безопасный diff-план:
  - сначала удаление FK/index/columns/tables, которые лишние или изменены (как destructive),
  - затем добавление новых table/column,
  - изменение default (через `ALTER COLUMN DEFAULT`),
  - затем добавление нужных index/FK.
  - Неподдерживаемые изменения (например type/nullability retained-column) выбрасывают `UnsupportedSchemaChangeError`.
- `_build_desired_schema(...)` — конвертирует seed/spec в `PhysicalSchemaSnapshot`.
- `_build_table_snapshot_from_seed(...)` / `_build_table_snapshot_from_spec(...)` — собирает snapshot таблицы.
- `_build_column_snapshot_from_seed(...)` / `_build_column_snapshot_from_spec(...)` — определяет SQL-тип и default.
- `_build_foreign_key_snapshot(...)` — строит FK snapshot.
- `_normalize_on_delete(...)`, `_normalize_relation_type(...)` — валидация/нормализация relation семантики.

### `PostgresFieldCanonicalizer`
- `sql_preset_from_field_type(...)` — доменный field type -> SQL preset.
- `sql_preset_from_postgres_type(...)` — PostgreSQL `format_type` -> SQL preset.
- `render_sql_preset(...)` — SQL preset -> конкретный SQL-тип.
- `normalize_seed_default(...)` — безопасная нормализация default из seed (ошибки как `SeedValidationError`).
- `normalize_postgres_default(...)` — нормализация default из introspection PostgreSQL.
- Внутренние helpers (`_normalize_default`, `_strip_outer_parentheses`, `_strip_postgres_casts`, `_extract_literal`, `_quote_sql_string`) приводят default к каноническому виду для корректного сравнения в diff.

### `MigrationPlan`
- `add(...)`, `extend(...)` — обычные операции.
- `add_destructive(...)`, `extend_destructive(...)` — destructive-операции (помечаются отдельно).
- `is_empty` — есть ли вообще изменения.
- `has_destructive_changes` — есть ли потенциально опасные изменения.

### `operations.py`
- Набор dataclass-операций (`CreateTableOperation`, `DropColumnOperation`, `AddForeignKeyOperation` и т.д.), из которых состоит план миграции.

### `physical_schema_snapshot.py`
- Snapshot-модель реальной/желаемой схемы:
  - `PhysicalSchemaSnapshot`, `TableSnapshot`, `ColumnSnapshot`, `IndexSnapshot`, `ForeignKeySnapshot`.
- Методы `get_*` помогают lookup при построении diff.

---

## Доступ к PostgreSQL

### `PostgresSchemaService`
- `ensure_schema_absent(schema_name)` — проверяет, что schema ещё нет (для create).
- `inspect_required_schema(schema_name)` — проверяет наличие schema и возвращает её snapshot.
- `apply_plan(plan)` — применяет план через executor (no-op для пустого плана).

### `PostgresTenantSchemaInspector`
- `schema_exists(schema_name)` — проверка существования schema в `information_schema.schemata`.
- `inspect(schema_name)` — агрегирует таблицы/колонки/индексы/FK в `PhysicalSchemaSnapshot`.
- `_load_tables`, `_load_columns`, `_load_indexes`, `_load_foreign_keys` — SQL introspection по catalog-таблицам PostgreSQL.
- `_ensure_postgres()` — защита от запуска не на PostgreSQL.

### `PostgresTenantSchemaExecutor`
- `execute(plan)` — выполняет каждую операцию плана по очереди + `flush()`.
- `_execute_operation(operation)` — маппинг operation -> SQL (`CREATE TABLE`, `ALTER TABLE`, `DROP INDEX` и т.д.).
- `_ensure_postgres()` — защита backend.
- `_qi`, `_qualified_table`, `_qualified_index` — quoting/qualified names.
- `_normalize_on_delete(...)` — нормализация поведения FK на delete.

---

## Metadata (schema_registry таблицы)

### `SchemaRegistryMetadataWriteService`
- `create_from_seed(...)` — создаёт datasource + полностью заполняет objects/fields из seed.
- `replace_from_seed(...)` — пересобирает objects/fields поверх существующего datasource.
- `reconcile_from_spec(...)` — диффит и синхронизирует metadata с валидированным spec.

### `SchemaRegistryMetadataReadService`
- `get_required_by_tenant(...)` — читает datasource + objects.
- Проверяет внутреннюю консистентность (`tenant_id`, `data_source_id`) и возвращает snapshot.

### `SchemaRegistryMetadataSnapshot`
- immutable контейнер (`datasource`, `objects`) для передачи текущего состояния metadata.

---

## Domain services и entities (используются metadata-сервисами)

### `DataSourceService`
- `create(...)` — создаёт datasource для tenant (с проверкой, что не существует).
- `get_required_by_tenant(...)` — обязательное чтение datasource.

### `ObjectService`
- `replace_all_for_tenant_from_seed(...)` — полная пересборка objects/fields.
- `reconcile_for_tenant_from_spec(...)` — обновление objects/fields с сохранением существующих ID там, где возможно.
- `list_by_tenant_id(...)` — чтение objects.
- Внутренние:
  - `_reconcile_fields(...)` — добавляет/обновляет/удаляет поля в объекте,
  - `_create_object_entity(...)` — фабрика ObjectEntity,
  - `_append_fields_from_seed(...)` / `_append_fields_from_spec(...)` — массовое заполнение полей,
  - `_update_object_metadata(...)` — обновление имени/лейбла/описания только если реально изменилось.

### `DataSourceEntity`, `ObjectEntity`, `FieldEntity`
- Доменные сущности metadata.
- `ObjectEntity` и `FieldEntity` содержат инварианты (уникальность имени поля, запрет недопустимых options/type-change и т.д.)

### Репозитории
- `SqlAlchemyDataSourceRepository` — CRUD datasource через ORM.
- `SqlAlchemyObjectRepository` — CRUD/replace/reconcile для objects+fields.

---

## 2) Дерево вызовов (Call Tree)

Ниже показано дерево вызовов в двух ключевых use case.

## UseCase A: `CreateSchemaUseCase.execute`

1. `CreateSchemaUseCase.execute(command)`
   1. `EntityIdVO.from_value(command.tenant_id)`
   2. `SchemaSeedService.load(seed_path)`
      - `PythonModuleSeedReader.read(seed_path)`
      - `SchemaSeedService._normalize(seed)`
   3. `PostgresSchemaService.ensure_schema_absent(schema_name)`
      - `PostgresTenantSchemaInspector.schema_exists(schema_name)`
   4. `PostgresSchemaPlanService.build_create_plan(schema_name, seed)`
      - `_build_desired_schema(...)`
      - генерирует `MigrationPlan` из операций create
   5. `PostgresSchemaService.apply_plan(plan)`
      - `PostgresTenantSchemaExecutor.execute(plan)`
      - `PostgresTenantSchemaExecutor._execute_operation(...)` для каждой операции
   6. `SchemaRegistryMetadataWriteService.create_from_seed(...)`
      - `DataSourceService.create(...)`
        - `SqlAlchemyDataSourceRepository.get_by_tenant_id(...)`
        - `SqlAlchemyDataSourceRepository.add(...)`
      - `ObjectService.replace_all_for_tenant_from_seed(...)`
        - сборка `ObjectEntity`/`FieldEntity`
        - `SqlAlchemyObjectRepository.replace_all_for_tenant(...)`

Итог: создана физическая schema в PostgreSQL + записаны метаданные registry.

## UseCase B: `DiffSchemaUseCase.execute`

1. `DiffSchemaUseCase.execute(command)`
   1. `EntityIdVO.from_value(command.tenant_id)`
   2. `SchemaSeedService.load(seed_path)`
      - `PythonModuleSeedReader.read(seed_path)`
      - `SchemaSeedService._normalize(seed)`
   3. `SchemaRegistryMetadataReadService.get_required_by_tenant(tenant_id)`
      - `DataSourceService.get_required_by_tenant(...)`
        - `SqlAlchemyDataSourceRepository.get_by_tenant_id(...)`
      - `ObjectService.list_by_tenant_id(...)`
        - `SqlAlchemyObjectRepository.list_by_tenant_id(...)`
      - консистентность-проверки snapshot
   4. `PostgresSchemaService.inspect_required_schema(schema_name)`
      - `PostgresTenantSchemaInspector.schema_exists(...)`
      - `PostgresTenantSchemaInspector.inspect(...)`
        - `_load_tables` / `_load_columns` / `_load_indexes` / `_load_foreign_keys`
   5. `PostgresSchemaPlanService.build_diff_plan(schema_name, seed, actual_schema)`
      - `_build_desired_schema(...)`
      - сравнение desired vs actual
      - формирование destructive и non-destructive операций
   6. `PostgresSchemaService.apply_plan(plan)`
      - `PostgresTenantSchemaExecutor.execute(plan)`
      - SQL по операциям
   7. `SchemaRegistryMetadataWriteService.reconcile_from_spec(...)`
      - `DataSourceService.get_required_by_tenant(...)`
      - `ObjectService.reconcile_for_tenant_from_spec(...)`
        - `SqlAlchemyObjectRepository.list_by_tenant_id(...)`
        - `SqlAlchemyObjectRepository.reconcile_for_tenant(...)`
   8. Возврат `DiffSchemaResultDTO`

Итог: физическая schema приведена к seed, metadata синхронизирована, вызвавший код получает summary изменений.

---

## 3) Где начинается выполнение на практике

В management CLI для schema_registry сейчас зарегистрирована команда `diff`:
- `handle_diff(...)` создаёт `UnitOfWork`, собирает зависимости (`build_diff_schema_use_case`) и запускает `DiffSchemaUseCase.execute(...)`.

Фабрика зависимостей:
- `presentation/depends/management.py::build_diff_schema_use_case`
- `presentation/depends/application.py`
- `presentation/depends/infrastructure.py`

Это хорошая точка входа для отладки в рантайме.
