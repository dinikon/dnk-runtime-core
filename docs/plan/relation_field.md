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

    source_field_id: RuntimeFieldIdVO | None
    target_field_id: RuntimeFieldIdVO | None

    source_relation_name: str | None
    target_relation_name: str | None

    relation_name: str | None

    on_delete: RelationOnDelete
    is_required: bool
    is_unique: bool

    kind: RelationKind
    settings: dict

    created_at: datetime
    updated_at: datetime
```

## 3.2. RelationType

```python
class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"
```

Даже если публично нужны только:

```text
OneToOne
OneToMany
ManyToMany
```

внутри лучше оставить `MANY_TO_ONE`, потому что физически `OneToMany` реализуется как FK на стороне many.

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
Нужно добавить таблицу relations.

## 4.1. `relations`

```sql
CREATE TABLE relations
(
    id                   uuid PRIMARY KEY,
    tenant_id            uuid        NOT NULL,
    data_source_id       uuid        NOT NULL,

    name                 text        NOT NULL,
    label                text,

    relation_type        text        NOT NULL,

    relation_name        text NULL,

    source_object_id     uuid        NOT NULL,
    target_object_id     uuid        NOT NULL,

    source_field_id      uuid NULL,
    target_field_id      uuid NULL,

    source_relation_name text NULL,
    target_relation_name text NULL,

    on_delete            text        NOT NULL DEFAULT 'restrict',
    is_required          boolean     NOT NULL DEFAULT false,
    is_unique            boolean     NOT NULL DEFAULT false,

    kind                 text        NOT NULL DEFAULT 'custom',
    settings             jsonb       NOT NULL DEFAULT '{}'::jsonb,

    created_at           timestamptz NOT NULL,
    updated_at           timestamptz NOT NULL,

    CONSTRAINT uq_schema_registry_relations_name
        UNIQUE (tenant_id, data_source_id, name)
);
```

## 4.2. FK metadata constraints

```sql
ALTER TABLE schema_registry_relations
    ADD CONSTRAINT fk_relations_source_object
        FOREIGN KEY (source_object_id)
            REFERENCES schema_registry_objects (id);

ALTER TABLE schema_registry_relations
    ADD CONSTRAINT fk_relations_target_object
        FOREIGN KEY (target_object_id)
            REFERENCES schema_registry_objects (id);

ALTER TABLE schema_registry_relations
    ADD CONSTRAINT fk_relations_source_field
        FOREIGN KEY (source_field_id)
            REFERENCES schema_registry_fields (id);

ALTER TABLE schema_registry_relations
    ADD CONSTRAINT fk_relations_target_field
        FOREIGN KEY (target_field_id)
            REFERENCES schema_registry_fields (id);
```

---

# 5. FieldEntity changes

## 5.1. Добавить relation reference

В `FieldEntity` добавить:

```python
relation_id: RuntimeRelationIdVO | None
is_unique: bool
is_indexed: bool
```

Для FK-поля:

```text
field.type = reference
field.relation_id = relation.id
field.settings.target_object_id = ...
field.settings.target_field = "id"
```

## 5.2. Важное правило

```text
FieldEntity создается только там, где есть физическая колонка.
```

Значит:

```text
OneToOne:
- FieldEntity есть на owning/source стороне

OneToMany:
- FieldEntity есть на many/target стороне

ManyToMany:
- FieldEntity в основных object не создается
- связь описывается только RelationEntity
```

---

# 6. Seed schema

Добавить в seed поддержку `relations`.

## 6.1. Пример OneToOne

```python
RelationSpec(
    name="contact_profile",
    label="Contact Profile",
    relation_type="one_to_one",

    source_object="contacts",
    target_object="contact_profiles",

    source_field_name="profile_id",
    target_field_name="id",

    source_relation_name="profile",
    target_relation_name="contact",

    required=False,
    on_delete="set_null",
)
```

Физический результат:

```text
contacts.profile_id uuid
FK contacts.profile_id -> contact_profiles.id
UNIQUE contacts.profile_id
```

## 6.2. Пример OneToMany

```python
RelationSpec(
    name="company_contacts",
    label="Company Contacts",
    relation_type="one_to_many",

    source_object="companies",
    target_object="contacts",

    target_field_name="company_id",

    source_relation_name="contacts",
    target_relation_name="company",

    required=False,
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

## 6.3. Пример ManyToMany

```python
RelationSpec(
    name="contact_tags",
    label="Contact Tags",
    relation_type="many_to_many",

    source_object="contacts",
    target_object="tags",

    relation_name="contacts_tags",

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
    contact_id uuid        NOT NULL,
    tag_id     uuid        NOT NULL,
    created_at timestamptz NOT NULL,

    CONSTRAINT uq_contacts_tags_contact_id_tag_id
        UNIQUE (contact_id, tag_id)
);
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

## 8.1. OneToOne

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
source_field.is_unique = true
source_field.is_required = relation.required
source_field.relation_id = relation.id
```

## 8.2. OneToMany

План:

```text
1. AddColumnOperation на target/many object
2. CreateForeignKeyOperation
3. CreateRelationMetadataOperation
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
```

## 8.3. ManyToMany

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
  "field_name": "company_id",
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
  "relation_name": "contacts_tags",
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
      "physical_field": "company_id",
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
    "field_name": "company_id",
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
7. Проверить field_name, если relation требует физическое FK-поле
8. Построить RelationEntity
9. Построить FieldEntity, если нужна physical column
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

---

# 13. Validation rules

## 13.1. Общие правила

```text
source_object != target_object
```

Для self-relation можно добавить позже.

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

## 13.2. OneToOne

```text
source_field_name обязателен
source_field_name не должен существовать
source_field получает is_unique = true
```

## 13.3. OneToMany

```text
target_field_name обязателен
target_field_name не должен существовать
FK создается на target side
source side virtual
```

## 13.4. ManyToMany

```text
relation_name обязателен или генерируется
relation_name не должен существовать
source_field_name и target_field_name не создаются в object fields
unique pair обязателен
```

---

# 14. Runtime data behavior

После добавления связей `runtime_data` должен читать metadata relations из `schema_registry`.

## 14.1. OneToOne

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

## 14.2. OneToMany

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

## 14.3. ManyToMany

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

```text
- создать missing relation
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
- RelationEntity validates one_to_one
- RelationEntity validates one_to_many
- RelationEntity validates many_to_many
- rejects invalid relation type
- rejects missing required field names
```

## 19.2. Application

```text
- create one_to_one relation
- create one_to_many relation
- create many_to_many relation
- reject relation for system/view object
- reject duplicate relation name
- reject duplicate relation field name
- delete custom relation
- reject delete standard relation
```

## 19.3. Planning

```text
- one_to_one creates add column + FK + unique
- one_to_many creates add column on many side + FK + index
- many_to_many creates relation table + 2 FK + unique pair + indexes
```

## 19.4. Executor

```text
- executes CreateForeignKeyOperation
- executes DropForeignKeyOperation
- executes CreateUniqueIndexOperation
- executes CreateRelationTableOperation
- executes DropRelationTableOperation
```

## 19.5. Runtime data

```text
- get one_to_one related record
- list one_to_many children
- attach many_to_many
- detach many_to_many
- prevent duplicate many_to_many pair
```

## 19.6. Diff

```text
- seed relation added
- seed relation preserved
- custom relation preserved
- removed seed relation not dropped automatically in MVP
```

---

# 20. Порядок реализации

## Этап 1 — Relation metadata

```text
1. Добавить RelationEntity
2. Добавить enum/value objects
3. Добавить metadata table
4. Добавить RelationRepository
5. Добавить row mapper
```

## Этап 2 — Application services

```text
1. RelationValidationService
2. RelationMetadataReadService
3. RelationMetadataWriteService
4. RelationPlanService
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
OneToOne:
FieldEntity + RelationEntity

OneToMany:
FieldEntity на many side + RelationEntity

ManyToMany:
только RelationEntity + physical relation table
```

Это закрывает главный пробел текущего MVP: связи перестают быть побочным эффектом `Field.settings` и становятся
полноценной частью metadata graph.
