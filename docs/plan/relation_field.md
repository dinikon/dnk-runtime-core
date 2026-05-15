# План расширения `runtime_schema`: связи между объектами

Текущее состояние: `many_to_one` уже материализуется как FK, `one_to_one` как FK + unique index, а `one_to_many` и
`many_to_many` известны как relation types, но пока отклоняются как unsupported.

## 1. Цель расширения

Добавить полноценную модель связей между runtime-объектами:

```text
OneToOne
OneToMany
ManyToMany
```

При этом связи должны быть частью `schema_registry`, а `runtime_data` должен использовать metadata связей для чтения,
записи и join-операций.

---

# 2. Архитектурное решение

## 2.1. Разделяем Field и Relation

```text
FieldEntity
- описывает поле/колонку объекта

RelationEntity
- описывает связь между двумя объектами
```

Почему так:

```text
OneToOne / ManyToOne:
- есть физическое FK-поле

OneToMany:
- физического поля на стороне one нет
- это reverse-связь

ManyToMany:
- нет поля в основных таблицах
- есть отдельная relation table
```

Поэтому связь не должна жить только в `Field.settings`.

---

# 3. Domain model

## 3.1. Добавить RelationEntity

```python
class RelationEntity:
    id: RuntimeRelationIdVO
    tenant_id: EntityIdVO
    data_source_id: DataSourceIdVO

    name: str
    label: str | None

    relation_type: RelationType

    source_object_id: RuntimeObjectIdVO
    target_object_id: RuntimeObjectIdVO

    owning_object_id: RuntimeObjectIdVO | None
    fk_field_id: RuntimeFieldIdVO | None

    referenced_object_id: RuntimeObjectIdVO | None
    referenced_field_id: RuntimeFieldIdVO | None

    source_relation_name: str | None
    target_relation_name: str | None

    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None

    on_delete: RelationOnDelete
    is_required: bool
    is_unique: bool

    kind: RelationKind
    settings: dict

    created_at: datetime
    updated_at: datetime
```

Семантика:

```text
source_object_id / target_object_id:
- logical/API direction relation

owning_object_id / fk_field_id:
- physical FK side for many_to_one / one_to_one / one_to_many
- null for many_to_many

referenced_object_id / referenced_field_id:
- referenced side for FK-based relations
- null for many_to_many

relation_table_name / *_join_column_name:
- physical relation table contract for many_to_many
- null for FK-based relations
```

## 3.2. RelationType

```python
class RelationType(str, Enum):
    MANY_TO_ONE = "many_to_one"
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
```

Даже если публично нужны только:

```text
OneToOne
OneToMany
ManyToMany
```

внутри нужно оставить `MANY_TO_ONE`, потому что текущий seed и физическая FK-модель уже используют этот тип.

## 3.3. RelationKind

```python
class RelationKind(str, Enum):
    SYSTEM = "system"
    STANDARD = "standard"
    CUSTOM = "custom"
```

Правила такие же, как для объектов и полей: `SYSTEM/VIEW` read-only, `STANDARD` можно расширять, `CUSTOM` можно
создавать и удалять. Текущая config API политика уже построена вокруг `SYSTEM`, `STANDARD`, `CUSTOM`.

## 3.4. RelationOnDelete

```python
class RelationOnDelete(str, Enum):
    RESTRICT = "restrict"
    CASCADE = "cascade"
    SET_NULL = "set_null"
    NO_ACTION = "no_action"
```

```text
default = restrict
```

---

# 4. Metadata tables

Сейчас metadata graph хранит только datasource, objects, fields.
Нужно добавить таблицу `relations`.

## 4.1. `relations`

Реальное имя новой metadata-таблицы:

```text
relations
```

FK должны ссылаться на реальные ORM-таблицы:

```text
data_sources.id
objects.id
fields.id
```

```sql
CREATE TABLE relations
(
    id                      uuid PRIMARY KEY,
    tenant_id               uuid        NOT NULL,
    data_source_id          uuid        NOT NULL,

    name                    text        NOT NULL,
    label                   text,

    relation_type           text        NOT NULL,

    source_object_id        uuid        NOT NULL,
    target_object_id        uuid        NOT NULL,

    owning_object_id        uuid NULL,
    fk_field_id             uuid NULL,

    referenced_object_id    uuid NULL,
    referenced_field_id     uuid NULL,

    source_relation_name    text NULL,
    target_relation_name    text NULL,

    relation_table_name     text NULL,
    source_join_column_name text NULL,
    target_join_column_name text NULL,

    on_delete               text        NOT NULL DEFAULT 'restrict',
    is_required             boolean     NOT NULL DEFAULT false,
    is_unique               boolean     NOT NULL DEFAULT false,

    kind                    text        NOT NULL DEFAULT 'standard',
    settings                jsonb       NOT NULL DEFAULT '{}'::jsonb,

    created_at              timestamptz NOT NULL,
    updated_at              timestamptz NOT NULL,

    CONSTRAINT uq_relations_tenant_datasource_name
        UNIQUE (tenant_id, data_source_id, name),

    CONSTRAINT fk_relations_data_source
        FOREIGN KEY (data_source_id)
            REFERENCES data_sources (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_source_object
        FOREIGN KEY (source_object_id)
            REFERENCES objects (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_target_object
        FOREIGN KEY (target_object_id)
            REFERENCES objects (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_owning_object
        FOREIGN KEY (owning_object_id)
            REFERENCES objects (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_referenced_object
        FOREIGN KEY (referenced_object_id)
            REFERENCES objects (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_fk_field
        FOREIGN KEY (fk_field_id)
            REFERENCES fields (id)
            ON DELETE RESTRICT,

    CONSTRAINT fk_relations_referenced_field
        FOREIGN KEY (referenced_field_id)
            REFERENCES fields (id)
            ON DELETE RESTRICT
);
```

## 4.2. Почему RESTRICT, а не CASCADE

Удаление object/field/relation должно идти только через UseCase.

UseCase обязан:

```text
1. Загрузить RelationEntity и связанные FieldEntity/ObjectEntity.
2. Проверить kind и runtime data impact.
3. Построить physical DDL drop plan.
4. Применить DDL.
5. Удалить metadata.
6. Commit.
```

Если сделать `ON DELETE CASCADE`, можно случайно удалить metadata relation и оставить physical FK/index/relation table в
tenant schema. Это создаст рассинхронизацию metadata graph и физической схемы.

## 4.3. PR-1 migration flow

PR-1 не должен менять physical tenant schemas и не должен менять таблицу `fields`.

Flow:

```text
1. Создать metadata-таблицу relations.
2. Не менять таблицу fields.
3. Не менять физические tenant schemas.
4. При следующем metadata write/diff/create-schema записывать RelationEntity из seed.
5. Для уже существующих datasource сделать backfill из текущего seed.
```

Backfill должен:

```text
1. Прочитать текущий seed.
2. Найти many_to_one и one_to_one relations.
3. Найти source object.
4. Найти target object.
5. Найти FK field.
6. Найти referenced field, обычно id.
7. Вставить rows в relations.
```

Backfill не должен:

```text
- создавать/удалять tenant tables
- создавать/удалять tenant columns
- создавать/удалять FK/index constraints
- менять rows в fields
```

---

# 5. FieldEntity changes

## 5.1. Решение по reference field type

Decision:

```text
Не добавлять FieldType.REFERENCE в MVP.
```

FK-поля остаются обычным типом:

```text
uuid
```

То, что поле является FK, определяется через:

```text
relations.fk_field_id -> fields.id
```

То есть:

```text
FieldEntity.type = uuid
RelationEntity.fk_field_id = fields.id
```

Почему так:

```text
1. В текущем enum нет reference.
2. Физически FK-колонка в PostgreSQL — это uuid.
3. UI/API может показывать field как relation field через RelationDescriptor.
4. Не нужно мигрировать существующие fields.
```

Позже можно добавить computed descriptor:

```json
{
  "field_name": "company_id",
  "field_type": "uuid",
  "semantic_type": "reference",
  "relation_id": "...",
  "target_object": "companies"
}
```

## 5.2. Решение по FieldEntity.relation_id, is_unique, is_indexed

Decision для PR-1:

```text
Не добавлять в fields новые колонки:
- relation_id
- is_unique
- is_indexed
```

Вместо этого:

```text
relations.fk_field_id -> fields.id
relations.is_unique
```

Причина:

```text
FieldEntity сейчас отвечает за logical type, label, nullability,
default, options и settings.

RelationEntity должен стать отдельной частью metadata graph.
```

Resolver не должен искать `field.relation_id`.
Он должен строить descriptors так:

```text
fields = read fields by object
relations = read relations where source_object_id = object.id OR target_object_id = object.id
```

## 5.3. Важное правило

```text
FieldEntity создается только там, где есть физическая колонка.
```

Значит:

```text
ManyToOne:
- FieldEntity есть на owning/source стороне

OneToOne:
- FieldEntity есть на owning/source стороне

OneToMany:
- FieldEntity есть на owning/target/many стороне

ManyToMany:
- FieldEntity в основных object не создается
- связь описывается RelationEntity + physical relation table
```

---

# 6. Seed schema

## 6.1. Новый RelationSeed contract

Текущий `RelationSeed` слишком узкий:

```text
name
relation_type
source_field
target_object
target_field
on_delete
```

Он подходит для legacy `many_to_one` и `one_to_one`, но не подходит для `one_to_many` и `many_to_many`.

Новый contract:

```python
from dataclasses import dataclass
from typing import Literal

RelationTypeValue = Literal[
    "many_to_one",
    "one_to_one",
    "one_to_many",
    "many_to_many",
]

RelationKindValue = Literal[
    "system",
    "standard",
    "custom",
]

RelationOnDeleteValue = Literal[
    "restrict",
    "cascade",
    "set_null",
    "no_action",
]


@dataclass(frozen=True)
class RelationSeed:
    name: str
    relation_type: RelationTypeValue

    # Logical/API direction.
    # For one_to_many:
    #   source_object = parent/one side
    #   target_object = child/many side
    source_object: str | None = None
    target_object: str | None = None

    # Physical FK side for one_to_one / many_to_one / one_to_many.
    owning_object: str | None = None
    fk_field: str | None = None

    # Referenced side for physical FK.
    referenced_object: str | None = None
    referenced_field: str = "id"

    # API relation names.
    source_relation_name: str | None = None
    target_relation_name: str | None = None

    # Many-to-many physical table.
    relation_table_name: str | None = None
    source_join_column_name: str | None = None
    target_join_column_name: str | None = None

    on_delete: RelationOnDeleteValue = "restrict"
    is_required: bool = False
    kind: RelationKindValue = "standard"

    settings: dict | None = None

    # Legacy compatibility.
    source_field: str | None = None
    target_field: str | None = None
```

## 6.2. Legacy compatibility mapping

Старый формат:

```python
RelationSeed(
    name="contact_company",
    relation_type="many_to_one",
    source_field="company_id",
    target_object="companies",
    target_field="id",
    on_delete="set_null",
)
```

Нормализация:

```text
source_object = current_object_from_seed_context
target_object = target_object

owning_object = current_object_from_seed_context
fk_field = source_field

referenced_object = target_object
referenced_field = target_field or "id"

source_relation_name = target_object singular name by default
target_relation_name = current object plural name by default
```

Legacy `on_delete` значения должны нормализоваться:

```text
"set null" -> "set_null"
"no action" -> "no_action"
```

Это сохраняет текущие seed relations без массовой правки seed в PR-1.

## 6.3. Пример OneToOne

```python
RelationSeed(
    name="contact_profile",
    relation_type="one_to_one",

    source_object="contacts",
    target_object="contact_profiles",

    owning_object="contacts",
    fk_field="profile_id",

    referenced_object="contact_profiles",
    referenced_field="id",

    source_relation_name="profile",
    target_relation_name="contact",

    is_required=False,
    on_delete="set_null",
)
```

Физический результат:

```text
contacts.profile_id uuid
FK contacts.profile_id -> contact_profiles.id
UNIQUE contacts.profile_id
```

## 6.4. Пример OneToMany

```python
RelationSeed(
    name="company_contacts",
    relation_type="one_to_many",

    source_object="companies",
    target_object="contacts",

    owning_object="contacts",
    fk_field="company_id",

    referenced_object="companies",
    referenced_field="id",

    source_relation_name="contacts",
    target_relation_name="company",

    is_required=False,
    on_delete="set_null",
)
```

Физический результат:

```text
contacts.company_id uuid
FK contacts.company_id -> companies.id
```

В API:

```text
company.contacts = virtual relation
contact.company = physical FK relation
```

## 6.5. Пример ManyToMany

```python
RelationSeed(
    name="contact_tags",
    relation_type="many_to_many",

    source_object="contacts",
    target_object="tags",

    relation_table_name="contacts_tags",
    source_join_column_name="contact_id",
    target_join_column_name="tag_id",

    source_relation_name="tags",
    target_relation_name="contacts",

    on_delete="cascade",
)
```

Физический результат:

```sql
CREATE TABLE tenant_schema.contacts_tags
(
    id         uuid PRIMARY KEY,
    contact_id uuid NOT NULL,
    tag_id     uuid NOT NULL,
    created_at timestamptz NOT NULL,

    CONSTRAINT uq_contacts_tags_contact_id_tag_id
        UNIQUE (contact_id, tag_id)
);
```

## 6.6. Canonical direction

Самое важное правило: `source_object` и `target_object` описывают logical/API direction, а `owning_object/fk_field`
описывают physical FK side.

### many_to_one

Пример:

```text
contacts.company_id -> companies.id
```

```text
source_object = contacts
target_object = companies

owning_object = contacts
fk_field = company_id

referenced_object = companies
referenced_field = id

source_relation_name = company
target_relation_name = contacts
```

Metadata:

```text
relation_type = many_to_one
source_object_id = contacts
target_object_id = companies
owning_object_id = contacts
fk_field_id = contacts.company_id
referenced_object_id = companies
referenced_field_id = companies.id
```

### one_to_one

Пример:

```text
contacts.profile_id -> contact_profiles.id
```

```text
source_object = contacts
target_object = contact_profiles

owning_object = contacts
fk_field = profile_id

referenced_object = contact_profiles
referenced_field = id

is_unique = true
```

Metadata:

```text
relation_type = one_to_one
source_object_id = contacts
target_object_id = contact_profiles
owning_object_id = contacts
fk_field_id = contacts.profile_id
referenced_object_id = contact_profiles
referenced_field_id = contact_profiles.id
is_unique = true
```

### one_to_many

Пример:

```text
companies -> contacts[]
contacts.company_id -> companies.id
```

```text
source_object = companies
target_object = contacts

owning_object = contacts
fk_field = company_id

referenced_object = companies
referenced_field = id

source_relation_name = contacts
target_relation_name = company
```

Metadata:

```text
relation_type = one_to_many
source_object_id = companies
target_object_id = contacts
owning_object_id = contacts
fk_field_id = contacts.company_id
referenced_object_id = companies
referenced_field_id = companies.id
```

Важно:

```text
На стороне source_object = companies физическое поле не создается.
```

### many_to_many

Пример:

```text
contacts <-> tags
contacts_tags(contact_id, tag_id)
```

```text
source_object = contacts
target_object = tags

owning_object = null
fk_field = null

relation_table_name = contacts_tags
source_join_column_name = contact_id
target_join_column_name = tag_id
```

Metadata:

```text
relation_type = many_to_many
source_object_id = contacts
target_object_id = tags
owning_object_id = null
fk_field_id = null
referenced_object_id = null
referenced_field_id = null
relation_table_name = contacts_tags
source_join_column_name = contact_id
target_join_column_name = tag_id
```

---

# 7. Migration operations

Добавить операции:

```text
CreateForeignKeyOperation
DropForeignKeyOperation

CreateUniqueIndexOperation
DropUniqueIndexOperation

CreateRelationTableOperation
DropRelationTableOperation

CreateRelationMetadataOperation
DeleteRelationMetadataOperation
```

Дополнительно стоит добавить:

```text
CreateIndexOperation
DropIndexOperation
AddColumnOperation
DropColumnOperation
```

Если они уже есть — переиспользовать.

---

# 8. Planning rules

PR-1 scope:

```text
- CreateRelationMetadataOperation для seed/backfill
- без DDL изменений tenant schemas
- без изменений fields
```

Полные DDL planning rules нужны для следующих PR.

## 8.1. ManyToOne

План для create schema/bootstrap:

```text
1. AddColumnOperation на owning/source object, если колонки еще нет
2. CreateForeignKeyOperation
3. CreateIndexOperation на FK column
4. CreateRelationMetadataOperation
```

Пример:

```text
contacts.company_id uuid null
fk_contacts_company_id_companies
idx_contacts_company_id
```

Правила:

```text
relation.owning_object_id = contacts
relation.fk_field_id = contacts.company_id
relation.referenced_object_id = companies
relation.referenced_field_id = companies.id
relation.is_unique = false
```

## 8.2. OneToOne

План:

```text
1. AddColumnOperation
2. CreateForeignKeyOperation
3. CreateUniqueIndexOperation
4. CreateRelationMetadataOperation
```

Пример:

```text
contacts.profile_id uuid null
fk_contacts_profile_id_contact_profiles
uq_contacts_profile_id
```

Правила:

```text
relation.owning_object_id = contacts
relation.fk_field_id = contacts.profile_id
relation.referenced_object_id = contact_profiles
relation.referenced_field_id = contact_profiles.id
relation.is_unique = true
field.is_nullable = not relation.is_required
```

## 8.3. OneToMany

План:

```text
1. AddColumnOperation на target/many object
2. CreateForeignKeyOperation
3. CreateIndexOperation на FK column
4. CreateRelationMetadataOperation
```

Пример:

```text
companies -> contacts[]

contacts.company_id uuid null
fk_contacts_company_id_companies
```

Важно:

```text
На стороне companies не создается физическая колонка.
relation.owning_object_id = contacts
relation.fk_field_id = contacts.company_id
relation.referenced_object_id = companies
relation.referenced_field_id = companies.id
```

## 8.4. ManyToMany

План:

```text
1. CreateRelationTableOperation
2. CreateForeignKeyOperation left
3. CreateForeignKeyOperation right
4. CreateUniqueIndexOperation на pair
5. CreateIndexOperation left_id
6. CreateIndexOperation right_id
7. CreateRelationMetadataOperation
```

Пример:

```text
contacts_tags
- id
- contact_id
- tag_id
- created_at
```

---

# 9. Naming convention

## 9.1. FK

```text
fk_{source_table}_{source_column}_{target_table}
```

Пример:

```text
fk_contacts_company_id_companies
```

## 9.2. Unique index

Decision:

```text
Переходить сразу на uq_{table}_{column}.
```

```text
uq_{table}_{column}
```

Пример:

```text
uq_contacts_profile_id
```

## 9.3. M2M table

```text
rel_{source_table}_{target_table}
```

или из seed:

```text
contacts_tags
```

Рекомендация:

```text
Для custom relations лучше использовать rel_ prefix.
Для standard seed relations можно задавать явное имя.
```

## 9.4. M2M columns

```text
{source_singular_name}_id
{target_singular_name}_id
```

Пример:

```text
contact_id
tag_id
```

## 9.5. M2M unique

```text
uq_{relation_table}_{left_column}_{right_column}
```

Пример:

```text
uq_contacts_tags_contact_id_tag_id
```

---

# 10. Config API

Добавить endpoints:

```text
POST /api/config/objects/relations/create
DELETE /api/config/objects/relations/delete
POST /api/config/objects/relations/list
POST /api/config/objects/relations/schema
```

## 10.1. Create relation request

```json
{
  "source_object_name": "companies",
  "target_object_name": "contacts",
  "relation_type": "one_to_many",
  "name": "company_contacts",
  "label": "Company Contacts",
  "source_relation_name": "contacts",
  "target_relation_name": "company",
  "owning_object_name": "contacts",
  "fk_field": "company_id",
  "referenced_object_name": "companies",
  "referenced_field": "id",
  "required": false,
  "on_delete": "set_null"
}
```

Для `many_to_many`:

```json
{
  "source_object_name": "contacts",
  "target_object_name": "tags",
  "relation_type": "many_to_many",
  "name": "contact_tags",
  "label": "Contact Tags",
  "source_relation_name": "tags",
  "target_relation_name": "contacts",
  "relation_table_name": "contacts_tags",
  "on_delete": "cascade"
}
```

## 10.2. Delete relation request

```json
{
  "relation_id": "..."
}
```

или:

```json
{
  "source_object_name": "contacts",
  "relation_name": "tags"
}
```

Для надежности лучше использовать `relation_id`.

## 10.3. List relations request

```json
{
  "object_name": "contacts",
  "include_reverse": true
}
```

Ответ:

```json
{
  "items": [
    {
      "id": "...",
      "name": "company_contacts",
      "relation_type": "one_to_many",
      "source_object": "companies",
      "target_object": "contacts",
      "source_relation_name": "contacts",
      "target_relation_name": "company",
      "owning_object": "contacts",
      "fk_field": "company_id",
      "referenced_object": "companies",
      "referenced_field": "id",
      "is_virtual": false
    }
  ]
}
```

## 10.4. Schema response

`POST /api/config/objects/relations/schema`

Должен вернуть описание связи для UI:

```json
{
  "relation": {
    "id": "...",
    "name": "company_contacts",
    "type": "one_to_many"
  },
  "source": {
    "object": "companies",
    "relation_name": "contacts",
    "is_virtual": true
  },
  "target": {
    "object": "contacts",
    "relation_name": "company",
    "fk_field": "company_id",
    "is_virtual": false
  }
}
```

---

# 11. Ограничения

## 11.1. SYSTEM / VIEW

```text
- read-only
- нельзя создавать физические связи
- можно показывать существующие standard/system relations
```

## 11.2. STANDARD

```text
- можно добавлять custom relations
- нельзя удалять standard/system relations
- нельзя менять seed-owned relation
```

## 11.3. CUSTOM

```text
- можно создавать custom relations
- можно удалять custom relations
- можно удалять custom relation вместе с physical DDL
```

---

# 12. Application layer

## 12.1. UseCases

```text
CreateRelationUseCase
DeleteRelationUseCase
ListObjectRelationsUseCase
GetObjectRelationSchemaUseCase
```

Дополнительно:

```text
ValidateRelationUseCase
RebuildRelationMetadataUseCase
```

## 12.2. CreateRelationUseCase flow

```text
1. Принять command
2. Загрузить source object
3. Загрузить target object
4. Проверить права изменения по kind
5. Проверить уникальность relation.name
6. Проверить уникальность relation names внутри object schema
7. Проверить fk_field, если relation требует физическое FK-поле
8. Построить RelationEntity
9. Построить FieldEntity, если нужна новая physical column и это не PR-1
10. Построить MigrationPlan
11. Применить DDL
12. Сохранить FieldEntity
13. Сохранить RelationEntity
14. Commit через текущий UoW
```

## 12.3. DeleteRelationUseCase flow

```text
1. Загрузить RelationEntity
2. Проверить kind
3. Запретить удаление SYSTEM/STANDARD
4. Проверить runtime data impact
5. Построить Drop plan
6. Применить DDL
7. Удалить RelationEntity
8. Удалить/обновить FieldEntity, если FK-поле было создано этой relation
9. Commit
```

В MVP можно сделать жесткое правило:

```text
Удаление relation разрешено только если:
- relation.kind = custom
- FK column или relation table созданы этой relation
```

## 12.4. Добавление required FK на непустую таблицу

Запретить в MVP:

```sql
ALTER TABLE contacts
    ADD COLUMN company_id uuid NOT NULL;
```

если таблица уже содержит строки.

Безопасный flow позже:

```text
1. add nullable column
2. backfill
3. validate no nulls
4. set not null
```

Для MVP:

```text
required=True разрешен только при create schema/bootstrap
required=True запрещен через config API на существующей таблице
```

## 12.5. Удаление relation с данными

Для FK-based relations:

```text
delete relation запрещен, если FK column содержит non-null values
```

Для M2M:

```text
delete relation запрещен, если relation table содержит rows
```

В будущем можно добавить:

```text
force=true
drop_data=true
```

Но не в MVP.

---

# 13. Validation rules

## 13.1. Общие правила

```text
relation.name уникален внутри tenant + datasource
```

```text
source_relation_name уникален внутри source object
target_relation_name уникален внутри target object
```

```text
Нельзя создавать связь с VIEW как physical target/source в MVP
```

## 13.2. Self-relation

Self-relation нельзя запрещать полностью.
Текущий seed уже использует self-reference для `product_category.parent_category_id`, поэтому правило
`source_object != target_object` нельзя применять глобально.

MVP rule:

```text
Разрешить self-relation для FK-based связей:
- many_to_one
- one_to_one
- one_to_many

Запретить в MVP:
- many_to_many self-relation
```

То есть:

```text
product_categories.parent_category_id -> product_categories.id
валидно.
```

Validation:

```python
if relation.source_object == relation.target_object:
    if relation.relation_type == "many_to_many":
        raise UnsupportedSelfManyToManyRelationError()
```

## 13.3. Validator changes

Сейчас validator требует `source_field` для любой relation. Это нужно заменить на type-specific validation.

### many_to_one

Обязательно:

```text
source_object/current object
target_object
fk_field или legacy source_field
referenced_field или legacy target_field
```

### one_to_one

Обязательно:

```text
source_object/current object
target_object
fk_field или legacy source_field
referenced_field или legacy target_field
```

Дополнительно:

```text
is_unique = true
```

### one_to_many

Обязательно:

```text
source_object
target_object
owning_object = target_object
fk_field
referenced_object = source_object
referenced_field = id
source_field не требуется
```

### many_to_many

Обязательно:

```text
source_object
target_object
relation_table_name или возможность сгенерировать имя
source_join_column_name или возможность сгенерировать имя
target_join_column_name или возможность сгенерировать имя
source_field не требуется
```

---

# 14. Runtime data behavior

После добавления связей `runtime_data` должен читать metadata relations из `schema_registry`.

PR-1 boundary:

```text
Resolver должен вернуть нормальную форму relation descriptors,
но runtime loading behavior в PR-1 не реализуется.
```

## 14.1. Object schema response

```json
{
  "object": {
    "name": "contacts",
    "plural_name": "contacts",
    "singular_name": "contact"
  },
  "fields": [
    {
      "name": "company_id",
      "type": "uuid",
      "is_nullable": true
    }
  ],
  "relations": [
    {
      "id": "...",
      "name": "contact_company",
      "relation_type": "many_to_one",
      "source_object": "contacts",
      "target_object": "companies",
      "source_relation_name": "company",
      "target_relation_name": "contacts",
      "owning_object": "contacts",
      "fk_field": "company_id",
      "referenced_object": "companies",
      "referenced_field": "id",
      "is_collection": false,
      "is_virtual": false,
      "is_unique": false
    }
  ]
}
```

## 14.2. OneToMany descriptor

```json
{
  "name": "company_contacts",
  "relation_type": "one_to_many",
  "source_object": "companies",
  "target_object": "contacts",
  "source_relation_name": "contacts",
  "target_relation_name": "company",
  "owning_object": "contacts",
  "fk_field": "company_id",
  "referenced_object": "companies",
  "referenced_field": "id",
  "is_collection": true,
  "is_virtual": true
}
```

`is_virtual=true` означает:

```text
На текущем объекте нет физической колонки.
```

## 14.3. ManyToMany descriptor

```json
{
  "name": "contact_tags",
  "relation_type": "many_to_many",
  "source_object": "contacts",
  "target_object": "tags",
  "source_relation_name": "tags",
  "target_relation_name": "contacts",
  "relation_table_name": "contacts_tags",
  "source_join_column_name": "contact_id",
  "target_join_column_name": "tag_id",
  "is_collection": true,
  "is_virtual": true
}
```

## 14.4. Future runtime behavior

Следующие пункты не входят в PR-1, но остаются целевым поведением runtime layer.

## 14.5. OneToOne

Должен уметь:

```text
- join по FK
- set related record
- unset related record
- enforce unique через DB unique index
```

Пример:

```sql
SELECT c.*, p.*
FROM tenant.contacts c
         LEFT JOIN tenant.contact_profiles p
                   ON p.id = c.profile_id
WHERE c.id = :contact_id;
```

## 14.6. OneToMany

Должен уметь:

```text
- получить children по FK
- присвоить child parent-объекту
- отвязать child от parent
- агрегировать children
```

Пример:

```sql
SELECT *
FROM tenant.contacts
WHERE company_id = :company_id;
```

## 14.7. ManyToMany

Должен уметь:

```text
- читать связанные записи через relation table
- attach relation
- detach relation
- list relation rows
```

Пример attach:

```sql
INSERT INTO tenant.contacts_tags (id,
                                  contact_id,
                                  tag_id,
                                  created_at)
VALUES (gen_random_uuid(),
        :contact_id,
        :tag_id,
        now()) ON CONFLICT (contact_id, tag_id) DO NOTHING;
```

Пример detach:

```sql
DELETE
FROM tenant.contacts_tags
WHERE contact_id = :contact_id
  AND tag_id = :tag_id;
```

---

# 15. Runtime use cases

Добавить в `runtime_data`:

```text
GetRelatedRecordUseCase
ListRelatedRecordsUseCase
AttachRelatedRecordUseCase
DetachRelatedRecordUseCase
SetRelationUseCase
UnsetRelationUseCase
```

## 15.1. Mapping по типам

```text
OneToOne:
- SetRelationUseCase
- UnsetRelationUseCase
- GetRelatedRecordUseCase

OneToMany:
- ListRelatedRecordsUseCase
- SetRelationUseCase для child -> parent
- UnsetRelationUseCase

ManyToMany:
- AttachRelatedRecordUseCase
- DetachRelatedRecordUseCase
- ListRelatedRecordsUseCase
```

---

# 16. Diff behavior

Текущий diff сохраняет custom object metadata и custom physical tables, которых нет в seed.
То же правило нужно применить к relations.

## 16.1. Seed relation added

PR-1:

```text
- создать missing RelationEntity metadata
- не менять physical tenant schema
```

Следующие PR:

```text
- создать FK / unique / relation table
- сохранить metadata
```

## 16.2. Seed relation removed

```text
- standard relation можно удалить или пометить deprecated
- custom relation не трогать
```

Для безопасности лучше в MVP:

```text
seed diff не удаляет physical relation автоматически
seed diff не удаляет RelationEntity metadata автоматически
```

## 16.3. Custom relation

```text
custom relation сохраняется при diff
```

## 16.4. Rename

Текущий diff не пытается эвристически угадывать rename.
Для relations сохранить такое же правило:

```text
rename не inferred
новое имя = новая relation
старое имя = missing relation
```

---

# 17. PostgreSQL DDL examples

## 17.1. OneToOne

```sql
ALTER TABLE tenant_schema.contacts
    ADD COLUMN profile_id uuid NULL;

ALTER TABLE tenant_schema.contacts
    ADD CONSTRAINT fk_contacts_profile_id_contact_profiles
        FOREIGN KEY (profile_id)
            REFERENCES tenant_schema.contact_profiles (id)
            ON DELETE SET NULL;

CREATE UNIQUE INDEX uq_contacts_profile_id
    ON tenant_schema.contacts (profile_id) WHERE profile_id IS NOT NULL;
```

Лучше использовать partial unique index, если поле nullable.

## 17.2. OneToMany

```sql
ALTER TABLE tenant_schema.contacts
    ADD COLUMN company_id uuid NULL;

ALTER TABLE tenant_schema.contacts
    ADD CONSTRAINT fk_contacts_company_id_companies
        FOREIGN KEY (company_id)
            REFERENCES tenant_schema.companies (id)
            ON DELETE SET NULL;

CREATE INDEX idx_contacts_company_id
    ON tenant_schema.contacts (company_id);
```

## 17.3. ManyToMany

```sql
CREATE TABLE tenant_schema.contacts_tags
(
    id         uuid PRIMARY KEY     DEFAULT gen_random_uuid(),
    contact_id uuid        NOT NULL,
    tag_id     uuid        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_contacts_tags_contact_id_contacts
        FOREIGN KEY (contact_id)
            REFERENCES tenant_schema.contacts (id)
            ON DELETE CASCADE,

    CONSTRAINT fk_contacts_tags_tag_id_tags
        FOREIGN KEY (tag_id)
            REFERENCES tenant_schema.tags (id)
            ON DELETE CASCADE,

    CONSTRAINT uq_contacts_tags_contact_id_tag_id
        UNIQUE (contact_id, tag_id)
);

CREATE INDEX idx_contacts_tags_contact_id
    ON tenant_schema.contacts_tags (contact_id);

CREATE INDEX idx_contacts_tags_tag_id
    ON tenant_schema.contacts_tags (tag_id);
```

---

# 18. Файловая структура

```text
src/modules/schema_registry/
  domain/
    relation/
      entity.py
      enum.py
      exception.py
      repository.py
      value_object.py

  application/
    relation/
      command/
        create_relation_command.py
        delete_relation_command.py
        list_relations_command.py
      dto/
        relation_dto.py
        relation_schema_dto.py
      service/
        relation_validation_service.py
        relation_metadata_read_service.py
        relation_metadata_write_service.py
      use_case/
        create_relation_use_case.py
        delete_relation_use_case.py
        list_object_relations_use_case.py
        get_relation_schema_use_case.py

    migration/
      operation/
        create_foreign_key_operation.py
        drop_foreign_key_operation.py
        create_unique_index_operation.py
        drop_unique_index_operation.py
        create_relation_table_operation.py
        drop_relation_table_operation.py

      postgres_schema_plan_service.py

  infrastructure/
    relation/
      relation_repository.py
      row_mapper.py

  presentation/
    http/
      config/
        relation_router.py
        relation_controller.py
        relation_schema.py
```

---

# 19. Тесты

## 19.1. Domain

```text
- RelationEntity validates many_to_one
- RelationEntity validates one_to_one
- RelationEntity validates one_to_many
- RelationEntity validates many_to_many
- rejects invalid relation type
- rejects missing required type-specific fields
- allows FK-based self-relation
- rejects many_to_many self-relation
```

## 19.2. Application

```text
- create one_to_one relation
- create one_to_many relation
- create many_to_many relation
- reject relation for system/view object
- reject duplicate relation name
- reject duplicate relation field name
- reject required FK on existing non-empty table
- reject delete FK relation with non-null FK values
- reject delete M2M relation with relation table rows
- delete custom relation
- reject delete standard relation
```

## 19.3. Metadata/backfill

```text
- creates relations table without changing fields table
- backfills many_to_one relation from legacy seed
- backfills one_to_one relation from legacy seed
- normalizes legacy source_field/target_field into fk_field/referenced_field
- normalizes legacy on_delete values
- resolver returns relation descriptors
```

## 19.4. Planning

```text
- many_to_one creates add column + FK + index
- one_to_one creates add column + FK + unique
- one_to_many creates add column on many side + FK + index
- many_to_many creates relation table + 2 FK + unique pair + indexes
```

## 19.5. Executor

```text
- executes CreateForeignKeyOperation
- executes DropForeignKeyOperation
- executes CreateUniqueIndexOperation
- executes CreateRelationTableOperation
- executes DropRelationTableOperation
```

## 19.6. Runtime data

```text
- PR-1 does not load relation data
- resolver exposes many_to_one descriptors
- resolver exposes one_to_many virtual descriptors
- resolver exposes many_to_many descriptors
- get one_to_one related record
- list one_to_many children
- attach many_to_many
- detach many_to_many
- prevent duplicate many_to_many pair
```

## 19.7. Diff

```text
- seed relation added
- seed relation preserved
- custom relation preserved
- removed seed relation not dropped automatically in MVP
- physical FK/index/relation table not dropped automatically in MVP
```

---

# 20. Порядок реализации

## Этап 1 — Relation metadata

```text
1. Добавить RelationEntity
2. Добавить enum/value objects
3. Добавить metadata table relations
4. Добавить RelationRepository
5. Добавить row mapper
6. Добавить PR-1 backfill из текущего seed
7. Не менять fields table
8. Не менять physical tenant schemas
```

## Этап 2 — Application services

```text
1. RelationValidationService
2. RelationMetadataReadService
3. RelationMetadataWriteService
4. RelationPlanService
5. Runtime resolver descriptors без relation loading
```

## Этап 3 — Migration operations

```text
1. FK operations
2. Unique index operations
3. Relation table operations
4. PostgreSQL executor support
```

## Этап 4 — OneToOne

```text
1. CreateRelationUseCase for one_to_one
2. DDL plan
3. metadata write
4. config API
5. tests
```

## Этап 5 — OneToMany

```text
1. FK on many side
2. virtual reverse relation in schema response
3. runtime children listing
4. tests
```

## Этап 6 — ManyToMany

```text
1. relation table generation
2. attach/detach runtime operations
3. list related records
4. tests
```

## Этап 7 — Diff integration

```text
1. seed relations
2. metadata comparison
3. physical schema inspection
4. safe diff behavior
```

## Этап 8 — UI/config schema

```text
1. relation list
2. relation schema
3. create relation form schema
4. delete relation
```

---

# 21. Главное правило реализации

```text
FieldEntity — это поле объекта.
RelationEntity — это связь между объектами.
```

Тогда:

```text
ManyToOne:
FieldEntity на owning/source side + RelationEntity

OneToOne:
FieldEntity на owning/source side + RelationEntity

OneToMany:
FieldEntity на owning/target/many side + RelationEntity

ManyToMany:
только RelationEntity + physical relation table
```

Это закрывает главный пробел текущего MVP: связи перестают быть побочным эффектом `Field.settings` и становятся
полноценной частью metadata graph.
