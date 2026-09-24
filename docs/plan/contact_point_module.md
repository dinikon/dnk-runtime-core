# Модуль `contact_points`

План для текущего `dnk-runtime-core`. Классы нового модуля ниже — проектируемые контракты;
ссылки на существующие исходники фиксируют архитектурную основу. Реализация не восстанавливает
удалённые `contact_point`, `schema_registry` или `runtime_data`.

## 1. Основа в текущем приложении

- [Стиль модулей](../develop-style.md): структура по поддоменам, command/query/use case,
  доменные VO, инфраструктурные адаптеры и DI в `presentation/depends`.
- [CRM](../modules/crm.md): статические Company и Contact внутри tenant, CRUD под `/api/console/crm`.
  Сейчас у них нет телефонов или email; Lead в этой интеграции отсутствует.
- [Shared UoW protocol](../../src/modules/shared/application/persistence/unit_of_work_protocol.py),
  [реализация](../../src/modules/shared/infrastructure/persistence/unit_of_work.py) и
  [HTTP dependency](../../src/modules/shared/presentation/persistence/depends.py): общая session,
  commit/rollback на выходе из контекста.
- [CRM infrastructure dependencies](../../src/modules/crm/presentation/depends/infrastructure.py) и
  [application dependencies](../../src/modules/crm/presentation/depends/application.py): образец сборки.
- [Tenant migrations](../data/tenant-migrations.md): `TenantBase`, регистрация моделей и Alembic.
- [Shared outbox port](../../src/modules/shared/application/events/outbox_repository_protocol.py) и
  [publisher builder](../../src/modules/shared/presentation/events/outbox_publisher_builder.py):
  outbox/RabbitMQ уже существуют.

## 2. Граница первой версии

`contact_points` хранит единый справочник phone/email **внутри tenant** и связи с объектами.
Одна точка может принадлежать нескольким объектам. Company и Contact подключаются первыми;
следующие модули используют тот же application API через собственные адаптеры.

Первая версия включает общую модель ContactPoint, отдельную ContactPointBinding, нормализацию,
дедупликацию, чтение связей в обе стороны, настраиваемые подписи отдельно для phone/email,
два компонента ввода и атомарное сохранение вместе с CRM-карточкой.

Отправка сообщений, социальные профили, подтверждение владения, глобальный CRM-поиск,
Lead и Record Registry не входят в реализацию. `is_primary`, status, произвольный JSON metadata,
source и фоновые удаления точек — возможные расширения по отдельному требованию,
а не зависимости для запуска первой версии.

## 3. Domain и persistence

### ContactPoint

Отдельный aggregate root: `id`, `type`, `canonical_value`, `country_code` для телефона,
`created_at`, `updated_at`, `created_by`, `updated_by`.

- Тип — `phone | email`; `(type, canonical_value)` уникален внутри tenant.
- Тип и canonical value неизменяемы после создания.
- Номер хранится в E.164, email — в нормализованном виде.
- После удаления последнего binding точка остаётся для повторного использования.

### ContactPointBinding

Отдельный aggregate root: `id`, `contact_point_id`, `target`, optional `label_id`, `position`,
audit-поля. Это не коллекция внутри ContactPoint: привязка не загружает всех владельцев номера.

```python
@dataclass(slots=True, frozen=True)
class ContactPointTargetVO:
    model_key: str
    record_id: EntityIdVO
```

Ключи `crm.contact` и `crm.company` — устойчивые идентификаторы интеграции, не имена классов
или таблиц. Tenant передаётся отдельно. Domain/application используют VO, а не голые UUID.

Уникальность binding: `(model_key, record_id, contact_point_id)`. Редактирование значения
находит/создаёт новую точку и меняет `contact_point_id` существующего binding, сохраняя его id.
Другие связи и исходная точка не изменяются. Порядок массива хранится в `position`.

### ContactPointLabel

Отдельная сущность настроек: `id`, `type`, `name`, `is_active`, audit-поля. Binding хранит
`label_id`, а не произвольную строку вместо справочника. Тип подписи совпадает с типом точки.
Начальные подписи каждого типа: «Рабочий», «Личный», «Другой». Выбор подписи необязателен.

Администратор переименовывает и архивирует подписи. Архивная подпись сохраняется у старых связей,
но не назначается новым. Физическое удаление используемой подписи не предоставляется.

### Общие правила

- Entities: `@dataclass(slots=True)`; VO и commands: `@dataclass(slots=True, frozen=True)`.
- `ContactPointIdVO`, `ContactPointBindingIdVO`, `ContactPointLabelIdVO` наследуют shared
  `EntityIdVO` и находятся в `domain/<subdomain>/value_object`.
- Domain errors наследуют `DomainError`; NotFound — специализированная ошибка.
- Таблицы `contact_points`, `contact_point_bindings`, `contact_point_labels` используют
  `TenantBase`, shared `StringUUID`, `AudienceMixin` и actor-поля по образцу CRM.
- Колонки `tenant_id` в этих таблицах нет; справочник не размещается в `public`.
- FK binding → point и binding → label находятся внутри tenant-схемы. FK на полиморфный target нет.
- Добавить индекс `(model_key, record_id, position, id)` и индекс по `contact_point_id`,
  CHECK для допустимого типа и неотрицательной позиции. Тип подписи проверяет domain service.
- `contact_point_type` в binding ради primary-индекса не добавлять: primary не входит в первую версию.

### Что переиспользуется через Shared, а что остаётся в модуле

**В первой версии новые contact-specific VO в Shared не выносить.** Использовать уже имеющиеся
`EntityIdVO`, `DomainError`, `ClockPort` и общие инфраструктурные примитивы. Shared не должен
импортировать `contact_points` или становиться общим хранилищем предметных типов всех модулей.

| Тип/контракт | Владелец и способ использования |
| --- | --- |
| `EntityIdVO`, общие ошибки и время | Существующий Shared; переиспользуются напрямую |
| `ContactPointIdVO`, `ContactPointBindingIdVO`, `ContactPointLabelIdVO` | Domain `contact_points`; не переносить в Shared ради межмодульного вызова |
| `ContactPointValueVO`, canonical phone/email, тип и контекст нормализации | Domain `contact_points`; этот модуль владеет правилами нормализации и уникальности |
| `ContactPointTargetVO` | Domain `contact_points`; общий `RecordRef` в Shared пока не требуется |
| CRM `ContactPointsPort` и входные/выходные DTO этого порта | Application CRM; определяют потребности CRM без зависимости на внутренние VO другого модуля |
| Публичные commands/query/DTO `contact_points` | Application `contact_points`; используются адаптером через явные публичные экспорты |

Межмодульное взаимодействие — **Protocol + типизированные данные + адаптер**, а не только
интерфейс без контракта данных. CRM use case оперирует собственным портом/DTO; infrastructure
adapter переводит их в публичные commands/query `contact_points` и возвращает CRM-owned DTO.
Если публичный command содержит VO модуля, адаптер вправе использовать его публичный экспорт;
это не требует переноса VO в Shared. Domain CRM не импортирует contact_points entities или VO.
Через границу не передаются ORM-объекты, repositories или session.

Переиспользование операций нормализации идёт через владельца `contact_points`. Например,
email для входа в систему и контактный email могут иметь разные правила сравнения: совпадение
названия поля не является основанием объединять их в Shared EmailVO.

Вынос общего VO допустим отдельным изменением, когда как минимум два независимых модуля
нуждаются в одной семантике и одинаковых инвариантах, тип не зависит от lifecycle contact_points,
а зависимости направлены только в Shared. Тогда извлекается минимальный нейтральный примитив
с общими тестами. CountryCodeVO или общий RecordRef — возможные кандидаты при появлении таких
потребителей; специализированные идентификаторы точек и bindings остаются у своего владельца.

## 4. Нормализация и repository contracts

Синхронный порт normalizer и VO контекста/результата находятся в domain; реализации
`phonenumbers` и `email-validator` — в infrastructure. Сопоставление типа и стратегии
собирается в DI и передаётся сервису, без глобального service locator.

- Телефон: страна передаётся явно, проверяются валидность и соответствие стране, результат — E.164.
  UI начинает с `UA`. Международный номер может определить страну в UI; неоднозначность
  требует выбора. Добавочные номера не поддерживаются в первой версии.
- Email: trim, синтаксис `local@domain.tld`, нормализация домена/IDN; не ограничивать `.com`.
  Сохранять регистр локальной части согласно ранее выбранной политике. DNS-проверку отключить.
  Не объединять Gmail-точки или `+alias`.
- Display formatting вычисляется отдельно. Исходный ввод не является ключом дедупликации;
  `original_value` в binding можно добавить при требовании к импорту.
- Ошибки библиотек переводятся в domain errors. Domain/application не импортируют реализации
  библиотек, SQLAlchemy, FastAPI или Pydantic.

Repository получает `(session, naming)`. **Каждая операция** принимает tenant явно:

```python
class ContactPointRepositoryProtocol(Protocol):
    async def get(
        self, tenant_id: EntityIdVO, point_id: ContactPointIdVO
    ) -> ContactPoint: ...

    async def find_by_canonical(
        self,
        tenant_id: EntityIdVO,
        point_type: ContactPointType,
        canonical_value: ContactPointValueVO,
    ) -> ContactPoint | None: ...

    async def get_or_create(
        self, tenant_id: EntityIdVO, candidate: ContactPoint
    ) -> ContactPoint: ...
```

`get` поднимает NotFound, `find_by_canonical` допускает отсутствие. Binding/label repositories
следуют тем же правилам. Query repository поддерживает batch read нескольких target без N+1.

SQLAlchemy Core statements применяют локальный `schema_translate_map` через `TenantSchemaNaming`,
как CRM repositories. Не менять engine options или `search_path` в бизнес-коде, не хранить
текущий tenant в repository instance. Rows явно преобразуются в entity/DTO.

`get_or_create`: `INSERT ... ON CONFLICT DO NOTHING RETURNING ...`, при конфликте — чтение
существующей точки. Unique constraint защищает параллельные создания. Не продолжать работу
после обычного `IntegrityError` в аварийной транзакции и не откатывать всю карточку ради resolve.

## 5. UoW: общая граница транзакции

**Не создавать ContactPointsUnitOfWork, новый UnitOfWorkProtocol или UoW с полями
`contact_points`/`bindings`.** Shared protocol уже предоставляет session, context manager,
commit/rollback. Репозитории создаются отдельно в dependency factories. Хотя shared protocol
типизирует `AsyncSession`, use cases нового модуля получают repository/service protocols
и не используют session напрямую.

HTTP использует существующий `UoWDep = Annotated[UnitOfWorkProtocol, Depends(get_uow)]`:

1. `get_uow` берёт session factory из `app.state.db` либо shared `db_helper`.
2. При наличии `request.state.tenant_connection` dependency создаёт session на этом connection.
   Модуль не открывает обходное соединение и не дублирует tenant admission gate.
3. Стандартное кеширование FastAPI dependency даёт одну UoW всем repository factories запроса.
4. CRM, points, bindings, labels и при необходимости outbox используют **один экземпляр session**.
5. Выход из контекста делает commit при успехе, rollback при исключении; session закрывается в finally.

Граница бизнес-транзакции — вся карточка, а не каждый вложенный use case:

```text
HTTP create/update Contact или Company
  └─ shared get_uow
      └─ CRM use case
          ├─ create / lock + update CRM aggregate
          └─ CRM-owned port → infrastructure adapter
              └─ contact_points use case
                  ├─ normalize + resolve points
                  └─ synchronize bindings
      └─ общий commit при успешном выходе
         либо rollback всех изменений при исключении
```

В use cases, repositories и межмодульном адаптере не вызывать `commit`, `rollback`,
`session.close` и не открывать вложенный UoW. Execution/flush допустимы внутри repository;
flush и возврат DTO из вложенного use case не означают commit.

В приложении есть специальные сценарии с явными commit, например Control Plane acceptance
и некоторые identity flows. Их границы не переносить в составное сохранение CRM-карточки.

При переводе ошибки в HTTP **поднимать** `HTTPException`, как CRM `http_errors`, а не поглощать
исключение и возвращать обычный response: UoW должна увидеть ошибку. Не считать возврат use case
гарантией durable success: финализация yield-dependency происходит отдельно. Изменение lifecycle
shared dependency не входит в модуль; интеграционный тест проверяет завершение запроса и состояние БД.

Для будущего CLI/worker внешний entrypoint открывает shared UoW и собирает зависимости
на её session. Самостоятельная операция получает внешнюю транзакцию; вложенные операции
сохранения карточки используют уже открытую.

## 6. Dependency injection

Сборка выполняется в `presentation/depends`:

| Файл | Ответственность |
| --- | --- |
| `contact_points/presentation/depends/infrastructure.py` | Repositories, TenantSchemaNaming, normalizers |
| `contact_points/presentation/depends/application.py` | Domain services и отдельные use cases |
| `crm/presentation/depends/infrastructure.py` | CRM adapter к готовым contact_points use cases |
| `crm/presentation/depends/application.py` | CRM use cases с repository, ClockPort и новым портом |

Ниже эскизы будущих factories; импорты проектируемых классов сокращены.

```python
from typing import Annotated
from fastapi import Depends

from src.config import dnk_config
from src.modules.shared.application.persistence.tenant_schema_naming import TenantSchemaNaming
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_tenant_naming() -> TenantSchemaNaming:
    return TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)


TenantNamingDep = Annotated[TenantSchemaNaming, Depends(get_tenant_naming)]


def get_contact_point_repository(uow: UoWDep, naming: TenantNamingDep):
    return SqlAlchemyContactPointRepository(uow.session, naming)


ContactPointRepositoryDep = Annotated[
    SqlAlchemyContactPointRepository, Depends(get_contact_point_repository)
]
```

Binding и label factories получают тот же shared `UoWDep`. Не добавлять `use_cache=False`,
альтернативный `get_uow` или ручной вызов yield-dependency. Naming создаётся в composition root
по shared контракту без импорта приватной factory из CRM infrastructure.

```python
from src.modules.shared.presentation.time.depends import ClockDep


def get_contact_point_resolver(
    repository: ContactPointRepositoryDep,
    normalizers: ContactPointNormalizersDep,
    clock: ClockDep,
):
    return ContactPointResolver(repository, normalizers, clock)


ContactPointResolverDep = Annotated[
    ContactPointResolver, Depends(get_contact_point_resolver)
]


def get_sync_target_contact_points_use_case(
    resolver: ContactPointResolverDep,
    bindings: ContactPointBindingRepositoryDep,
    labels: ContactPointLabelRepositoryDep,
    clock: ClockDep,
):
    return SyncTargetContactPointsUseCase(resolver, bindings, labels, clock)


SyncTargetContactPointsUseCaseDep = Annotated[
    SyncTargetContactPointsUseCase, Depends(get_sync_target_contact_points_use_case)
]
```

`Depends`/dependency aliases не переходят в конструкторы domain/application. Use case принимает
Protocol/ClockPort и вызывается через `async def __call__(command)`. Controller получает
`<UseCase>Dep`, создаёт frozen command, переводит DTO в response schema. Public classes и aliases
экспортируются через `__all__`; factories и use cases имеют короткие docstring.

HTTP create-id генерирует controller через существующий `UuidDep`. Для sync он выдаёт candidate
point-id каждой строке и binding-id новым строкам; адаптер передаёт их в command. Если точка уже
существует, resolver использует её id. Существующий binding-id проверяется на принадлежность target.
Не создавать generator или clock внутри use case/repository.

## 7. Межмодульный адаптер и проверка target

```text
CRM application → CRM-owned ContactPointsPort
                         ▲
CRM infrastructure adapter → contact_points public application contracts
                                      ↓
                              contact_points domain
```

CRM-owned port предоставляет sync, batch read и удаление связей. Адаптер получает готовые
contact_points use cases через CRM dependency factory. CRM repository и их repositories
сходятся на одном shared `get_uow`. Адаптер переводит DTO/VO и не делает HTTP-запрос к своему API.

Пример сборки адаптера в `crm/presentation/depends/infrastructure.py` и передачи в
CRM use case из `crm/presentation/depends/application.py`:

```python
def get_crm_contact_points_port(
    sync: SyncTargetContactPointsUseCaseDep,
    read: GetTargetsContactPointsUseCaseDep,
    remove: RemoveTargetContactPointsUseCaseDep,
) -> ContactPointsPort:
    return ContactPointsApplicationAdapter(sync, read, remove)


CrmContactPointsDep = Annotated[
    ContactPointsPort, Depends(get_crm_contact_points_port)
]


def get_update_contact_use_case(
    repository: ContactRepositoryDep,
    clock: ClockDep,
    contact_points: CrmContactPointsDep,
):
    return UpdateContactUseCase(repository, clock, contact_points)
```

`GetTargetsContactPointsUseCaseDep` здесь обозначает dependency пакетного query.
Импорт dependency aliases другого модуля выполняется только в presentation composition root.
Сам `ContactPointsApplicationAdapter` импортирует публичные application contracts, а не
`presentation/depends`. Так инфраструктура не зависит от FastAPI-сборки.

Для преобразования ContactIdVO/CompanyIdVO в общий target использовать
`EntityIdVO.from_value(typed_id.uuid)`: shared VO намеренно не принимает другой специализированный
IdVO напрямую. `model_key` задаётся интеграцией CRM, не произвольным payload пользователя.

**В первой версии существование, доступ и блокировку target обеспечивает модуль-владелец.**
ContactPoints не импортирует CRM domain, repositories или presentation. Не создавать обратный
TargetResolver с зависимостью на CRM use cases: это породит цикл.

- Create: CRM создаёт объект и синхронизирует точки на той же session.
- Update: CRM получает объект `for_update=True`, обновляет данные и синхронизирует массивы.
- Delete: дополнить текущий CRM delete последовательностью lock → удалить bindings через порт →
  удалить объект, всё в одной UoW.
- Блокировка target сериализует update/delete даже при отсутствии bindings. Блокировки только
  существующих bindings недостаточно. Будущие writers обязаны соблюдать тот же порядок.

Целостность полиморфного target обеспечивают эти сценарии и их тесты. Если позже появится
универсальный внешний HTTP API bindings, отдельно добавить порт проверки target/доступа/блокировки
и адаптеры владельцев без обхода указанной дисциплины.

## 8. Application и HTTP API

Основные операции:

- `SyncTargetContactPointsUseCase`: resolve/create, создание/rebind, изменение label/position,
  удаление отсутствующих bindings для переданных массивов.
- `GetTargetContactPointsUseCase` и batch query нескольких target.
- `RemoveTargetContactPointsUseCase`: очистка связей перед удалением владельца.
- `ResolveContactPointTargetsUseCase`: нормализовать значение и вернуть target refs внутри tenant,
  не создавая точку при отсутствии совпадения. Данные CRM добавляет потребитель.
- Отдельные list/create/update use cases подписей; архивирование входит в update.

Отдельные attach/detach/replace HTTP-запросы для каждой строки формы не нужны: они нарушат
сохранение вместе с карточкой. Эти действия выполняются внутри sync.

Существующие CRM POST/PUT и GET/list расширяются `phones` и `emails`:

- входная строка: `binding_id` для существующей связи, `value`, optional `label_id`,
  `country_code` для телефона; ответ также содержит `contact_point_id`;
- omitted-array при update означает «не изменять», `[]` — «очистить»; при create omitted означает
  пустой список; `null` вместо массива отклоняется;
- при переводе Pydantic request в command сохранять отличие omitted от `[]`;
- ошибка строки откатывает всю карточку; ошибка содержит массив, индекс и поле;
- чужой binding нельзя переназначить текущему target.

Роутер модуля подключается через `src/modules/router.py` под существующим `/api/console`:

| Method | Path | Доступ |
| --- | --- | --- |
| GET | `/api/console/contact-points/labels?type=phone` | Участник tenant |
| POST | `/api/console/contact-points/labels` | Администратор tenant |
| PATCH | `/api/console/contact-points/labels/{label_id}` | Администратор tenant |

Tenant и actor извлекаются из `AuthenticatedRequestContextDep`, не принимаются из тела.
Роль admin проверяется сервером на presentation boundary. Mutations используют `require_csrf`.
Ошибки: validation 422, not found 404, conflict 409, недостаточные права 403.
`/api/v1/...` и новый механизм аутентификации не вводятся.

## 9. События и outbox

Новый event bus не нужен: shared уже содержит порты, repositories и RabbitMQ publisher.
Integration events подключаются при согласованном потребителе; первая версия не требует subscribers.
Если события включаются, порядок такой:

```text
domain operation
  → запись points/bindings
  → запись IntegrationEvent через shared OutboxRepositoryProtocol на той же session
  → commit внешней UoW
  → existing shared outbox worker публикует событие с повторными попытками
```

Не публиковать в брокер из handler после собственного commit, не создавать модульный event bus
и не импортировать shared RabbitMQ adapter в бизнес-модуль. `SqlAlchemyOutboxRepository(uow.session)`
собирается на presentation boundary, application видит порт. Перевод IdVO в UUID существующего
shared IntegrationEvent происходит на границе событий. Ошибка карточки откатывает и outbox.

## 10. Структура модуля

Использовать структуру по поддоменам из develop-style, не общие `entities/repositories/handlers`:

```text
src/modules/contact_points/
├── domain/
│   ├── contact_point/
│   │   ├── entity.py, error.py, repository.py, service.py, normalization.py
│   │   └── value_object/
│   ├── binding/
│   │   ├── entity.py, error.py, repository.py, service.py
│   │   └── value_object/
│   └── label/
│       ├── entity.py, error.py, repository.py
│       └── value_object/
├── application/
│   ├── contact_point/{command,dto,query,use_case}/
│   ├── binding/{command,dto,query,use_case}/
│   └── label/{command,dto,query,use_case}/
├── infrastructure/
│   ├── persistence/
│   │   ├── models.py
│   │   ├── contact_point_repository.py
│   │   ├── binding_repository.py
│   │   └── label_repository.py
│   └── normalization/{phone.py,email.py}
└── presentation/
    ├── depends/{infrastructure.py,application.py}
    └── http/
        ├── router.py, boundary.py
        └── label/{controller,requests,responses}/
```

Добавить `__init__.py` и публичные экспорты. Queries используют `query/repository.py`, когда
нужен отдельный read contract. Pydantic находится в requests/responses. Модульного `unit_of_work.py` нет.

## 11. Console

### Виджет и композиция компонентов

Реализовать `ContactPointsWidget` в `frontends/apps/console/src/modules/contact-points/ui/`.
Это составной предметный виджет для форм Company, Contact и будущих владельцев. Он объединяет
два независимо переиспользуемых компонента `PhoneContactPointsField` и `EmailContactPointsField`.
Экспортировать виджет, оба поля и frontend-типы через публичный `index.ts` модуля.

```text
ContactFormDialog / CompanyFormDialog / форма будущего объекта
  └─ ContactPointsWidget
      ├─ PhoneContactPointsField
      │   └─ строки: страна + телефон + подпись + удалить
      └─ EmailContactPointsField
          └─ строки: email + подпись + удалить
```

Виджет и поля **составляются из существующих простых shadcn-vue компонентов** из
`@/components/ui`; предметные правила не добавляются в базовые UI components.

| Элемент виджета | Переиспользуемые компоненты |
| --- | --- |
| Группа телефонов/email | `FieldSet`, `FieldLegend`, `FieldGroup` |
| Строка и сообщения валидации | `Field`, `FieldLabel`, `FieldError` |
| Телефон с кодом страны | `InputGroup`, `InputGroupAddon`, `InputGroupInput` с `type="tel"` |
| Поиск и выбор страны | Существующий `Combobox` с его `Anchor`, `Input`, `List`, `Group`, `Item`, `Empty`; trigger находится в addon |
| Email | `Input` с `type="email"` |
| Подпись связи | `Select`, `SelectTrigger`, `SelectValue`, `SelectContent`, `SelectGroup`, `SelectItem` |
| Добавление/удаление строки | `Button`, иконки из используемого `@lucide/vue`, `Tooltip` для кнопки удаления |
| Ошибка загрузки справочника и повтор | `Alert`, `AlertDescription`, `Button`; во время загрузки — `Spinner` |

Перечисленные примитивы уже есть в проекте. Использовать их текущие public exports и Vue API;
не устанавливать React-версию shadcn и не копировать существующие controls в новый модуль.
Внутри `InputGroup` использовать `InputGroupInput`, а не обычный `Input`. Страны показывать
с названием, кодом и флагом; поиск должен работать по названию и телефонному коду.

### Контракт и управление состоянием

- `ContactPointsWidget` получает `v-model:phones` и `v-model:emails`; отдельные поля получают
  массив через обычный `v-model`. Дополнительные props: options подписей по типам, `disabled`,
  `pending`, состояние загрузки/ошибки options и построчные ошибки. Повтор загрузки — событие родителю.
- Frontend draft-строка содержит стабильный `clientKey`, optional `bindingId`, `value`,
  optional `labelId`; телефон также содержит `countryCode`. `clientKey` служит ключом рендера
  и ошибок, не отправляется в API. Не использовать индекс массива как Vue key.
- Виджет не знает `model_key`, tenant, id владельца, CRM API или backend VO. Он выдаёт обновлённые
  массивы без прямой мутации props и без HTTP-запросов. Это позволяет использовать его до создания объекта.
- CRM-контейнер получает справочники через query hooks нового модуля, передаёт options и
  сохраняет карточку вместе с массивами существующей CRM mutation. Только контейнер отвечает
  за загрузку, сохранение, уведомления и invalidation соответствующих query caches.
- Новая строка телефона начинается с `UA`, email — с пустого значения; подпись изначально не выбрана.
  Пустой массив допустим. Добавленная пустая строка требует заполнения или явного удаления;
  её нельзя молча отбросить при сохранении.
- Поля выполняют предварительную валидацию на blur и при попытке сохранения; форма получает
  событие `validation-change` с текущей валидностью и передаёт признак попытки submit для показа ошибок.
  Серверная валидация остаётся окончательной. Ответные ошибки по индексам сопоставляются с
  `clientKey` снимка отправленных массивов, чтобы не попадать на другую строку после удаления.
- При `pending` блокировать изменения строк и повторное сохранение. Отмена отбрасывает черновик,
  ошибка сохранения оставляет ввод. Архивная подпись существующей строки отображается, но не
  предлагается для новых назначений. Ошибка загрузки options не очищает текущие labelId или массивы.

### Интеграция, доступность и настройки

Встроить виджет в существующие create/edit dialogs Company и Contact. Backend GET/list читает
массивы пакетно. На узком экране элементы строки переносятся вертикально без горизонтального скролла.
Использовать существующие semantic tokens, размеры и варианты компонентов.

Каждая строка получает уникальные id и связанные labels; ошибки используют `data-invalid`,
`aria-invalid`, `aria-describedby`. Кнопки добавить/удалить имеют `type="button"`, у удаления есть
доступное текстовое имя. После добавления фокус переходит в новую строку, после удаления —
в соседнюю строку или кнопку добавления. Выбор страны и подписи доступен с клавиатуры.

Добавить `/admin/contact-points` в существующий AdminLayout и навигацию с вкладками «Телефоны»
и «Email» на компонентах `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`.
Подписями управляет администратор там; шестерёнка в строке не нужна.
После изменений обновлять соответствующие TanStack Query caches.

## 12. Миграция и внедрение

1. Зарегистрировать модели и исторические имена таблиц в `src/modules/tenant_persistence.py`.
2. Добавить tenant revision после текущего `0007_crm_contacts_companies` (проверить head перед
   реализацией). Явный DDL, без импорта runtime ORM и фиксированной tenant-схемы.
3. Создать три таблицы, ограничения и начальные подписи. Seed ревизии использует фиксированные
   UUID и timestamp. Для миграционных подписей actor-поля допускают null, поскольку у DDL нет
   пользователя; обычные операции записывают actor из контекста. Points/bindings создаются с actor.
4. Новые tenant получают схему через существующий bootstrap до head; существующие — через
   `dnk-manage tenant-migrations upgrade`. Ревизия не делает commit/autocommit.
5. Выполнить upgrade существующих tenant перед запуском кода, требующего новые таблицы.
   CRM-данные сохраняются; у существующих карточек изначально пустые массивы.

Backfill/dual-write не нужны: текущие Contact/Company не имеют legacy phone/email, Lead отсутствует.
Не переносить identity `user_emails` — это другой bounded context. Внешний импорт и Record Registry
требуют отдельного плана: target abstraction не гарантирует миграцию без изменения API.

Обновить документацию CRM/HTTP и boundary tests: разрешить новый `contact_points` и его маршруты,
сохранив запрет на старый `contact_point`, динамические модули и legacy attach routes.

## 13. Проверки и порядок реализации

- Domain: нормализация, страна, регистр email, immutable canonical value, rebind с прежним id,
  типы подписей, позиции и дубликаты.
- Use cases: sync, omitted/empty массивы, ошибки строк, чужой binding, удаление владельца,
  batch read и reverse lookup без создания точек.
- DI smoke: CRM, points, bindings и labels получают одну UoW/session; use cases получают готовые
  Protocol dependencies; вложенные операции не коммитят.
- PostgreSQL: ошибка после записи CRM/части bindings откатывает весь запрос; параллельный resolve
  даёт одну точку; update/delete одного владельца не оставляют висящих связей; одинаковые UUID
  и значения в разных tenant изолированы.
- HTTP: CSRF, tenant/actor из контекста, admin-only изменения labels, корректные 4xx,
  атомарное сохранение карточки и отсутствие частичного успеха.
- Миграции: новый tenant, upgrade существующего без потери CRM-данных, initial labels и rollback
  bootstrap. Использовать disposable PostgreSQL через `TEST_POSTGRES_URL`.
- Архитектурные проверки: отсутствие SQLAlchemy/FastAPI/Pydantic в domain/application нового модуля,
  отсутствие импорта CRM из contact_points и contact_points из Shared, соблюдение направлений адаптеров;
  CRM application использует собственный порт/DTO, преобразование публичных контрактов тестируется у адаптера.
- Console: typecheck/lint/build, браузерная проверка форм, отмены, ошибок, административных вкладок
  и мобильной компоновки. Проверить каждое поле отдельно и в общем виджете, отсутствие HTTP mutations
  при редактировании черновика, стабильность строк/ошибок после удаления, keyboard focus, пустые строки,
  загрузку/сбой справочника и сохранение архивной подписи. При подключении integration events — тест атомарности outbox.

Порядок: domain/contracts → normalizers → persistence/migration → use cases/DI → CRM adapter
и атомарные сценарии → HTTP/Console → проверки и документация. Отдельный UoW, broker,
Record Registry или восстановление dynamic objects для этого не требуются.
