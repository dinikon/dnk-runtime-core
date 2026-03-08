# Runtime Schema Custom Fields: Clean Architecture

## Цель

Этот документ описывает целевую реализацию declarative custom fields для системных и runtime-объектов.

Это не описание текущего состояния кода. Это описание того, как фичу нужно реализовать правильно:

- с чистым разложением по слоям;
- с разделением metadata и record storage;
- с поддержкой системных сущностей вроде `Lead`;
- с declarative logical types, которые компилируются в primitive storage.

## Проблема, которую нужно решить

Система должна уметь объявлять поля через metadata в БД, но физически хранить данные в primitive storage.

Нужно поддержать logical field types:

- `BOOLEAN`
- `JSON`
- `SELECT`
- `MULTISELECT`
- `ADDRESS`
- `ARRAY`
- `LINK`

При этом:

- system entity, например `Lead`, должна сохранять свои предметные инварианты;
- custom fields не должны ломать доменный код `crm`;
- валидация, фильтрация, ACL и views должны работать на уровне logical fields, а не raw storage.

## Базовые принципы

### 1. `runtime_schema` не должен владеть record CRUD

`runtime_schema` - это control-plane bounded context.

Он должен отвечать за:

- object definitions;
- field definitions;
- storage layout compilation;
- physical schema synchronization;
- field capabilities;
- metadata validation.

Он не должен сам реализовывать CRUD бизнес-записей.

### 2. Metadata и data-plane должны быть разделены

Нужно чётко разделить:

- logical field definition;
- physical storage layout;
- record value handling.

Правильная схема:

- `runtime_schema` - описывает, что такое поле;
- `runtime_records` или аналогичный data module - знает, как хранить и читать значения;
- owner-module, например `crm`, владеет только системной предметной логикой.

### 3. Один logical field не обязан равняться одной SQL-колонке

Это ключевой принцип.

Например:

- `ADDRESS` = несколько primitive columns;
- `MULTISELECT` = несколько primitive rows;
- `ARRAY` = несколько primitive rows;
- `LINK` = набор ссылок на target records.

Если пытаться заставить все logical types жить как `1 field = 1 column`, архитектура сразу ломается.

### 4. Многозначные поля нельзя чисто реализовать только колонками основной таблицы

Для `ARRAY`, `MULTISELECT` и `LINK` правильное решение - side tables.

Если хранить их в одной JSON/TEXT колонке:

- ломается нормальная фильтрация;
- усложняется индексация;
- теряется целостность;
- `LINK` перестаёт быть нормальной ссылкой.

Поэтому требование "в таблице создаются примитивы" должно пониматься так:

- для fixed-shape fields создаются primitive columns;
- для collection fields создаются primitive child rows в storage tables.

## Целевая модель слоёв

## Layer 1. Domain: logical schema

Модуль: `runtime_schema/domain`

Главные сущности:

- `ObjectDefinition`
- `FieldDefinition`
- `FieldOption`
- `FieldLayout`
- `FieldComponent`

### `FieldDefinition`

Описывает logical field:

- `field_id`
- `object_id`
- `name`
- `label`
- `logical_type`
- `is_required`
- `is_unique`
- `is_system`
- `is_custom`
- `is_active`
- `settings`
- `capabilities`

Важно: `FieldDefinition` не хранит SQL-тип напрямую.

### `FieldLayout`

Описывает physical storage, сгенерированный из logical type.

Примеры:

- `BOOLEAN` -> 1 scalar component
- `JSON` -> 1 scalar component
- `SELECT` -> 1 scalar component
- `ADDRESS` -> 5 scalar components
- `MULTISELECT` -> collection storage
- `ARRAY` -> collection storage
- `LINK` -> collection storage с target object contract

## Layer 2. Application: schema orchestration

Модуль: `runtime_schema/application`

Use case'ы:

- `CreateCustomFieldUseCase`
- `UpdateCustomFieldUseCase`
- `DeleteCustomFieldUseCase`
- `GetFieldDefinitionUseCase`
- `ListObjectFieldDefinitionsUseCase`
- `CompileFieldLayoutUseCase`
- `SyncPhysicalSchemaUseCase`

Задачи application-слоя:

- валидировать metadata-команду;
- собрать `FieldDefinition`;
- скомпилировать `FieldLayout`;
- сохранить metadata;
- синхронизировать physical schema.

## Layer 3. Infrastructure: metadata persistence + DDL

Модуль: `runtime_schema/infrastructure`

Нужны отдельные части:

- metadata repositories;
- field layout repository;
- DDL generator;
- schema synchronizer.

`SchemaManager` не должен больше работать по модели `field -> one column`.
Он должен принимать `FieldLayout`.

## Layer 4. Runtime values

Нужен отдельный bounded context, например:

- `src/modules/runtime_records`

Он должен отвечать за:

- write/read values;
- serialization logical payload <-> storage;
- query compilation;
- filter/sort over logical field paths;
- storage transactions.

Это нельзя держать внутри `runtime_schema`, иначе metadata и data-plane смешаются.

## Logical types и их правильное хранение

### `BOOLEAN`

Хранение:

- одна `BOOLEAN` колонка

Валидация:

- только `true/false`

### `JSON`

Хранение:

- одна `JSONB` колонка

Валидация:

- валидный JSON
- опционально schema-based JSON validation

### `SELECT`

Хранение:

- одна scalar колонка, обычно `VARCHAR`

В metadata:

- список допустимых options

Валидация:

- значение должно быть одним из активных option codes

### `MULTISELECT`

Хранение:

- child table `record_id + option_code`

Валидация:

- все значения должны быть допустимыми option codes
- без дублей

### `ADDRESS`

Хранение:

- набор inline columns

Пример:

- `shipping_address_country`
- `shipping_address_region`
- `shipping_address_city`
- `shipping_address_line`
- `shipping_address_number`

В metadata:

- фиксированный набор subfields
- правила required parts

Валидация:

- объект допустимой структуры
- проверка required subfields
- нормализация строк

### `ARRAY`

Хранение:

- child table `record_id + position + primitive_value`

В metadata:

- `item_type`
- `max_length`
- `allow_duplicates`

Валидация:

- все элементы одного primitive type
- ограничения массива

### `LINK`

Хранение:

- child table `record_id + target_record_id`

В metadata:

- `target_object_metadata_id`
- cardinality rules

Валидация:

- все target records существуют
- принадлежат нужному object type
- принадлежат нужному tenant

## Metadata persistence model

Нужно ввести минимум 3 control-plane таблицы.

### `field_metadata`

Хранит logical field definition:

- `id`
- `tenant_id`
- `object_metadata_id`
- `name_field`
- `label`
- `logical_type`
- `settings`
- `is_system`
- `is_custom`
- `is_active`
- `is_nullable`
- `is_unique`
- `is_ui_read_only`

### `field_storage_metadata`

Хранит compiled storage layout:

- `id`
- `field_metadata_id`
- `storage_kind`
- `component_name`
- `column_name`
- `primitive_type`
- `position`
- `is_nullable`
- `is_indexed`

### `field_option_metadata`

Для `SELECT` и `MULTISELECT`:

- `id`
- `field_metadata_id`
- `value`
- `label`
- `color`
- `position`
- `is_active`

Опционально:

### `field_collection_metadata`

Для `ARRAY` и `LINK`:

- `field_metadata_id`
- `item_primitive_type`
- `target_object_metadata_id`
- `ordering_strategy`

## Storage strategies

Нужно формально ввести storage strategies.

### `INLINE_SINGLE`

Подходит для:

- `BOOLEAN`
- `JSON`
- `SELECT`
- scalar system fields

### `INLINE_COMPOSITE`

Подходит для:

- `ADDRESS`

### `COLLECTION`

Подходит для:

- `ARRAY`
- `MULTISELECT`
- `LINK`

## Правильная работа системной сущности с custom fields

Пример: `Lead`

`Lead` должен быть разделён на:

- `LeadCore`
- `LeadCustomValues`

### `LeadCore`

Содержит только системные поля и инварианты:

- `title`
- `assigned_user_id`
- `contact_id`
- `company_id`
- lifecycle fields

Именно здесь должна жить предметная бизнес-логика CRM.

### `LeadCustomValues`

Это runtime-managed extension того же объекта `lead`.

Он не должен попадать в доменный класс `LeadCore`.

Он должен жить в runtime record layer как metadata-driven payload.

## Как должен выглядеть write flow

Пример `UpdateLead`.

### Шаг 1. Load metadata

Загружаются:

- object definition `lead`
- field definitions для `lead`

### Шаг 2. Split payload

Payload делится на:

- system fields
- custom fields

Пример:

```json
{
  "title": "Lead A",
  "company_id": "uuid",
  "budget": {"amount": 1200, "currency": "USD"},
  "shipping_address": {
    "country": "UA",
    "city": "Kyiv",
    "line": "Khreshchatyk"
  }
}
```

Где:

- `title`, `company_id` -> `LeadCore`
- `budget`, `shipping_address` -> runtime custom field engine

### Шаг 3. Validate system part

`crm`-слой валидирует и применяет только свою предметную часть.

### Шаг 4. Validate custom part

Runtime field engine:

- определяет logical type поля;
- прогоняет value через normalizer/validator;
- компилирует value в storage writes.

### Шаг 5. Save atomically

В одной UoW сохраняются:

- core entity state;
- custom field storage values.

## Как должен выглядеть read flow

### Шаг 1. Read core record

Owner module читает системную часть `LeadCore`.

### Шаг 2. Read custom values

Runtime record engine читает значения custom fields.

### Шаг 3. Assemble response

На выходе формируется единый DTO:

```json
{
  "id": "...",
  "title": "Lead A",
  "company_id": "...",
  "budget": {"amount": 1200, "currency": "USD"},
  "shipping_address": {
    "country": "UA",
    "city": "Kyiv",
    "line": "Khreshchatyk"
  }
}
```

Это должна делать отдельная assembler-компонента, а не доменный класс `LeadCore`.

## Где должна жить бизнес-логика

### В `crm`

Только инварианты системной сущности:

- обязательные поля;
- transitions;
- специальные правила `Lead`;
- cross-system business rules.

### В runtime field engine

Только generic logic:

- validation;
- normalization;
- storage mapping;
- serialization;
- filter/sort translation.

### Не должно быть

Нельзя:

- добавлять custom fields в dataclass `Lead`;
- захламлять `LeadApplicationService` знанием `ADDRESS`, `MULTISELECT`, `LINK`;
- заставлять owner-модуль разбирать raw metadata settings.

## ACL, filters и views

`access_control` и `universal_access` должны работать на logical field path.

Примеры:

- `budget.amount`
- `shipping_address.city`
- `tags`

Это значит:

- ACL хранит `field_id` и optional `subfield_name`;
- query compiler умеет превращать logical path в storage query;
- views описывают logical fields, а не raw columns.

## Правильное разложение модулей

### `runtime_schema`

Владеет:

- object definitions
- field definitions
- field layout compilation
- metadata validation
- DDL sync

### `runtime_records`

Владеет:

- generic record value storage
- custom field reads/writes
- query compiler
- collection storage
- field serializers

### `crm`

Владеет:

- system entities
- business invariants
- system use case orchestration

### `universal_access`

Владеет:

- generic console facade
- views
- object tree
- DTO assembly for UI

### `access_control`

Владеет:

- access decisions
- logical field path constraints

## Чего не нужно делать

- Не делать `FieldMetadata` универсальным мешком, где вся схема лежит в `settings`.
- Не смешивать logical type и SQL type.
- Не использовать JSON column как универсальный storage для всех сложных типов.
- Не расширять `Lead`, `Deal`, `Company`, `Contact` произвольными полями на уровне dataclass.
- Не оставлять custom field writes внутри owner service.

## Минимальный целевой результат

Фича считается реализованной правильно, если:

1. системная сущность и custom fields живут раздельно;
2. logical field type не зависит от physical storage shape;
3. fixed-shape fields компилируются в primitive columns;
4. collection fields компилируются в primitive child rows;
5. validation описывается metadata и исполняется централизованно;
6. `crm` не знает деталей `ADDRESS`, `MULTISELECT`, `LINK`;
7. `universal_access` и `access_control` работают с logical fields, а не с raw storage.

## Рекомендуемый порядок внедрения

1. Ввести новую metadata model: logical type + storage layout.
2. Добавить DDL compiler и schema sync для field layouts.
3. Выделить отдельный runtime records module.
4. Перевести custom field storage на generic engine.
5. Переписать `Lead`/`Deal` flows на split: core fields + custom values.
6. Расширить filters, ACL и views на logical subfields.
7. Только после этого включать UI для создания custom fields.
