# План реализации модуля жизненного цикла сегментов для рассылок и коммуникаций

## 1. Назначение модуля

### 1.1. Цель

`segment` — tenant-scoped модуль для создания, хранения, валидации и расчета правил выбора коммуникационной аудитории.

Главная задача модуля:

```text
source objects + filters -> target audience subjects
```

Segment отвечает за выбор **кого включить в аудиторию**, но не отвечает за выбор `PHONE`, `EMAIL`, `Viber`, `SMS`,
`primary`, `last active` и другие правила конкретной отправки.

Выбор конкретного `ContactPoint` выполняет `broadcast` в контексте конкретной рассылки.

---

### 1.2. Границы ответственности

`segment` отвечает за:

* создание сегментов;
* хранение static/dynamic segment definitions;
* выбор target object сегмента;
* проверку, что target object может быть использован как коммуникационная аудитория;
* хранение include/exclude DSL;
* проверку source object filters;
* проверку resolution path от source object к target object;
* проверку ссылок на другие сегменты;
* preview количества аудитории;
* расчет target audience subjects;
* snapshot результата расчета;
* дедупликацию target subjects;
* жизненный цикл сегмента: draft, active, paused, invalid, archived.

---

### 1.3. Что не входит в модуль

`segment` не отвечает за:

* выбор `PHONE` или `EMAIL`;
* выбор `is_primary`, `last active`, `all active`;
* выбор provider;
* выбор message template;
* отправку сообщений;
* throttling, batches, retries;
* delivery status;
* webhook processing;
* campaign orchestration;
* workflow execution;
* создание ContactPoint;
* нормализацию телефона/email;
* хранение provider-specific recipient payload.

Эти ответственности распределяются так:

| Задача                                                     | Модуль                        |
|------------------------------------------------------------|-------------------------------|
| Выбрать аудиторию                                          | `segment`                     |
| Получить phone/email/contact point для конкретной рассылки | `broadcast` + `contact_point` |
| Отправить сообщение                                        | `communication`               |
| Управлять бизнес-сценарием                                 | `campaign` / `workflow`       |

---

## 2. Термины и доменные понятия

| Термин                           | Описание                                                          | Примечание                                               |
|----------------------------------|-------------------------------------------------------------------|----------------------------------------------------------|
| Segment                          | Сохраненное правило или фиксированный список выбора аудитории     | Основной aggregate                                       |
| Static Segment                   | Фиксированный список target subjects                              | Например, список Contact или Company                     |
| Dynamic Segment                  | DSL-правило выбора target subjects                                | Include/exclude blocks                                   |
| Target Object                    | Итоговый объект, который возвращает сегмент                       | Например `contact`, `company`, `lead`, `job_application` |
| Source Object                    | Объект, по которому выполняется фильтр                            | Например `deal`, `loan_request`, `lead`                  |
| AudienceSubject                  | Нормализованный результат сегмента                                | `target_object_id + target_record_id`                    |
| Resolution Path                  | Путь от source object к target object                             | Например `deal.contact_id -> contact.id`                 |
| Include Block                    | Правила включения в сегмент                                       | Формирует базовую аудиторию                              |
| Exclude Block                    | Правила исключения из сегмента                                    | Имеет приоритет над include                              |
| Segment Reference                | Ссылка на другой сегмент                                          | Для MVP только сегменты с тем же target object           |
| Segment Calculation              | Факт расчета сегмента                                             | Может быть preview или snapshot                          |
| Segment Snapshot                 | Сохраненный результат расчета                                     | Используется Broadcast/Campaign                          |
| Communication Addressable Target | Target object, из которого Broadcast сможет получить ContactPoint | Напрямую или через relation path                         |
| ContactPoint Resolution          | Процесс выбора phone/email/contact_point                          | Не входит в Segment, выполняется Broadcast               |

---

## 3. Основные сценарии

### 3.1. Создание сегмента

Пользователь создает сегмент и указывает:

* название;
* описание;
* тип сегмента: `STATIC` или `DYNAMIC`;
* target object;
* для dynamic segment — include/exclude definition;
* для static segment — список target records.

Пример:

```text
Segment: Клиенты с заявкой сегодня
Type: DYNAMIC
Target Object: contact
```

Include rule:

```text
source_object = loan_request
filter = created_at = current_date
resolution_path = contact_id
```

Результат:

```text
contact_id[]
```

---

### 3.2. Изменение сегмента

Пользователь может изменить:

* название;
* описание;
* include rules;
* exclude rules;
* static members;
* segment status.

При изменении dynamic definition увеличивается `definition_version`.

Если active segment изменен, система должна:

1. перевести его в `DRAFT` или оставить `ACTIVE`, но пометить `requires_validation=true`;
2. сбросить `last_validated_at`;
3. потребовать повторной валидации перед использованием в Broadcast.

Рекомендуемый MVP-вариант:

```text
ACTIVE segment после изменения definition становится DRAFT
```

---

### 3.3. Активация сегмента

Перед активацией система должна выполнить validation:

* target object существует;
* target object communication-addressable;
* все source objects существуют;
* все filter DSL валидны;
* все поля фильтров существуют;
* все operators применимы к типам полей;
* все resolution paths существуют;
* все referenced segments существуют;
* referenced segments имеют тот же target object;
* нет циклических segment references;
* include block не пустой для dynamic segment;
* static segment имеет хотя бы одного active member, если это требуется настройкой.

После успешной проверки:

```text
DRAFT -> ACTIVE
```

---

### 3.4. Деактивация сегмента

Деактивация временно запрещает использование сегмента в новых Broadcast/Campaign.

```text
ACTIVE -> PAUSED
```

Уже созданные Broadcast snapshots не меняются.

---

### 3.5. Архивация сегмента

Архивация скрывает сегмент из активного использования.

```text
DRAFT / PAUSED / INVALID -> ARCHIVED
```

`ACTIVE` segment перед архивацией лучше сначала переводить в `PAUSED`, либо разрешить прямой переход:

```text
ACTIVE -> ARCHIVED
```

Но после archive сегмент нельзя использовать в новых рассылках.

---

### 3.6. Пересчет состава сегмента

Пересчет выполняется для dynamic segment.

Режимы:

| Режим    | Описание                                                                         |
|----------|----------------------------------------------------------------------------------|
| Preview  | Быстрый расчет count без сохранения members                                      |
| Snapshot | Полный расчет с сохранением `segment_calculation` и `segment_calculation_member` |

Segment пересчитывает только target subjects.

Он не выбирает ContactPoint.

---

### 3.7. Использование сегмента в рассылке или коммуникации

Flow:

```text
Broadcast получает segment_id
  -> вызывает SegmentSubjectResolverPort
  -> получает target subjects
  -> вызывает ContactPoint resolver
  -> выбирает PHONE/EMAIL по правилам конкретной рассылки
  -> создает broadcast recipient snapshot
  -> передает сообщения в Communication
```

Пример:

Один и тот же segment:

```text
Segment: Клиенты с активным кредитом
Target: contact
```

Можно использовать в разных Broadcast:

```text
SMS Broadcast -> PHONE + LAST_ACTIVE
Email Broadcast -> EMAIL + PRIMARY_ONLY
Viber Broadcast -> PHONE + ALL_ACTIVE
```

---

## 4. Жизненный цикл сегмента

### 4.1. Статусы

| Статус     | Назначение                                                  | Разрешенные переходы                                     |
|------------|-------------------------------------------------------------|----------------------------------------------------------|
| `DRAFT`    | Сегмент создан или изменен, но еще не готов к использованию | `ACTIVE`, `ARCHIVED`                                     |
| `ACTIVE`   | Сегмент валиден и доступен для Broadcast/Campaign           | `PAUSED`, `INVALID`, `ARCHIVED`, `DRAFT` после изменения |
| `PAUSED`   | Сегмент временно отключен                                   | `ACTIVE`, `ARCHIVED`                                     |
| `INVALID`  | Definition больше невалидна                                 | `DRAFT`, `ARCHIVED`                                      |
| `ARCHIVED` | Сегмент закрыт для использования                            | нет переходов в MVP                                      |

---

### 4.2. Переходы между статусами

```text
DRAFT -> ACTIVE
DRAFT -> ARCHIVED

ACTIVE -> PAUSED
ACTIVE -> INVALID
ACTIVE -> ARCHIVED
ACTIVE -> DRAFT

PAUSED -> ACTIVE
PAUSED -> ARCHIVED

INVALID -> DRAFT
INVALID -> ARCHIVED
```

---

### 4.3. Инварианты жизненного цикла

1. `ACTIVE` segment должен иметь валидный target object.

2. `ACTIVE` dynamic segment должен иметь валидный include/exclude definition.

3. `ACTIVE` segment нельзя использовать, если он ссылается на `ARCHIVED` или `INVALID` segment.

4. Segment reference в MVP разрешен только на segment с тем же `target_object_id`.

5. Если source object больше не существует, segment становится `INVALID`.

6. Если relation path больше не существует, segment становится `INVALID`.

7. Если filter field удален или тип поля изменился, segment становится `INVALID`.

8. `ARCHIVED` segment нельзя использовать в новых Broadcast.

9. Старые calculation snapshots не удаляются при изменении segment definition.

10. Изменение dynamic definition увеличивает `definition_version`.

---

## 5. Доменная модель

### 5.1. Aggregates

## `SegmentAggregate`

Главный aggregate root.

Поля:

```text
id
tenant_id
created_at
updated_at

segment_code
name
description

segment_type
status

target_object_id
target_object_name

definition_version
include_definition
exclude_definition

last_validated_at
last_calculated_at
requires_validation
```

Ответственность:

* хранит lifecycle state;
* проверяет разрешенные status transitions;
* фиксирует target object;
* хранит definition version;
* не выполняет runtime query самостоятельно;
* не выбирает ContactPoint.

---

### 5.2. Entities

## `SegmentStaticMemberEntity`

Элемент static segment.

```text
id
segment_id
target_object_id
target_record_id
source
is_active
created_at
updated_at
```

## `SegmentCalculationEntity`

Факт расчета segment.

```text
id
segment_id
definition_version
status
started_at
finished_at
include_count
exclude_count
result_count
error_message
```

## `SegmentCalculationMemberEntity`

Результат snapshot calculation.

```text
id
calculation_id
segment_id

target_object_id
target_record_id

source_object_id
source_record_id
source_rule_id

matched_at
```

---

### 5.3. Value Objects

| Value Object                 | Назначение                                         |
|------------------------------|----------------------------------------------------|
| `SegmentIdVO`                | ID сегмента                                        |
| `SegmentCodeVO`              | Уникальный код сегмента внутри tenant              |
| `SegmentNameVO`              | Название сегмента                                  |
| `SegmentTypeVO`              | `STATIC`, `DYNAMIC`                                |
| `SegmentStatusVO`            | `DRAFT`, `ACTIVE`, `PAUSED`, `INVALID`, `ARCHIVED` |
| `SegmentDefinitionVersionVO` | Версия definition                                  |
| `TargetObjectRefVO`          | `object_id`, `object_name`                         |
| `SourceObjectRefVO`          | `object_id`, `object_name`                         |
| `AudienceSubjectRefVO`       | `target_object_id`, `target_record_id`             |
| `ResolutionPathVO`           | Путь от source к target                            |
| `SegmentRuleIdVO`            | ID правила внутри definition                       |
| `SegmentReferenceVO`         | Ссылка на другой segment                           |
| `SegmentCalculationIdVO`     | ID расчета                                         |

---

### 5.4. Domain Services

## `SegmentLifecycleService`

Проверяет допустимые переходы статусов.

## `SegmentDefinitionPolicy`

Проверяет базовые ограничения definition:

* include block обязателен для dynamic segment;
* conditions count <= 10;
* nesting depth <= 2;
* operators только из разрешенного списка;
* exclude block optional;
* segment references не должны быть циклическими.

## `SegmentSetOperationService`

Выполняет операции над target subject sets:

```text
OR = union
AND = intersection
EXCLUDE = difference
```

## `SegmentTargetPolicy`

Проверяет, может ли target object быть коммуникационной аудиторией.

Target valid, если:

1. object имеет системную или включенную feature `CONTACT_POINT`;
2. или object имеет relation path к объекту, у которого есть `CONTACT_POINT`;
3. или object является стандартным communication subject: `contact`, `company`, `lead`.

---

### 5.5. Domain Events

Для MVP можно не внедрять event bus, но события стоит заложить как domain events:

| Event                           | Когда возникает               |
|---------------------------------|-------------------------------|
| `SegmentCreatedEvent`           | Создан segment                |
| `SegmentDefinitionChangedEvent` | Изменена definition           |
| `SegmentActivatedEvent`         | Segment активирован           |
| `SegmentPausedEvent`            | Segment деактивирован         |
| `SegmentArchivedEvent`          | Segment архивирован           |
| `SegmentInvalidatedEvent`       | Segment стал invalid          |
| `SegmentCalculatedEvent`        | Snapshot calculation завершен |

---

## 6. Application Layer

### 6.1. Commands

| Command                              | Назначение                                        | Результат                       |
|--------------------------------------|---------------------------------------------------|---------------------------------|
| `CreateSegmentCommand`               | Создать segment                                   | `SegmentDTO`                    |
| `UpdateSegmentCommand`               | Изменить name/description/definition              | `SegmentDTO`                    |
| `ActivateSegmentCommand`             | Активировать segment после validation             | `SegmentDTO`                    |
| `PauseSegmentCommand`                | Временно отключить segment                        | `SegmentDTO`                    |
| `ArchiveSegmentCommand`              | Архивировать segment                              | `SegmentDTO`                    |
| `ValidateSegmentCommand`             | Проверить definition                              | `SegmentValidationResultDTO`    |
| `PreviewSegmentCommand`              | Посчитать количество target subjects без snapshot | `SegmentPreviewDTO`             |
| `CalculateSegmentCommand`            | Создать snapshot calculation                      | `SegmentCalculationDTO`         |
| `AddStaticSegmentMembersCommand`     | Добавить target records в static segment          | `StaticSegmentMembersResultDTO` |
| `RemoveStaticSegmentMembersCommand`  | Удалить target records из static segment          | `StaticSegmentMembersResultDTO` |
| `ReplaceStaticSegmentMembersCommand` | Полностью заменить members                        | `StaticSegmentMembersResultDTO` |

---

### 6.2. Queries

| Query                                | Назначение                                   | Результат                         |
|--------------------------------------|----------------------------------------------|-----------------------------------|
| `GetSegmentQuery`                    | Получить segment по id                       | `SegmentDTO`                      |
| `ListSegmentsQuery`                  | Получить список segments                     | `SegmentListDTO`                  |
| `ListStaticSegmentMembersQuery`      | Получить members static segment              | `SegmentMemberListDTO`            |
| `GetSegmentCalculationQuery`         | Получить calculation по id                   | `SegmentCalculationDTO`           |
| `ListSegmentCalculationsQuery`       | История расчетов segment                     | `SegmentCalculationListDTO`       |
| `ListSegmentCalculationMembersQuery` | Получить snapshot members                    | `SegmentCalculationMemberListDTO` |
| `ResolveSegmentSubjectsQuery`        | Получить target subjects для consumer module | `SegmentSubjectListDTO`           |

---

### 6.3. Use Cases

## `CreateSegmentUseCase`

Создает segment в `DRAFT`.

Для dynamic segment:

* сохраняет include/exclude definition;
* выполняет lightweight validation;
* не активирует автоматически.

Для static segment:

* создает пустой segment;
* members добавляются отдельным command.

---

## `UpdateSegmentUseCase`

Изменяет segment.

Если меняется definition:

* увеличивает `definition_version`;
* сбрасывает `last_validated_at`;
* выставляет `requires_validation=true`;
* active segment переводит в `DRAFT`.

---

## `ValidateSegmentUseCase`

Выполняет полную проверку:

1. target object существует;
2. target object communication-addressable;
3. source objects существуют;
4. filter DSL валиден относительно source descriptor;
5. resolution path существует;
6. referenced segments существуют;
7. referenced segments имеют тот же target object;
8. нет циклов segment references.

---

## `ActivateSegmentUseCase`

Выполняет validation и переводит:

```text
DRAFT / PAUSED -> ACTIVE
```

---

## `PauseSegmentUseCase`

Переводит:

```text
ACTIVE -> PAUSED
```

---

## `ArchiveSegmentUseCase`

Переводит segment в `ARCHIVED`.

---

## `PreviewSegmentUseCase`

Выполняет calculation без сохранения members.

Возвращает:

```text
include_count
exclude_count
result_count
```

---

## `CalculateSegmentUseCase`

Создает snapshot calculation:

1. создает `segment_calculation`;
2. выполняет include rules;
3. приводит source rows к target records;
4. выполняет exclude rules;
5. делает set difference;
6. дедуплицирует target subjects;
7. сохраняет `segment_calculation_member`;
8. обновляет `last_calculated_at`.

---

## `ResolveSegmentSubjectsUseCase`

Публичный application boundary для других модулей.

Broadcast вызывает:

```text
segment_id -> target subjects
```

Не возвращает:

```text
phone
email
contact_point_id
recipient_address
```

---

### 6.4. DTO

## `SegmentDTO`

```text
id
created_at
updated_at
segment_code
name
description
segment_type
status
target_object_id
target_object_name
definition_version
include_definition
exclude_definition
last_validated_at
last_calculated_at
requires_validation
```

## `SegmentValidationResultDTO`

```text
is_valid
errors[]
warnings[]
target_object
source_objects[]
```

## `SegmentPreviewDTO`

```text
segment_id
definition_version
include_count
exclude_count
result_count
```

## `AudienceSubjectDTO`

```text
target_object_id
target_object_name
target_record_id
source_object_id
source_object_name
source_record_id
source_rule_id
```

## `SegmentCalculationDTO`

```text
id
segment_id
definition_version
status
started_at
finished_at
include_count
exclude_count
result_count
error_message
```

---

## 7. Infrastructure Layer

### 7.1. Persistence

Рекомендуемый вариант для проекта:

```text
segment хранить как runtime-data module
```

То есть:

* runtime objects описываются в `schema_registry` seed;
* repositories работают через `runtime_data`;
* собственных SQLAlchemy ORM моделей для segment runtime objects не создавать.

---

### 7.2. Repositories

## `SegmentRepositoryProtocol`

```python
class SegmentRepositoryProtocol(Protocol):
    async def load(self, *, tenant_id, segment_id) -> SegmentEntity | None: ...

    async def save(self, *, tenant_id, segment) -> None: ...

    async def list(self, *, tenant_id, limit, offset) -> list[SegmentDTO]: ...
```

## `SegmentStaticMemberRepositoryProtocol`

```python
class SegmentStaticMemberRepositoryProtocol(Protocol):
    async def add_members(...) -> None: ...

    async def remove_members(...) -> None: ...

    async def list_members(...) -> list[AudienceSubjectDTO]: ...
```

## `SegmentCalculationRepositoryProtocol`

```python
class SegmentCalculationRepositoryProtocol(Protocol):
    async def create_calculation(...) -> SegmentCalculationEntity: ...

    async def save_members(...) -> None: ...

    async def get_calculation(...) -> SegmentCalculationDTO | None: ...

    async def list_members(...) -> list[AudienceSubjectDTO]: ...
```

---

### 7.3. Background Jobs

Для MVP можно без background jobs.

Но архитектурно нужно заложить:

* `segment calculate --tenant-id --segment-id`;
* future queue job для больших calculation;
* periodic revalidation active segments;
* cleanup old calculation snapshots.

---

### 7.4. Integrations

## `schema_registry`

Используется для:

* resolve target object descriptor;
* resolve source object descriptor;
* проверка relation graph;
* проверка object features;
* проверка field metadata.

## `runtime_data`

Используется для:

* выполнения source object filters;
* DSL validation;
* pagination/count;
* загрузки source rows;
* runtime query execution.

`runtime_data` уже является техническим модулем для descriptor-backed CRUD/search и typed filter/sort DSL, поэтому
Segment должен переиспользовать его query pipeline, а не создавать отдельный DSL engine.

## `contact_point`

Segment напрямую не выбирает ContactPoint.

Но target object должен быть совместим с последующим ContactPoint resolution. Сам `contact_point` хранит tenant-scoped
контактные точки и binding к runtime owner record.

---

## 8. Presentation Layer

### 8.1. HTTP API

| Method   | Path                                                  | Назначение                   |
|----------|-------------------------------------------------------|------------------------------|
| `POST`   | `/api/segments`                                       | Создать segment              |
| `GET`    | `/api/segments`                                       | Список segments              |
| `GET`    | `/api/segments/{segment_id}`                          | Получить segment             |
| `PUT`    | `/api/segments/{segment_id}`                          | Обновить segment             |
| `POST`   | `/api/segments/{segment_id}/validate`                 | Проверить definition         |
| `POST`   | `/api/segments/{segment_id}/activate`                 | Активировать segment         |
| `POST`   | `/api/segments/{segment_id}/pause`                    | Поставить segment на паузу   |
| `POST`   | `/api/segments/{segment_id}/archive`                  | Архивировать segment         |
| `POST`   | `/api/segments/{segment_id}/preview`                  | Preview count                |
| `POST`   | `/api/segments/{segment_id}/calculate`                | Создать calculation snapshot |
| `GET`    | `/api/segments/{segment_id}/calculations`             | История расчетов             |
| `GET`    | `/api/segments/calculations/{calculation_id}/members` | Members snapshot             |
| `POST`   | `/api/segments/{segment_id}/members`                  | Добавить static members      |
| `DELETE` | `/api/segments/{segment_id}/members`                  | Удалить static members       |
| `GET`    | `/api/segments/{segment_id}/members`                  | Получить static members      |

---

### 8.2. Requests

## `CreateSegmentRequestSchema`

```json
{
  "segment_code": "active_credit_clients",
  "name": "Клиенты с активным кредитом",
  "description": "Клиенты, у которых есть активный кредит",
  "segment_type": "DYNAMIC",
  "target_object_id": "contact-object-id",
  "include_definition": {},
  "exclude_definition": {}
}
```

## `SegmentRuleSchema`

```json
{
  "rule_id": "loan_requests_today",
  "source_object_id": "loan-request-object-id",
  "filter": {
    "operator": "AND",
    "conditions": [
      {
        "field": "created_at",
        "operator": "date_eq",
        "value": "current_date"
      }
    ]
  },
  "resolution": {
    "type": "relation_path",
    "path": "contact_id"
  }
}
```

---

### 8.3. Responses

## `SegmentResponseSchema`

Возвращает `SegmentDTO`.

## `SegmentValidationResponseSchema`

```json
{
  "is_valid": false,
  "errors": [
    {
      "code": "SOURCE_CANNOT_RESOLVE_TO_TARGET",
      "message": "Source object deal cannot be resolved to target object job_application",
      "rule_id": "deals_today"
    }
  ],
  "warnings": []
}
```

## `SegmentPreviewResponseSchema`

```json
{
  "segment_id": "segment-id",
  "definition_version": 3,
  "include_count": 1200,
  "exclude_count": 150,
  "result_count": 1050
}
```

---

### 8.4. Dependencies

Presentation dependencies должны создавать:

* `SegmentRuntimeRepository`;
* `SegmentStaticMemberRuntimeRepository`;
* `SegmentCalculationRuntimeRepository`;
* `SegmentDefinitionValidationService`;
* `SegmentCalculationService`;
* `RuntimeObjectQueryService`;
* `RuntimeObjectResolver`;
* use cases.

Все HTTP controllers берут `tenant_id` из `AuthenticatedRequestContextDep`, а не из payload.

---

## 9. Runtime Data и Schema Registry

### 9.1. Runtime Objects

## `segment`

```text
id
created_at
updated_at

segment_code
name
description

segment_type
status

target_object_id
target_object_name

definition_version

include_definition
exclude_definition

last_validated_at
last_calculated_at
requires_validation
```

Indexes:

```text
unique(segment_code)
idx_segment_status
idx_segment_target_object_id
```

---

## `segment_static_member`

```text
id
created_at
updated_at

segment_id

target_object_id
target_object_name
target_record_id

source
is_active
```

Indexes:

```text
idx_segment_static_member_segment
idx_segment_static_member_target
unique(segment_id, target_object_id, target_record_id)
```

---

## `segment_calculation`

```text
id
created_at
updated_at

segment_id
definition_version

status

started_at
finished_at

include_count
exclude_count
result_count

error_message
```

Indexes:

```text
idx_segment_calculation_segment
idx_segment_calculation_status
idx_segment_calculation_created_at
```

---

## `segment_calculation_member`

```text
id
created_at

calculation_id
segment_id

target_object_id
target_object_name
target_record_id

source_object_id
source_object_name
source_record_id

source_rule_id
```

Indexes:

```text
idx_segment_calculation_member_calculation
idx_segment_calculation_member_target
unique(calculation_id, target_object_id, target_record_id)
```

---

### 9.2. Object Features

Для Segment важны object features:

## `CONTACT_POINT`

Означает, что object может иметь ContactPoint bindings.

Для стандартных объектов:

```text
contact
company
lead
```

feature должна быть системной и неотключаемой.

Для custom object:

```text
job_application
loan_request
support_ticket
```

feature может быть включена явно.

---

## Communication-addressable target

Target object валиден для communication segment, если:

```text
object has CONTACT_POINT feature
```

или:

```text
object has relation path to object with CONTACT_POINT feature
```

Пример:

```text
job_application.contact_id -> contact.id
```

Тогда `job_application` может быть target object, а Broadcast позже сможет получить ContactPoint через этот path.

---

### 9.3. Runtime Schema Changes

Нужно добавить seed objects:

```text
segment
segment_static_member
segment_calculation
segment_calculation_member
```

Также нужно добавить relations:

```text
segment_static_member.segment_id -> segment.id
segment_calculation.segment_id -> segment.id
segment_calculation_member.calculation_id -> segment_calculation.id
segment_calculation_member.segment_id -> segment.id
```

---

## 10. Связь с Communication Module

### 10.1. Message Templates

Segment не зависит от message templates.

Message template выбирается в Broadcast/Communication.

---

### 10.2. Outbound Messages

Segment не создает outbound messages.

Outbound messages создаются после того, как Broadcast:

1. получил target subjects из Segment;
2. получил ContactPoint из ContactPoint module;
3. сформировал recipient snapshot;
4. вызвал Communication send flow.

---

### 10.3. Campaigns или Broadcasts

Broadcast использует Segment как source аудитории.

Broadcast должен иметь собственные настройки:

```text
segment_id
channel_code
template_id
contact_point_type
contact_point_selection_policy
deduplication_policy
exclude_segment_ids
```

Пример:

```text
segment_id = active_credit_clients
channel = SMS
contact_point_type = PHONE
selection_policy = LAST_ACTIVE
```

Segment возвращает:

```text
contact_id[]
```

Broadcast превращает:

```text
contact_id[] -> phone recipients
```

---

### 10.4. Delivery и Events

Delivery events остаются в `communication`.

Segment может использовать communication history только как source object для exclude rule.

Например:

```text
exclude:
  source_object = communication_outbound_message
  filter = created_at >= now - 5 days
  resolution_path = contact_id
```

Так Segment может исключить клиентов, которым недавно писали, но не становится владельцем delivery/status logic.

---

## 11. Структура файлов

```text
src/modules/segment/
  domain/
    segment/
      entity.py
      error.py
      repository.py
      value_object/
        segment_id.py
        segment_code.py
        segment_status.py
        segment_type.py
        target_object_ref.py
        audience_subject_ref.py
        resolution_path.py
    calculation/
      entity.py
      repository.py
      value_object/
    service/
      lifecycle_service.py
      definition_policy.py
      set_operation_service.py

  application/
    command/
      create_segment.py
      update_segment.py
      activate_segment.py
      pause_segment.py
      archive_segment.py
      validate_segment.py
      preview_segment.py
      calculate_segment.py
      add_static_members.py
      remove_static_members.py
    query/
      get_segment.py
      list_segments.py
      list_static_members.py
      get_calculation.py
      list_calculations.py
      list_calculation_members.py
      resolve_segment_subjects.py
    dto/
      segment.py
      segment_validation.py
      segment_preview.py
      segment_calculation.py
      audience_subject.py
    ports.py
    use_case/
      create_segment.py
      update_segment.py
      activate_segment.py
      pause_segment.py
      archive_segment.py
      validate_segment.py
      preview_segment.py
      calculate_segment.py
      resolve_segment_subjects.py

  infrastructure/
    runtime_object_names.py
    runtime_repository.py
    row_mapper.py
    services/
      segment_definition_validator.py
      segment_calculator.py
      relation_path_resolver.py
      segment_reference_resolver.py

  presentation/
    depends/
      infrastructure.py
      application.py
    http/
      router.py
      controller/
        create_segment.py
        update_segment.py
        activate_segment.py
        pause_segment.py
        archive_segment.py
        validate_segment.py
        preview_segment.py
        calculate_segment.py
        list_segments.py
        get_segment.py
        static_members.py
      request/
      response/
      error_mapper.py
```

---

## 12. План реализации

### 12.1. Этап 1 — Domain и контракты

* [ ] Создать модуль `src/modules/segment`.
* [ ] Описать `SegmentEntity`.
* [ ] Описать `SegmentStatusVO`, `SegmentTypeVO`, `SegmentIdVO`.
* [ ] Описать `TargetObjectRefVO`.
* [ ] Описать `AudienceSubjectRefVO`.
* [ ] Описать `ResolutionPathVO`.
* [ ] Описать domain errors.
* [ ] Описать repository protocols.
* [ ] Описать DTO.
* [ ] Описать commands/queries.
* [ ] Добавить unit tests для lifecycle transitions.

---

### 12.2. Этап 2 — Runtime schema и repositories

* [ ] Добавить runtime objects в schema seed.
* [ ] Добавить indexes и relations.
* [ ] Создать `SegmentRuntimeRepository`.
* [ ] Создать row mappers.
* [ ] Реализовать save/load/list.
* [ ] Реализовать static members repository.
* [ ] Реализовать calculation repository.
* [ ] Покрыть repository tests.

---

### 12.3. Этап 3 — Definition validation

* [ ] Реализовать `SegmentDefinitionValidationService`.
* [ ] Проверять target object.
* [ ] Проверять communication-addressable target.
* [ ] Проверять source objects.
* [ ] Проверять filter DSL через runtime_data.
* [ ] Проверять resolution path.
* [ ] Проверять segment references.
* [ ] Проверять отсутствие циклов.
* [ ] Запрещать source rule без пути к target.
* [ ] Добавить tests для invalid cases.

Ключевой invalid case:

```text
Target = job_application
Source = deal
Resolution path отсутствует
```

Ожидаемый результат:

```text
SOURCE_CANNOT_RESOLVE_TO_TARGET
```

---

### 12.4. Этап 4 — Calculation и preview

* [ ] Реализовать `PreviewSegmentUseCase`.
* [ ] Реализовать `CalculateSegmentUseCase`.
* [ ] Реализовать include calculation.
* [ ] Реализовать exclude calculation.
* [ ] Реализовать set operations.
* [ ] Реализовать static segment calculation.
* [ ] Реализовать dynamic segment calculation.
* [ ] Реализовать segment reference calculation.
* [ ] Сохранять calculation snapshot.
* [ ] Покрыть calculation tests.

---

### 12.5. Этап 5 — HTTP API и интеграция с Broadcast

* [ ] Реализовать HTTP controllers.
* [ ] Реализовать request/response schemas.
* [ ] Реализовать error mapper.
* [ ] Реализовать DI dependencies.
* [ ] Реализовать `SegmentSubjectResolverPort`.
* [ ] Подключить port для Broadcast.
* [ ] Добавить API tests.
* [ ] Добавить architecture boundary tests.

---

## 13. Тестирование

### 13.1. Unit Tests

Проверить:

* создание segment;
* status transitions;
* invalid status transitions;
* static segment members;
* definition version increment;
* set operations;
* target object policy;
* segment reference cycles;
* resolution path validation.

---

### 13.2. Integration Tests

Проверить:

* runtime repository save/load/list;
* calculation snapshot persistence;
* dynamic segment по одному source object;
* dynamic segment по нескольким source objects;
* include OR;
* include AND;
* exclude rules;
* segment reference;
* invalid source-to-target path.

---

### 13.3. API Tests

Проверить:

* `POST /api/segments`;
* `GET /api/segments`;
* `GET /api/segments/{id}`;
* `PUT /api/segments/{id}`;
* `POST /validate`;
* `POST /activate`;
* `POST /preview`;
* `POST /calculate`;
* static members endpoints;
* HTTP error mapping.

---

### 13.4. Regression Tests

Проверить:

* Segment не импортирует `communication` infrastructure.
* Segment не импортирует `contact_point` infrastructure.
* Segment не выбирает `PHONE`/`EMAIL`.
* Segment result не содержит `recipient_address`.
* Broadcast integration получает только target subjects.
* RuntimeData DSL behavior не дублируется внутри Segment.

---

## 14. Открытые вопросы

* [ ] Нужен ли отдельный standard object `customer`, или для MVP target = `contact`?
* [ ] Должен ли `lead` быть самостоятельным communication target или всегда приводиться к `contact`?
* [ ] Нужна ли отдельная feature `COMMUNICATION_SUBJECT`, или достаточно `CONTACT_POINT` + relation path?
* [ ] Нужны ли background jobs для больших segment calculations в MVP?
* [ ] Нужен ли TTL для старых calculation snapshots?
* [ ] Разрешать ли referenced segment с другим target object через conversion path, или в MVP строго запретить?
* [ ] Нужен ли preview sample records, кроме count?
* [ ] Нужно ли хранить explanation trace для excluded records?

---

## 15. Риски и ограничения

| Риск                                                        | Влияние                                  | Решение                                                                  |
|-------------------------------------------------------------|------------------------------------------|--------------------------------------------------------------------------|
| Source object не связан с target object                     | Segment нельзя корректно рассчитать      | Валидация resolution path при save/activate                              |
| Segment начнет выбирать PHONE/EMAIL                         | Нарушение границ с Broadcast             | Запретить ContactPoint selection в Segment DTO/UseCase                   |
| Смешивание разных target types                              | Broadcast не сможет обработать аудиторию | Один segment = один target object                                        |
| Циклические segment references                              | Бесконечный расчет                       | Graph validation references                                              |
| Изменение runtime schema ломает segment                     | Active segment становится невалидным     | Revalidation + `INVALID` status                                          |
| Большие сегменты долго считаются                            | Timeout API                              | Snapshot jobs / batch calculation                                        |
| AND между разными source objects работает неочевидно        | Ошибки бизнес-логики                     | Все rules сначала приводить к target set, потом применять set operations |
| Segment references с разными target objects                 | Некорректная дедупликация                | В MVP разрешать только same target object                                |
| Старые snapshots расходятся с новой definition              | Путаница в аудитории                     | Хранить `definition_version` в calculation                               |
| Broadcast использует изменившийся segment во время отправки | Невоспроизводимая рассылка               | Broadcast должен работать по собственному recipient snapshot             |
