Ниже я бы зафиксировал финальную архитектуру `ContactPoints` для FastAPI + SQLAlchemy 2.x + PostgreSQL с DDD + Clean Architecture. Основная цель — сделать MVP небольшим, но не заложить решений, которые придётся ломать при появлении Custom Objects, Record Registry, дедупликации и omnichannel.

# 1. Граница модуля

`ContactPoints` отвечает только за стабильные контактные идентификаторы клиента:

```text
PHONE
EMAIL
```

Не включать сюда:

```text
Website       → WebPresence
Telegram      ┐
WhatsApp      │
Facebook      ├→ Communication / ChannelIdentity
Instagram     │
Viber         ┘
Conversation  → Communication
```

То есть ответственность модуля:

```text
ContactPoints

"Какие phone/email связаны с CRM-объектом
и с какими CRM-объектами связан данный phone/email?"
```

Не:

```text
"Как отправить клиенту сообщение?"
```

---

# 2. Основная модель

Целевая конструкция:

```text
Contact
Company
Lead
Custom Object (future)
      │
      │ TargetRef
      ▼
ContactPointBinding
      │
      ▼
ContactPoint
```

Например:

```text
ContactPoint
PHONE
+380501234567
       │
       ├── Contact #123
       ├── Company #50
       └── Lead #900
```

Один физический endpoint хранится один раз внутри tenant.

---

# 3. Два Aggregate Root

Я бы **не делал Binding дочерней коллекцией ContactPoint Aggregate**.

Лучше два отдельных aggregate:

```text
ContactPoint
```

и

```text
ContactPointBinding
```

Причина: один `ContactPoint` потенциально может иметь сотни связей. Не нужно загружать и блокировать весь aggregate ради добавления ещё одного Lead.

### Aggregate `ContactPoint`

Отвечает за:

```text
id
type
canonical_value
status
metadata
created_at
```

Главный invariant:

```text
(type, canonical_value) unique внутри tenant
```

### Aggregate `ContactPointBinding`

Отвечает за:

```text
ContactPoint ↔ CRM Object
```

и хранит:

```text
target
label
primary
original_value
source
```

---

# 4. Важный invariant: ContactPoint immutable

После создания:

```text
PHONE +380501234567
```

нельзя сделать:

```text
PHONE +380671112233
```

через обычный UPDATE.

Потому что этот ContactPoint может использовать:

```text
Contact A
Company B
Lead C
```

Редактирование номера у Contact должно означать:

```text
старый Binding
    ↓
detach

resolve/create нового ContactPoint
    ↓
attach
```

Сам:

```text
ContactPoint.canonical_value
```

не изменяется.

Это один из ключевых архитектурных принципов модуля.

---

# 5. Domain модели

Примерно:

```python
class ContactPoint:
    id: ContactPointId
    type: ContactPointType
    canonical_value: ContactPointValue
    status: ContactPointStatus
```

и:

```python
class ContactPointBinding:
    id: ContactPointBindingId
    contact_point_id: ContactPointId
    target: ContactPointTarget
    label: str | None
    original_value: str | None
    is_primary: bool
    source: ContactPointSource
```

---

# 6. Value Objects

В domain слое:

```text
ContactPointId
ContactPointBindingId
ContactPointType
ContactPointValue
CanonicalPhone
CanonicalEmail
ContactPointTarget
ContactPointLabel
```

Особенно важен:

```python
@dataclass(frozen=True, slots=True)
class ContactPointTarget:
    object_type: str
    object_id: UUID
```

Сегодня:

```python
ContactPointTarget(
    object_type="contact",
    object_id=...
)
```

Позже:

```text
object_type + object_id
        ↓
RecordId
```

Application API при этом менять не потребуется.

---

# 7. ContactPointType

На MVP:

```python
class ContactPointType(StrEnum):
    PHONE = "phone"
    EMAIL = "email"
```

Не добавлять туда:

```text
telegram
whatsapp
website
facebook
```

При этом domain-код не должен содержать:

```python
if type == "phone":
...
elif type == "email":
...
```

по всему проекту.

Используем Strategy + Registry.

---

# 8. Normalizer Strategy

Контракт:

```python
class ContactPointNormalizer(Protocol):

    def normalize(
        self,
        value: str,
        context: NormalizationContext,
    ) -> NormalizedContactPoint:
        ...
```

Registry:

```python
class ContactPointNormalizerRegistry:

    def get(
        self,
        point_type: ContactPointType,
    ) -> ContactPointNormalizer:
        ...
```

Реализации:

```text
PhoneNormalizer
EmailNormalizer
```

Таким образом позже можно подключать дополнительные стратегии без изменения application handlers.

---

# 9. Phone normalization

Использовать:

```text
phonenumbers
```

Canonical representation:

```text
E.164
```

Например:

```text
050 123 45 67
(050)123-45-67
+38 050 123 45 67

       ↓

+380501234567
```

Normalizer должен принимать context:

```python
NormalizationContext(
    default_region="UA",
)
```

Результат:

```python
NormalizedContactPoint(
    canonical_value="+380501234567",
    display_value="+380 50 123 45 67",
)
```

Но `display_value` необязательно хранить: его можно получать при чтении.

---

# 10. Email normalization

Использовать:

```text
email-validator
```

На MVP:

```text
trim
validation
domain normalization
case normalization согласно политике CRM
IDN normalization
```

Например:

```text
" Denis@Example.COM "
        ↓
"denis@example.com"
```

Не реализовывать provider-specific magic:

```text
Gmail dots
+alias
```

То есть:

```text
denis+shop@gmail.com
denis@gmail.com
```

не должны автоматически считаться одним endpoint.

---

# 11. Почему raw_value лучше хранить в Binding

Не стоит делать:

```text
ContactPoint.raw_value
```

главным полем.

Например:

```text
Contact A ввёл:
0501234567

Company B:
+38 (050) 123-45-67
```

Оба относятся к:

```text
ContactPoint
+380501234567
```

Поэтому:

```text
ContactPoint
    canonical_value
```

а:

```text
ContactPointBinding
    original_value
```

Это позволит сохранить исходное представление конкретного объекта.

---

# 12. SQLAlchemy модели

## contact_points

```text
contact_points
────────────────────────

id                  UUID PK
type                VARCHAR
canonical_value     VARCHAR
status              VARCHAR
metadata            JSONB
created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

Constraint:

```text
UNIQUE(type, canonical_value)
```

если schema-per-tenant.

Если shared schema:

```text
UNIQUE(
    tenant_id,
    type,
    canonical_value
)
```

Я бы держал `ContactPoint` именно внутри tenant schema, если ваша CRM уже использует schema-per-tenant.

Не делать глобальный каталог клиентов в `public`.

---

# 13. contact_point_bindings

```text
contact_point_bindings
────────────────────────────────

id                  UUID PK

contact_point_id    UUID FK

contact_point_type  VARCHAR

target_type         VARCHAR
target_id           UUID

label               VARCHAR NULL

original_value      VARCHAR NULL

is_primary          BOOLEAN

source              VARCHAR NULL

created_at          TIMESTAMPTZ
updated_at          TIMESTAMPTZ
```

Основной constraint:

```text
UNIQUE(
    contact_point_id,
    target_type,
    target_id
)
```

То есть один и тот же телефон нельзя дважды добавить одному Contact.

---

# 14. Зачем дублировать `contact_point_type` в Binding

Потому что нам нужен DB invariant:

```text
Contact может иметь максимум
один primary PHONE

и максимум
один primary EMAIL
```

Тогда PostgreSQL partial unique index:

```sql
CREATE UNIQUE INDEX uq_contact_point_primary
ON contact_point_bindings (
    target_type,
    target_id,
    contact_point_type
)
WHERE is_primary = TRUE;
```

Без `contact_point_type` это пришлось бы проверять JOIN-запросом на application уровне.

Чтобы исключить рассинхронизацию:

```text
binding.contact_point_type
```

и

```text
contact_point.type
```

можно использовать composite FK либо проверять через repository/application service.

Для первой версии допустим application invariant + integration tests.

---

# 15. Правило primary

Я бы установил invariant:

> Если у объекта существует хотя бы один ContactPoint определённого типа, один из них должен быть primary.

Например:

```text
Contact

PHONE
+380501111111 ← primary
+380502222222

EMAIL
x@example.com ← primary
y@example.com
```

Правила:

```text
первый PHONE → автоматически primary
второй PHONE → secondary

SetPrimary → старый primary снимается

удаляем primary →
следующий автоматически становится primary
```

Так downstream-коду не приходится постоянно решать:

> какой телефон использовать?

---

# 16. Label

Не делать PostgreSQL ENUM:

```text
PERSONAL
WORK
MOBILE
HOME
OTHER
```

Лучше:

```text
label VARCHAR
```

а допустимые значения определять domain policy / registry.

Например:

```text
PHONE:
    mobile
    work
    home
    other

EMAIL:
    personal
    work
    other
```

Позже labels можно сделать tenant-configurable без database migration.

---

# 17. Source

Полезно заложить уже сейчас:

```text
manual
import
api
lead
integration
migration
```

Например:

```python
source="lead"
```

Это даст ответ:

> откуда вообще появился этот номер?

Но не нужно превращать `source` в сложный audit log.

---

# 18. Repository Ports

Domain/Application слой не знает SQLAlchemy.

```python
class ContactPointRepository(Protocol):

    async def get(
        self,
        point_id: ContactPointId,
    ) -> ContactPoint | None:
        ...

    async def find_by_canonical(
        self,
        point_type: ContactPointType,
        value: ContactPointValue,
    ) -> ContactPoint | None:
        ...

    async def add(
        self,
        entity: ContactPoint,
    ) -> None:
        ...
```

Отдельно:

```python
class ContactPointBindingRepository(Protocol):

    async def get(...): ...

    async def add(...): ...

    async def remove(...): ...

    async def list_by_target(...): ...

    async def list_by_contact_point(...): ...

    async def find_binding(...): ...

    async def unset_primary(...): ...
```

---

# 19. Unit Of Work

Application handlers работают через:

```python
class UnitOfWork(Protocol):

    contact_points: ContactPointRepository
    bindings: ContactPointBindingRepository

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
```

Infrastructure:

```text
SqlAlchemyUnitOfWork
```

использует:

```python
AsyncSession
```

Каждый command handler = одна transaction boundary.

---

# 20. Основной Application Service — Resolver

Нужен отдельный:

```text
ContactPointResolver
```

Он реализует:

```text
raw value
    ↓
Normalizer
    ↓
canonical value
    ↓
find ContactPoint
    ↓
exists?
 ┌────┴─────┐
 yes        no
 │           │
 return    create
```

API:

```python
async def resolve(
    point_type: ContactPointType,
    value: str,
) -> ContactPoint:
    ...
```

Никто снаружи модуля не должен делать:

```text
ContactPoint(...)
repository.add(...)
```

для обычного пользовательского сценария.

Только:

```text
resolver.resolve(...)
```

---

# 21. Race condition при Resolve

Это нужно решить сразу.

Два параллельных request:

```text
request A → +380...
request B → +380...
```

оба могут не найти ContactPoint и попытаться создать.

Поэтому source of truth — DB unique constraint:

```text
UNIQUE(type, canonical_value)
```

Repository можно реализовать через PostgreSQL:

```text
INSERT ... ON CONFLICT DO NOTHING
```

затем прочитать существующую запись.

Не использовать схему:

```python
if not exists:
    insert()
```

как единственную защиту.

---

# 22. Command handlers

Минимальный набор:

```text
AttachContactPoint
ReplaceContactPoint
DetachContactPoint
SetPrimaryContactPoint
ChangeContactPointLabel
```

Queries:

```text
GetTargetContactPoints
ResolveContactPointTargets
FindContactPoint
```

---

# 23. AttachContactPoint

Command:

```python
AttachContactPointCommand(
    target=ContactPointTarget(
        object_type="contact",
        object_id=contact_id,
    ),
    type=ContactPointType.PHONE,
    value="0501234567",
    label="mobile",
    is_primary=False,
    source="manual",
)
```

Handler:

```text
validate target
      ↓
normalize
      ↓
resolve ContactPoint
      ↓
check Binding
      ↓
determine primary
      ↓
create Binding
      ↓
commit
      ↓
publish events
```

---

# 24. ReplaceContactPoint

Редактирование UI должно использовать именно этот use case.

Например пользователь меняет:

```text
0501111111
```

на:

```text
0672222222
```

Handler:

```text
old Binding
      ↓
resolve new ContactPoint
      ↓
create/update Binding
      ↓
preserve:
    label
    primary
    source rules
      ↓
remove old Binding
```

Не:

```sql
UPDATE contact_points
SET canonical_value = ...
```

---

# 25. DetachContactPoint

Удаляет только:

```text
ContactPointBinding
```

Не удаляет:

```text
ContactPoint
```

потому что он может использоваться другими объектами.

Например:

```text
+380501234567
 ├ Contact
 └ Lead
```

удаление телефона из Contact не должно уничтожить endpoint Lead.

---

# 26. Garbage collection

Не делать synchronously.

После detach могут оставаться:

```text
ContactPoint
bindings = 0
```

Это нормально.

Позже можно реализовать maintenance job:

```text
delete orphan ContactPoints
older than N days
```

Но даже это не обязательно, если объём небольшой.

---

# 27. SetPrimaryContactPoint

Отдельный command.

Transaction:

```text
SELECT bindings
FOR UPDATE

       ↓

old primary = false

       ↓

new primary = true

       ↓

COMMIT
```

Дополнительно PostgreSQL partial unique index защищает invariant.

---

# 28. Target validation

ContactPoints module не должен импортировать:

```python
from contacts import Contact
from companies import Company
from leads import Lead
```

Нужен application port:

```python
class ContactPointTargetResolver(Protocol):

    async def exists(
        self,
        target: ContactPointTarget,
    ) -> bool:
        ...
```

Infrastructure adapter уже может обращаться к нужным модулям.

Позже:

```text
TargetResolver
     ↓
Record Registry
```

И ContactPoints вообще не изменится.

---

# 29. Никаких прямых dependencies на Contact/Lead/Company

Запрещённая зависимость:

```text
contact_points
     ↓
contacts
     ↓
companies
     ↓
leads
```

Правильная:

```text
Contacts ───┐
Companies ──┼──► ContactPoints Application API
Leads ──────┘
```

А ContactPoints знает только:

```text
ContactPointTarget
```

---

# 30. Lead

У Lead остаётся:

```text
contact_id nullable
company_id nullable
```

И параллельно:

```text
Lead
 ↓
ContactPointBinding
 ↓
PHONE / EMAIL
```

Это разные связи.

Например:

```text
Lead #500
phone = +380...
contact = Contact #100
```

ContactPoint означает:

> Lead поступил с этим номером.

`contact_id` означает:

> Lead идентифицирован как существующий Contact.

ContactPoint Binding после матчинга удалять нельзя.

---

# 31. Поиск

ContactPoints должен давать reverse lookup:

```python
ResolveContactPointTargetsQuery(
    type=PHONE,
    value="0501234567",
)
```

Pipeline:

```text
normalize
   ↓
ContactPoint lookup
   ↓
Bindings
   ↓
TargetRef[]
```

Результат:

```text
[
    Contact #123,
    Company #50,
    Lead #900
]
```

---

# 32. Global CRM Search — не обязанность ContactPoints

Поиск:

```text
Иван Иванов
+380501234567
ivan@example.com
```

лучше делать отдельным:

```text
CRM Search / Customer Search
```

Он комбинирует:

```text
Contact search
Company search
ContactPoint search
```

Например:

```text
CustomerSearchService

          ┌─ Contacts
query ────┼─ Companies
          └─ ContactPoints
```

ContactPoints предоставляет только свой Search Port.

---

# 33. FastAPI endpoints

Я бы сделал API вокруг Binding, а не отдельных `/phones` и `/emails`.

Например:

```text
GET
/api/v1/{target_type}/{target_id}/contact-points
```

```text
POST
/api/v1/{target_type}/{target_id}/contact-points
```

Payload:

```json
{
  "type": "phone",
  "value": "0501234567",
  "label": "mobile",
  "is_primary": true
}
```

Редактирование:

```text
PUT
/api/v1/contact-point-bindings/{binding_id}
```

Удаление:

```text
DELETE
/api/v1/contact-point-bindings/{binding_id}
```

Primary:

```text
POST
/api/v1/contact-point-bindings/{binding_id}/make-primary
```

Reverse lookup:

```text
GET
/api/v1/contact-points/resolve
    ?type=phone
    &value=0501234567
```

---

# 34. Pydantic только на Presentation boundary

Например:

```text
presentation/
    api/
        schemas.py
```

Pydantic:

```python
class AttachContactPointRequest(BaseModel):
    type: Literal["phone", "email"]
    value: str
    label: str | None = None
    is_primary: bool = False
```

Но Domain:

```text
НЕ импортирует Pydantic
НЕ импортирует FastAPI
НЕ импортирует SQLAlchemy
```

Это принципиально для Clean Architecture.

---

# 35. Domain Events

Заложить сразу:

```text
ContactPointCreated
ContactPointAttached
ContactPointDetached
ContactPointReplaced
ContactPointPrimaryChanged
```

Например:

```python
@dataclass(frozen=True)
class ContactPointAttached:
    binding_id: UUID
    contact_point_id: UUID
    target: ContactPointTarget
```

Пока subscribers могут отсутствовать.

Позже:

```text
ContactPointAttached
       │
       ├── Audit
       ├── Search Index
       ├── Deduplication
       ├── Customer 360
       └── Timeline
```

---

# 36. Transaction + events

Правильный flow:

```text
Handler
   ↓
Domain operation
   ↓
Repository
   ↓
COMMIT
   ↓
Domain Events
```

Если в будущем события должны гарантированно попадать в Kafka/RabbitMQ, добавить:

```text
Transactional Outbox
```

Для MVP отдельную outbox infrastructure можно не вводить, если нет message broker.

---

# 37. Структура проекта

Я бы сделал модуль так:

```text
src/
└── modules/
    └── contact_points/

        domain/
        ├── entities/
        │   ├── contact_point.py
        │   └── contact_point_binding.py
        │
        ├── value_objects/
        │   ├── contact_point_id.py
        │   ├── binding_id.py
        │   ├── contact_point_value.py
        │   └── target.py
        │
        ├── enums/
        │   ├── contact_point_type.py
        │   └── contact_point_status.py
        │
        ├── events/
        │   ├── created.py
        │   ├── attached.py
        │   ├── detached.py
        │   └── primary_changed.py
        │
        ├── repositories/
        │   ├── contact_point.py
        │   └── binding.py
        │
        ├── services/
        │   └── normalization.py
        │
        └── exceptions.py

        application/
        ├── commands/
        │   ├── attach.py
        │   ├── replace.py
        │   ├── detach.py
        │   ├── set_primary.py
        │   └── change_label.py
        │
        ├── queries/
        │   ├── get_for_target.py
        │   └── resolve_targets.py
        │
        ├── handlers/
        │   ├── attach.py
        │   ├── replace.py
        │   ├── detach.py
        │   ├── set_primary.py
        │   └── resolve_targets.py
        │
        ├── services/
        │   └── resolver.py
        │
        ├── ports/
        │   ├── unit_of_work.py
        │   ├── target_resolver.py
        │   └── event_bus.py
        │
        └── dto/
            ├── contact_point.py
            └── binding.py

        infrastructure/
        ├── persistence/
        │   └── sqlalchemy/
        │       ├── models.py
        │       ├── repositories.py
        │       └── unit_of_work.py
        │
        ├── normalization/
        │   ├── phone.py
        │   ├── email.py
        │   └── registry.py
        │
        └── events/
            └── event_bus.py

        presentation/
        └── api/
            ├── router.py
            ├── schemas.py
            ├── dependencies.py
            └── mappers.py
```

---

# 38. Dependency direction

Получается:

```text
Presentation
      ↓
Application
      ↓
Domain
```

И:

```text
Infrastructure
      ↓
Application Ports / Domain Ports
```

Никогда:

```text
Domain → SQLAlchemy
Domain → FastAPI
Domain → Pydantic
```

---

# 39. SQLAlchemy

Использовать SQLAlchemy 2.x async:

```python
AsyncSession
async_sessionmaker
Mapped[]
mapped_column()
```

ORM model — это persistence model, а не domain entity.

То есть не нужно:

```python
class ContactPoint(Base, DomainEntity):
```

Лучше:

```text
SQLAlchemyContactPointModel
        ↕ mapper
Domain ContactPoint
```

Да, это немного больше кода, но для модульной CRM архитектура будет значительно чище.

---

# 40. Repository mapper

Infrastructure:

```text
ORM
 ↓
Domain mapper
 ↓
Entity
```

Например:

```python
ContactPointMapper.to_domain(model)
ContactPointMapper.to_model(entity)
```

Application handlers не должны получать SQLAlchemy ORM objects.

---

# 41. Миграция существующих Contact / Company / Lead

Проводить поэтапно.

**Этап 1.** Создать `ContactPoints` tables, domain и API.

**Этап 2.** Backfill существующих:

```text
Contact.phone
Contact.email

Company.phone
Company.email

Lead.phone
Lead.email
```

Pipeline:

```text
legacy value
    ↓
normalize
    ↓
resolve
    ↓
binding
```

Одинаковое значение:

```text
Contact A
Company B
Lead C
```

создаёт один `ContactPoint` и три Binding.

**Этап 3.** Включить dual-write на короткий migration period.

**Этап 4.** Переключить read на ContactPoints.

**Этап 5.** Запретить изменение legacy fields.

**Этап 6.** Удалить:

```text
phone
email
```

из Contact / Company / Lead либо оставить только denormalized read cache, если появится реальная необходимость.

---

# 42. Ошибочные legacy значения

Migration job не должен молча выбрасывать:

```text
+380 abc
foo@
1234
```

Нужен migration report:

```text
processed
created_points
created_bindings
duplicates
invalid_phone
invalid_email
errors
```

Invalid legacy values оставить для ручной обработки.

---

# 43. Custom Objects

Пока:

```text
ContactPointTarget

object_type
object_id
```

Например:

```text
contact / UUID
company / UUID
lead / UUID
```

Когда появится:

```text
Record Registry
```

делаем:

```text
contact_point_bindings

target_type
target_id

        ↓ migration

record_id
```

А Domain VO:

```text
ContactPointTarget
```

может остаться API abstraction или быть заменён внутри на:

```text
RecordId
```

Ни FastAPI API, ни ContactPoint Aggregate переписывать не придётся.

---

# 44. Что понадобится в Record Registry позже

Целевая модель:

```text
Record
────────────────

id
object_type
object_id
```

И:

```text
ContactPointBinding

record_id FK
contact_point_id FK
```

После этого такие горизонтальные модули:

```text
ContactPoints
Files
Tags
Notes
Comments
Tasks
Activities
Audit
```

смогут привязываться одинаково:

```text
Horizontal Module
       ↓
    RecordId
```

---

# 45. Что сознательно не делать в ContactPoints

Не добавлять туда:

```text
SMS sending
Email sending
WhatsApp
Telegram
Chats
Conversations
Open Channels
Websites
Social profiles
Marketing consent
Message history
```

Это отдельные bounded contexts.

Позже:

```text
Communication
      │
      ├── SMS → ContactPoint PHONE
      └── Email → ContactPoint EMAIL
```

То есть Communication **потребляет ContactPoints**, а не наоборот.

---

# 46. Tests

Нужны четыре уровня:

```text
Domain unit tests
Application handler tests
PostgreSQL repository integration tests
FastAPI API tests
```

Отдельно обязательно протестировать concurrency:

```text
два параллельных resolve одного телефона
два параллельных attach
два одновременных SetPrimary
```

И invariants:

```text
один ContactPoint на canonical value

один Binding на:
ContactPoint + target

не больше одного primary:
target + point type

ContactPoint value immutable

detach одного Binding
не удаляет ContactPoint
```

---

# 47. Реализация по итерациям

Я бы реализовывал модуль в таком порядке:

1. **Domain Core** — `ContactPoint`, `Binding`, VO, enums, invariants, repository ports.
2. **Normalization** — `PhoneNormalizer`, `EmailNormalizer`, registry, `phonenumbers`, `email-validator`.
3. **Persistence** — SQLAlchemy models, migrations, indexes, repositories, UoW.
4. **Application** — Resolve, Attach, Replace, Detach, SetPrimary, List, Reverse Lookup.
5. **FastAPI** — Pydantic schemas, routers, error mapping, DI.
6. **Migration** — backfill Contact/Company/Lead, migration report, temporary dual-write.
7. **Search integration** — поиск Contact/Company/Lead по normalized phone/email.
8. **Events & integrations** — audit/timeline/search index subscribers по мере необходимости.
9. **Record Registry migration** — когда появятся Custom Objects и другие горизонтальные capabilities.

После **этапа 6** модуль уже можно считать production MVP.

---

## Итоговая архитектура

В первой production-версии:

```text
              Contact / Company / Lead
                         │
                         │
                ContactPointTarget
                         │
                         ▼
               ContactPointBinding
                │               │
             primary          label
                │
                ▼
                 ContactPoint
                /            \
             PHONE          EMAIL
               │              │
        PhoneNormalizer EmailNormalizer
```

Позже:

```text
Contact / Company / Lead / CustomObject
                  │
                  ▼
                Record
                  │
                  ▼
         ContactPointBinding
                  │
                  ▼
            ContactPoint
```

А сбоку независимо развивается:

```text
Communication
    │
    ├── SMS ────────► PHONE
    ├── Email ──────► EMAIL
    ├── WhatsApp
    ├── Telegram
    └── Facebook
```

Главные решения, которые стоит зафиксировать сейчас: **`ContactPoint` immutable, уникален по canonical value внутри tenant; принадлежность объекту всегда через отдельный `Binding`; `PHONE/EMAIL` остаются единственными ContactPoint types; Domain не знает Contact/Company/Lead; изменение номера — rebind, а не update глобального ContactPoint; будущий переход на `RecordId` предусмотрен через `ContactPointTarget` abstraction.** Такой модуль можно реализовать сейчас без большого платформенного рефакторинга и впоследствии дорастить до общей CRM object architecture.
