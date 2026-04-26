# Описание модулей `schema_registry`, `runtime_data`, `custom_object`

## 1) `schema_registry`

### Назначение
Модуль хранит и синхронизирует metadata runtime-схемы tenant'а, валидирует seed-описание, планирует и применяет DDL-изменения в PostgreSQL, а также строит runtime-descriptor объекта для downstream-модулей.

### Структура
- `application/use_case`
  - `CreateSchemaUseCase` — первичное создание физической схемы + metadata.
  - `DiffSchemaUseCase` — diff между seed/spec и фактической схемой.
  - `DescribeRuntimeObjectUseCase` — описание runtime-объекта для tenant.
- `application/service`
  - `SchemaSeedService` — загрузка и нормализация seed в валидированную спецификацию.
  - `PostgresSchemaService` — проверка существования схемы, инспекция, применение плана.
- `application/migration`
  - `PostgresSchemaPlanService` — построение create/diff migration-планов.
  - `MigrationPlan` + операции (`CreateTableOperation`, `AddColumnOperation`, `Drop*`, `Alter*`, `AddForeignKeyOperation`).
- `application/metadata`
  - `SchemaRegistryMetadataReadService` — чтение консистентного metadata-снимка.
  - `SchemaRegistryMetadataWriteService` — запись/replace/reconcile metadata.
- `domain`
  - `ObjectEntity`, `FieldEntity`, `DataSourceService`, `ObjectService`, value objects, доменные ошибки.
- `runtime`
  - `SchemaRegistryRuntimeObjectResolver` — преобразует metadata в `RuntimeObjectDescriptor`.

### Логика работы
- **Создание схемы**: seed → ensure schema absent → create-plan → apply-plan → create metadata.
- **Diff схемы**: seed/spec + metadata + physical snapshot → diff-plan → apply-plan → reconcile metadata.
- **Ключевые проверки**:
  - целостность tenant/data_source ссылок,
  - запрет небезопасных изменений retained-колонок,
  - обязательность `id` в runtime descriptor.

---

## 2) `runtime_data`

### Назначение
Универсальный слой runtime CRUD по `RuntimeObjectDescriptor`: типизация payload, фильтры/сортировка/пагинация/projection, безопасная генерация SQL и нормализация строк.

### Структура
- `application/models`
  - `FilterSpec`, `FilterGroupSpec`, `SortSpec`, `PageSpec`, `FetchPlan`.
- `application/ports`
  - `RuntimeCommandGateway`, `RuntimeQueryGateway`, `RuntimeRelationLoader`.
- `application/type_policy`
  - `RuntimeFieldTypePolicy`, `RuntimeFieldTypeDefinition`.
- `infrastructure/postgres`
  - `PostgresRuntimeGateway` — реализация CRUD/list.
  - `NoopRuntimeRelationLoader` — заглушка relation-loader.
- `domain/error`
  - типы ошибок: validation/filter/policy/persistence.

### Логика работы
1. Валидируется descriptor и SQL-идентификаторы.
2. Payload приводится к каноническим типам (`uuid`, `int`, `decimal`, `date`, `datetime`, `json`, `multiselect`, ...).
3. Формируется параметризованный SQL с bind-параметрами.
4. Выполняется запрос через SQLAlchemy; ошибки преобразуются в доменные.
5. Строки нормализуются (например, datetime к UTC-aware при чтении).

### Поддерживаемые фильтры
- Операторы: `eq`, `in`, `contains`, `gte`, `lte`.
- Группы: `and` / `or` (вложенные выражения).

---

## 3) `custom_object`

### Назначение
Прикладной модуль для пользовательских объектов, который поверх `schema_registry` и `runtime_data` реализует:
- CRUD custom-объектов,
- CRUD custom-полей,
- CRUD runtime-записей custom-объектов,
- HTTP API и DI-склейку use case'ов.

### Структура
- `application/object`
  - команды/запросы/DTO/use-cases: create/list/describe/delete.
- `application/field`
  - команды/DTO/use-cases: add/delete.
- `application/record`
  - команды/запросы/DTO/use-cases: create/get/list/update/delete.
  - `filter_dsl.py` — парсер публичного DSL фильтров/сортировки.
- `infrastructure`
  - `CustomObjectSchemaRepository` — metadata + targeted DDL (таблицы/колонки).
  - `CustomRecordRuntimeRepository` — runtime CRUD через gateways.
- `presentation`
  - FastAPI router + dependency providers.
- `domain/error`
  - специализированные ошибки custom-object слоя.

### Логика работы
- **Создание custom-объекта**:
  1) проверка уникальности имён,
  2) создание metadata объекта,
  3) добавление системных полей (`id`, `created_at`, `updated_at`),
  4) генерация DDL плана (`create table`, `add columns`, индекс по `id`),
  5) применение DDL и сохранение metadata.
- **Добавление/удаление custom-поля**:
  - синхронное изменение metadata + физической колонки.
- **CRUD записей**:
  - резолв descriptor по tenant/object,
  - запрет записи в system fields,
  - выполнение insert/get/list/update/delete через runtime gateway,
  - маппинг строк в DTO.

### `filter_dsl`
- Преобразует входной JSON-фильтр в `runtime_data` модели.
- Валидирует структуру групп (`and`/`or`) и операторов.
- Парсит sort map в последовательность `SortSpec`.

---

## Связь модулей между собой
- `schema_registry` — источник истины о metadata и генератор descriptor.
- `runtime_data` — исполнитель runtime-операций по descriptor.
- `custom_object` — бизнес-слой, который использует оба модуля для работы с пользовательскими объектами и их данными.
