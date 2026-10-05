# Архитектурные правила проекта

## Бекенд

### Основы архитектуры

Проект строится по принципам **Domain-Driven Design + Clean Architecture**.

В `src/modules/` находятся бизнес-модули. Каждый модуль описывает отдельный
контекст предметной области (**bounded context**) и объединяет тесно связанные
Aggregate Roots, которые сохраняют самостоятельность.

Например, модуль `crm` описывает CRM-контекст, а `ContactEntity` и `Company` — два
самостоятельных корня агрегатов внутри него. У каждого свои идентификатор,
жизненный цикл, инварианты и контракт репозитория. Принадлежность одному контексту
не делает компанию частью агрегата контакта или контакт частью агрегата компании.

Примеры ниже — сокращённый псевдокод: импорты и вспомогательные реализации могут
быть опущены. Docstring внутри классов и методов объясняют их назначение и
поведение на русском языке; комментарии поясняют короткие вызовы и антипримеры.
`...` обозначает пропущенную реализацию, а не готовый production-код.

```text
src/modules/
├── crm/
├── orders/
├── catalog/
├── payments/
└── contact_points/
```

Каждый бизнес-модуль делится на четыре слоя. Внутри каждого слоя код группируется
по Aggregate Root, к которому он относится:

```text
src/modules/<module>/<layer>/<aggregate_root>/<responsibility>/
```

Например, `src/modules/crm/application/contact/command/` содержит команды и
обработчики сценариев контакта. `company/` находится рядом с `contact/` внутри
того же слоя, а не становится отдельным модулем со своими четырьмя слоями.

Класс Aggregate Root и его бизнес-инварианты определяются в `domain/<aggregate_root>/`.
Одноимённые каталоги в остальных слоях содержат сценарии Application, адаптеры
Infrastructure и интерфейсы Presentation этого агрегата. Это организация кода
вокруг одного Aggregate Root, а не четыре независимые реализации бизнес-модели.

Если модуль содержит ровно один корень агрегата, дополнительный одноимённый каталог
в каждом слое не нужен: код располагается прямо в `domain/`, `application/`,
`infrastructure/` и `presentation/`. Так устроен `contact_points`: `ContactPoint` —
корень, а binding и label находятся рядом как связанные сущности и настройки.
Сценарии по-прежнему разделяются в `application/command/<scenario>/` и
`application/query/<scenario>/`; SQL-адаптеры лежат в `infrastructure/persistence/`,
HTTP-контроллеры — в `presentation/http/controller/`.

#### Направление зависимостей

Допустимое направление:

```text
Presentation
      │
      ▼
Application
      │
      ▼
Domain


Infrastructure
      │
      ├────────► Application contracts
      │
      └────────► Domain contracts
```

Главное правило:

```text
Domain ничего не знает о внешних слоях.
```

То есть запрещено:

```text
domain → application
domain → infrastructure
domain → presentation

application → infrastructure
```

Допускается:

```text
application → domain

infrastructure → domain
infrastructure → application

presentation → application
```

Infrastructure является адаптером для интерфейсов, объявленных во внутренних слоях.

Внешняя сборка зависимостей (`presentation/depends`, composition root) может
импортировать конкретные Infrastructure adapters, чтобы связать их с Application.
В ней открывается UoW и его сессия передаётся репозиториям.

Контракты Application не импортируют SQLAlchemy и не раскрывают `AsyncSession`,
ORM models или session factory. Контракт UoW предоставляет управление транзакцией;
дополнительные зависимости в нём допустимы только как абстрактные порты без
инфраструктурных типов. Создание сессии и подключение репозиториев остаются снаружи.

#### Владение контекстом пользователя

Модуль `identity` владеет `Principal`, `RequestContext`, HTTP-аутентификацией и
зависимостями авторизации. HTTP-контроллеры других модулей импортируют
`AuthenticatedRequestContextDep` и `OptionalRequestContextDep` напрямую из
`src.modules.identity.presentation.auth.depends`, а `AuthorizationServiceDep` —
из `src.modules.identity.presentation.access.depends`. Domain-типы импортируются
из отдельных файлов `identity/domain/auth/`. Пакеты Identity не реэкспортируют
определения через `__init__.py`.

Сценарии Identity размещаются в `application/<responsibility>/command|query/<scenario>/`:
входной объект, `handler.py` с `execute(...)`, `dto.py`. `auth`, `access`, `cloud`
и `email` обозначают ответственность, а не новые Aggregate Roots. Общие операции
находятся в небольших Application services; обработчики не вызывают друг друга.

Зависимость контекста напрямую вызывает `AuthenticateBySessionHandler.execute` и
преобразует результат в `Principal`. Подмена обработчика выполняется через FastAPI
`dependency_overrides` для `get_authenticate_by_session_handler`; подмена готового
контекста — через `require_authenticated_request_context`. Транспортные Request/Depends
типы остаются в Presentation. Tenant context adapter принимает Application use case
Tenancy и переводит его ошибки в собственные ошибки порта Identity.

Чистая нормализация host находится в `shared/application/network/host.py` и доступна
внутренним слоям без импорта HTTP Presentation. Извлечение host из Request остаётся
HTTP-функцией. Подробная структура и диаграмма приведены в [Identity](../modules/identity.md).

Универсальные TokenManager, Redis-backend, доставка готовых email, UoW и jobs/events
остаются в `shared`. Виды писем OTP/приглашений, их переменные, шаблоны и сборка
сервиса принадлежат Identity; общий транспорт не импортирует их.

Tenancy владеет именованием tenant-схем, `TenantBase`, tenant-миграциями и admission.
Tenancy также владеет системным списком локалей и выбранным набором локалей каждого
tenant. Catalog и Channels проверяют выбор через Application-контракт Tenancy и
не читают его SQL-модель напрямую.
Глобальными read-only справочниками стран, валют, BCP 47 локалей и IANA временных
зон владеет модуль `reference_data`. Их SQL-модели находятся в `public`, а обновление
выполняют внутренние Application-сценарии через порты источников. Список локалей
Tenancy пока остаётся отдельным ограниченным набором для выбора tenant.
Пакеты Tenancy также имеют пустые `__init__.py`. Общая блокировка Alembic остаётся
в shared и используется обоими миграторами. Общие mixins не содержат правил
жизненного цикла tenant; `TitledEntityAuditMixin` остаётся в shared.

Control Plane владеет management trust policy и mTLS-метрикой. Общая обработка
proxy-заголовков вызывается после проверки исходного peer и сертификата;
затем выполняются tenant admission и HTTP dependencies. UoW переиспользует
соединение admission и завершает транзакцию до отправки ответа.
Tenancy привязывает `schema_translate_map` к этому соединению до создания сессии
UoW. Репозитории tenant-моделей получают общую сессию и не выбирают схему в
каждом SQL-выражении; один UoW работает с одним tenant.

#### Структура модуля

Целевая структура модуля CRM с самостоятельными агрегатами `ContactEntity` и `Company`:

```text
src/modules/crm/
├── domain/
│   ├── contact/
│   │   ├── aggregate.py
│   │   ├── value_object/
│   │   │   ├── identifier.py
│   │   │   ├── name.py
│   │   │   └── company_link.py
│   │   ├── error.py
│   │   └── repository.py
│   └── company/
│       ├── aggregate.py
│       ├── value_object/
│       │   ├── identifier.py
│       │   └── legal_name.py
│       ├── error.py
│       └── repository.py
├── application/
│   ├── contact/
│   │   ├── command/
│   │   │   ├── create_contact/
│   │   │   │   ├── command.py
│   │   │   │   ├── handler.py
│   │   │   │   └── dto.py
│   │   │   ├── update_contact/
│   │   │   │   ├── command.py
│   │   │   │   ├── handler.py
│   │   │   │   └── dto.py
│   │   │   ├── delete_contact/
│   │   │   │   ├── command.py
│   │   │   │   └── handler.py
│   │   │   ├── link_company/
│   │   │   │   ├── command.py
│   │   │   │   └── handler.py
│   │   │   └── unlink_company/
│   │   │       ├── command.py
│   │   │       └── handler.py
│   │   ├── query/
│   │   │   ├── get_contact/
│   │   │   │   ├── query.py
│   │   │   │   ├── handler.py
│   │   │   │   └── dto.py
│   │   │   ├── list_contacts/
│   │   │   │   ├── query.py
│   │   │   │   ├── handler.py
│   │   │   │   └── dto.py
│   │   │   └── list_companies/
│   │   │       ├── query.py
│   │   │       ├── handler.py
│   │   │       └── dto.py
│   │   └── port/
│   │       ├── query_repository.py
│   │       ├── company_link_repository.py
│   │       └── company_link_query_repository.py
│   └── company/
│       ├── command/
│       │   ├── create_company/
│       │   │   ├── command.py
│       │   │   ├── handler.py
│       │   │   └── dto.py
│       │   ├── update_company/
│       │   │   ├── command.py
│       │   │   ├── handler.py
│       │   │   └── dto.py
│       │   └── delete_company/
│       │       ├── command.py
│       │       └── handler.py
│       ├── query/
│       │   ├── get_company/
│       │   │   ├── query.py
│       │   │   ├── handler.py
│       │   │   └── dto.py
│       │   ├── list_companies/
│       │   │   ├── query.py
│       │   │   ├── handler.py
│       │   │   └── dto.py
│       │   └── list_contacts/
│       │       ├── query.py
│       │       ├── handler.py
│       │       └── dto.py
│       └── port/
│           ├── query_repository.py
│           └── contact_link_query_repository.py
├── infrastructure/
│   ├── contact/
│   │   └── persistence/
│   │       ├── mapper.py
│   │       ├── repository.py
│   │       ├── query_repository.py
│   │       ├── query_mapper.py
│   │       ├── company_link_repository.py
│   │       └── company_link_query_repository.py
│   ├── company/
│   │   └── persistence/
│   │       ├── mapper.py
│   │       ├── repository.py
│   │       ├── query_mapper.py
│   │       ├── query_repository.py
│   │       └── contact_link_query_repository.py
│   └── persistence/
│       └── models/
│           ├── contact.py
│           ├── company.py
│           └── contact_company.py
└── presentation/
    ├── contact/
    │   ├── router.py
    │   ├── depends.py
    │   └── http/
    │       ├── controller/
    │       │   ├── create_contact.py
    │       │   ├── get_contact.py
    │       │   ├── list_contacts.py
    │       │   ├── put_contact.py
    │       │   ├── patch_contact.py
    │       │   ├── delete_contact.py
    │       │   ├── link_company.py
    │       │   ├── unlink_company.py
    │       │   └── list_companies.py
    │       ├── request/
    │       │   ├── create_contact.py
    │       │   ├── put_contact.py
    │       │   └── patch_contact.py
    │       └── response/
    │           ├── create_contact.py
    │           ├── get_contact.py
    │           ├── list_contacts.py
    │           ├── put_contact.py
    │           ├── patch_contact.py
    │           └── list_companies.py
    ├── company/
    │   ├── router.py
    │   ├── depends.py
    │   └── http/
    │       ├── controller/
    │       │   ├── create_company.py
    │       │   ├── get_company.py
    │       │   ├── list_companies.py
    │       │   ├── put_company.py
    │       │   ├── patch_company.py
    │       │   ├── delete_company.py
    │       │   ├── link_contact.py
    │       │   ├── unlink_contact.py
    │       │   └── list_contacts.py
    │       ├── request/
    │       │   ├── create_company.py
    │       │   ├── put_company.py
    │       │   └── patch_company.py
    │       └── response/
    │           ├── create_company.py
    │           ├── get_company.py
    │           ├── list_companies.py
    │           ├── put_company.py
    │           ├── patch_company.py
    │           └── list_contacts.py
    └── depends/
        └── company_link.py
```

Основной порядок каталогов: **модуль → слой → Aggregate Root → назначение**.
Поэтому команда контакта находится в `crm/application/contact/command/`,
а не в `crm/contact/application/command/` или `crm/application/command/contact/`.

Общие для нескольких агрегатов элементы остаются на уровне соответствующего слоя:
например, сборка зависимостей в `presentation/depends/` и сохранённые SQL-модели
CRM в `infrastructure/persistence/models/`. Каждая SQL-модель находится в отдельном
файле и импортируется напрямую; `__init__.py` не используется для реэкспортов.
Общая папка хранения не объединяет агрегаты и не определяет их границы.
Таблица связи `contact_companies` сама по себе не означает отдельный Aggregate Root.

Взаимодействие самостоятельных агрегатов внутри контекста координируется в
Application через их контракты. Каждый агрегат изменяет своё состояние через
собственные domain-методы и ссылается на другие агрегаты по идентификаторам.
Чистые правила, относящиеся к нескольким агрегатам, могут находиться в Domain Service
или Policy; принадлежность одному модулю не отменяет границы агрегатов.

Дерево показывает правило организации слоёв CRM. Для Contact и Company
реализованы создание, чтение списка и карточки, полное и частичное обновление,
удаление. Связь между ними реализована без третьего Aggregate Root: одна пара
ID хранится в `contact_companies`, запись принадлежит сценарию Contact, а
обратное чтение — проекции Company. Актуальное поведение описано в
[документации CRM](../modules/crm.md). Пустые каталоги заранее не создаются —
элементы добавляются по мере реализации соответствующего поведения.

### Слои модуля

#### Domain layer

`domain` содержит бизнес-модель и правила предметной области.

Domain не должен знать:

```text
SQLAlchemy
FastAPI
Django
Redis
Kafka
HTTP
Pydantic
Celery
JSON API
PostgreSQL
```

Domain должен быть максимально обычным Python.

##### Aggregate Root

Метод `__post_init__` разрешён **только в Value Objects (VO)**.
В Aggregate Root, Entity, Command, Query и DTO использовать его запрещено.

Проверки при создании агрегата выполняются в его явной фабрике, например `create(...)`.
Проверки переходов состояния — в публичных domain-методах агрегата.
При восстановлении сохранённого агрегата, если нужны проверки, используется
явная фабрика восстановления. Валидация отдельных значений остаётся в VO;
инварианты агрегата не переносятся в VO или в persistence mapper.

В модуле `Orders` одним из Aggregate Roots может быть `Order`.
Далее показан его код из `src/modules/orders/domain/order/aggregate.py`.

```python
@dataclass(slots=True)
class Order:
    """Корень агрегата заказа: управляет позициями, статусом и доменными событиями."""
    id: OrderIdVO
    customer_id: EntityIdVO
    status: OrderStatus
    items: list[OrderItem]

    created_at: datetime
    updated_at: datetime

    _events: list[DomainEvent] = field(
        default_factory=list,
        init=False,
    )

    @classmethod
    def create(
        cls,
        *,
        order_id: OrderIdVO,
        customer_id: EntityIdVO,
        created_at: datetime,
    ) -> "Order":
        """Создаёт пустой черновик заказа и накапливает событие его создания."""
        order = cls(
            id=order_id,
            customer_id=customer_id,
            status=OrderStatus.DRAFT,
            items=[],
            created_at=created_at,
            updated_at=created_at,
        )

        order._events.append(
            OrderCreated(
                order_id=order.id,
                customer_id=customer_id,
            )
        )

        return order

    def add_item(
        self,
        *,
        product_id: EntityIdVO,
        quantity: QuantityVO,
        price: MoneyVO,
    ) -> None:
        """Добавляет позицию в черновик или увеличивает количество уже выбранного товара."""
        self._ensure_editable()

        existing = self._find_item(product_id)

        if existing is not None:
            existing.increase(quantity)
            return

        self.items.append(
            OrderItem.create(
                product_id=product_id,
                quantity=quantity,
                price=price,
            )
        )

    def remove_item(
        self,
        product_id: EntityIdVO,
    ) -> None:
        """Проверяет возможность редактирования; удаление позиции в примере опущено."""
        self._ensure_editable()

        ...

    def confirm(self) -> None:
        """Подтверждает непустой черновик и накапливает событие подтверждения."""
        if self.status is not OrderStatus.DRAFT:
            raise OrderAlreadyConfirmedError()

        if not self.items:
            raise EmptyOrderCannotBeConfirmedError()

        self.status = OrderStatus.CONFIRMED

        self._events.append(
            OrderConfirmed(
                order_id=self.id,
            )
        )

    def calculate_total(self) -> MoneyVO:
        """Вычисляет сумму стоимостей всех позиций заказа."""
        return sum(
            item.total
            for item in self.items
        )

    def pull_events(
        self,
    ) -> tuple[DomainEvent, ...]:
        """Возвращает накопленные события и очищает внутреннюю очередь агрегата."""
        events = tuple(self._events)
        self._events.clear()
        return events

    def _ensure_editable(self) -> None:
        """Запрещает изменение заказа, если он уже вышел из состояния черновика."""
        if self.status is not OrderStatus.DRAFT:
            raise OrderCannotBeModifiedError()
```

Правило:

```text
Изменение состояния Aggregate Root происходит
только через его публичные domain-методы.
```

Не писать:

```python
# Антипример: прямое присваивание обходит проверки и события агрегата.
order.status = OrderStatus.CONFIRMED
```

из Application Service.

Правильно:

```python
# Публичный метод агрегата проверяет инварианты и фиксирует доменное событие.
order.confirm()
```

##### Entity внутри Aggregate

Например `OrderItem`.

```python
@dataclass(slots=True)
class OrderItem:
    """Позиция заказа, жизненным циклом которой управляет агрегат Order."""
    id: OrderItemIdVO
    product_id: EntityIdVO

    quantity: QuantityVO
    unit_price: MoneyVO

    @classmethod
    def create(
        cls,
        *,
        product_id: EntityIdVO,
        quantity: QuantityVO,
        price: MoneyVO,
    ) -> "OrderItem":
        """Создаёт позицию с новым идентификатором, количеством и ценой за единицу."""
        return cls(
            id=OrderItemIdVO.generate(),
            product_id=product_id,
            quantity=quantity,
            unit_price=price,
        )

    @property
    def total(self) -> MoneyVO:
        """Возвращает стоимость позиции: цену за единицу, умноженную на количество."""
        return self.unit_price * self.quantity.value

    def increase(
        self,
        quantity: QuantityVO,
    ) -> None:
        """Увеличивает количество товара, создавая новое значение QuantityVO."""
        self.quantity = self.quantity + quantity
```

`OrderItem` не имеет собственного Repository, если его lifecycle полностью принадлежит `Order`.

Нельзя загружать:

```python
# Антипример: внутреннюю позицию нельзя загружать отдельно от её агрегата.
OrderItemRepository.get(item_id)
```

если `OrderItem` является внутренней entity агрегата.

Он загружается через:

```python
# Заказ загружается вместе с принадлежащими ему позициями.
OrderRepository.get(order_id)
```

##### Value Objects

В VO можно использовать `__post_init__` для проверки и нормализации собственного
значения. Это единственное допустимое место использования `__post_init__`;
правила жизненного цикла агрегата проверяются его фабриками и domain-методами.

Value Object должен описывать значение, а не строку/число технически.

Например:

```python
@dataclass(
    frozen=True,
    slots=True,
)
class QuantityVO:
    """Неизменяемое положительное количество товара с проверкой при создании."""
    value: int

    def __post_init__(self) -> None:
        """Отклоняет нулевое и отрицательное количество как нарушение бизнес-правила."""
        if self.value <= 0:
            raise InvalidQuantityError()

    def __add__(
        self,
        other: "QuantityVO",
    ) -> "QuantityVO":
        """Возвращает сумму двух количеств, не изменяя исходные объекты."""
        return QuantityVO(
            self.value + other.value
        )
```

Другой пример:

```python
class OrderStatus(StrEnum):
    """Перечисляет допустимые состояния заказа; переходами управляет агрегат."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
```

Value Objects желательно делать immutable.

##### Domain Errors

Ошибки бизнес-правил принадлежат Domain.

```python
class OrderError(DomainError):
    """Базовая ошибка бизнес-операций с заказом."""
    pass


class OrderNotFoundError(OrderError):
    """Сообщает, что запрошенный заказ не найден."""
    pass


class EmptyOrderCannotBeConfirmedError(OrderError):
    """Сообщает о запрете подтверждать заказ без позиций."""
    pass


class OrderCannotBeModifiedError(OrderError):
    """Сообщает о запрете редактировать заказ в текущем состоянии."""
    pass
```

Не использовать:

```python
# Антипример: эти типы не выражают предметные ошибки публичного Domain API.
HTTPException
IntegrityError
ValueError
```

как публичные бизнес-ошибки domain layer.

##### Domain Events

Domain Event описывает факт, который уже произошёл.

```python
@dataclass(
    frozen=True,
    slots=True,
)
class OrderConfirmed(DomainEvent):
    """Неизменяемый факт подтверждения заказа, ещё не означающий commit в БД."""
    order_id: OrderIdVO
```

Aggregate создаёт событие:

```python
def confirm(self) -> None:
    """Меняет статус и накапливает событие; проверки инвариантов здесь опущены."""
    ...

    self.status = OrderStatus.CONFIRMED

    self._events.append(
        OrderConfirmed(
            order_id=self.id,
        )
    )
```

Domain Event не должен сам:

```text
отправлять email
писать Kafka
делать HTTP
писать в БД
```

##### Domain Repository

Domain Repository работает с Aggregate Root.

Контракт расположен в `domain`.

```python
class OrderRepositoryProtocol(Protocol):

    """Определяет операции хранения и загрузки агрегата в контексте tenant."""
    async def get(
        self,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:
        """Загружает заказ с его позициями или выбрасывает OrderNotFoundError."""
        ...

    async def add(
        self,
        tenant_id: EntityIdVO,
        order: Order,
    ) -> None:
        """Добавляет новый агрегат в текущую транзакцию без самостоятельного commit."""
        ...

    async def save(
        self,
        tenant_id: EntityIdVO,
        order: Order,
    ) -> None:
        """Сохраняет состояние существующего агрегата в текущей транзакции без commit."""
        ...
```

Repository возвращает:

```python
# Контракт записи возвращает полноценный доменный агрегат.
Order
```

а не:

```python
# Антипример: представления хранения и DTO не заменяют агрегат в Domain Repository.
OrderModel
Row
dict
OrderDTO
```

Domain Repository предназначен для изменения бизнес-состояния.

##### Domain Service

Domain Service нужен, если бизнес-операция:

```text
является частью domain;
не принадлежит естественным образом одной Entity;
может участвовать несколько domain objects;
не требует orchestration внешней инфраструктуры.
```

Например политика расчёта цены.

```python
class OrderPricingService:

    """Содержит чистое бизнес-правило расчёта стоимости с учётом скидки."""
    def calculate(
        self,
        *,
        items: tuple[OrderItem, ...],
        discount: DiscountVO | None,
    ) -> MoneyVO:
        """Суммирует стоимость позиций и применяет скидку, если она задана."""
        subtotal = sum(
            item.total
            for item in items
        )

        if discount is None:
            return subtotal

        return discount.apply(subtotal)
```

Domain Service:

```text
не открывает транзакции;
не использует repository;
не делает HTTP;
не знает SQLAlchemy;
не вызывает payment gateway.
```

Он содержит именно domain logic.

Другой вариант — domain policy:

```python
class OrderConfirmationPolicy:

    """Проверяет условия подтверждения по заказу и снимку данных клиента."""
    def ensure_can_confirm(
        self,
        order: Order,
        customer: CustomerSnapshot,
    ) -> None:
        """Запрещает заказ заблокированному клиенту и подтверждение нулевой суммы."""
        if customer.is_blocked:
            raise CustomerCannotPlaceOrderError()

        if order.calculate_total().is_zero:
            raise ZeroTotalOrderError()
```

##### Aggregate boundary

При проектировании нового функционала агент сначала должен определить Aggregate Root.

Например:

```text
Order
 ├── OrderItem
 ├── OrderDiscount
 └── OrderAddressSnapshot
```

Если `OrderItem` не может существовать независимо:

```text
OrderItem lifecycle = Order lifecycle
```

значит он находится внутри Aggregate.

Другой Aggregate:

```text
Payment
```

может ссылаться:

```python
# Другой агрегат хранит идентификатор заказа как ссылку на его границу.
order_id: OrderIdVO
```

но не должен содержать прямой Python reference:

```python
# Антипример: прямая ссылка на объект связывает жизненные циклы разных агрегатов.
payment.order: Order
```

Связи между Aggregate Roots осуществляются через IDs.

##### Domain snapshots

Если Domain Order должен использовать информацию из другого context, но она нужна для принятия domain decision, использовать специализированный immutable snapshot.

Например:

```python
@dataclass(
    frozen=True,
    slots=True,
)
class CustomerOrderSnapshot:
    """Хранит неизменяемый снимок данных клиента, нужных для бизнес-решения Order."""
    customer_id: EntityIdVO
    is_blocked: bool
    customer_type: CustomerType
```

А не передавать:

```python
# Антипример: чужой агрегат не передаётся в Domain вместо специализированного снимка.
CustomerAggregate
```

из другого bounded context.

#### Application layer

Application отвечает за use cases.

Он:

```text
принимает Command/Query;
загружает Aggregate;
вызывает domain methods;
координирует repositories;
координирует external ports;
при необходимости явно управляет commit/rollback через контракт UoW;
возвращает DTO/result.
```

По умолчанию UoW открывается во внешней сборке Depends, передаёт свою сессию
репозиториям и завершает транзакцию после выполнения процесса: commit при успехе,
rollback при исключении. Обычный Use Case получает только необходимые порты.
UoW передаётся в Use Case только при необходимости управлять моментом commit/rollback.

Application не должен содержать бизнес-инварианты.

Плохо:

```python
# Антипример: Application дублирует бизнес-правило и меняет состояние напрямую.
if order.status == "draft" and len(order.items) > 0:
    order.status = "confirmed"
```

Правильно:

```python
# Application делегирует проверку и переход состояния самому агрегату.
order.confirm()
```

##### Command

Command описывает намерение изменить систему.

```python
@dataclass(
    frozen=True,
    slots=True,
)
class ConfirmOrderCommand:
    """Передаёт намерение подтвердить заказ с контекстом tenant и инициатора."""
    tenant_id: EntityIdVO
    order_id: OrderIdVO
    actor_id: EntityIdVO
```

Command не содержит SQLAlchemy model или HTTP Request.

##### Command Handler

Обычный handler работает внутри UoW, уже открытого в Depends.

```python
class ConfirmOrderHandler:

    """Координирует подтверждение и запись Outbox в уже открытой транзакции."""
    def __init__(
        self,
        *,
        repository: OrderRepositoryProtocol,
        outbox: OutboxRepositoryProtocol,
    ) -> None:
        """Принимает порты заказа и Outbox, собранные на одной сессии внешнего UoW."""
        self._repository = repository
        self._outbox = outbox

    async def execute(
        self,
        command: ConfirmOrderCommand,
    ) -> None:

        """Подтверждает заказ, сохраняет его и сообщения Outbox; commit выполняется снаружи."""
        order = await self._repository.get(
            tenant_id=command.tenant_id,
            order_id=command.order_id,
        )

        order.confirm()

        await self._repository.save(
            tenant_id=command.tenant_id,
            order=order,
        )

        for event in order.pull_events():
            await self._outbox.add(
                order_event_to_integration_event(
                    event,
                    tenant_id=command.tenant_id,
                )
            )
```

`order_event_to_integration_event` в примере — Application mapping доменного
события в контракт интеграционного сообщения. Он не выполняет I/O.
Order Repository и Outbox Repository используют одну сессию и транзакцию UoW.

Handler отвечает за сценарий:

```text
load
↓
invoke domain
↓
persist
↓
записать сообщения в Outbox
```

Commit выполняется при успешном завершении внешнего UoW context.
При исключении откатываются и изменения заказа, и сообщения Outbox.
Handler не реализует правило `можно ли подтвердить заказ`.

##### Application Service

Application Service используется, когда use case сложнее простого handler.

Например:

```python
class OrderApplicationService:

    """Координирует порты и агрегат, оставляя бизнес-решения в Domain."""
    def __init__(
        self,
        *,
        order_repository: OrderRepositoryProtocol,
        inventory: InventoryGatewayProtocol,
        payment: PaymentGatewayProtocol,
    ) -> None:
        """Принимает порты хранения, склада и оплаты; порт оплаты в этом сценарии не вызван."""
        self._orders = order_repository
        self._inventory = inventory
        self._payment = payment

    async def confirm(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:

        """Проверяет наличие товаров через порт, вызывает Domain и сохраняет заказ без commit."""
        order = await self._orders.get(
            tenant_id,
            order_id,
        )

        availability = await self._inventory.check(
            order.product_requirements
        )

        order.ensure_inventory_available(
            availability
        )

        order.confirm()

        await self._orders.save(
            tenant_id,
            order,
        )

        return order
```

Application Service координирует.

Domain принимает решения.

Пример показывает координацию внутри уже открытого внешней сборкой UoW.
Если сценарий создаёт интеграционные сообщения, до завершения UoW он также
записывает их в Outbox, как в разделе [Command Handler](#command-handler). Вложенный Application Service не открывает
новый UoW и не коммитит общую транзакцию самостоятельно.

##### External Ports

Application не должен импортировать конкретные Stripe, Nova Poshta, Prom, Redis и т.п.

Контракт:

```python
class PaymentGatewayProtocol(
    Protocol
):

    """Определяет независимый от платёжного провайдера контракт авторизации."""
    async def authorize(
        self,
        payment: PaymentRequest,
    ) -> PaymentAuthorization:
        """Запрашивает авторизацию платежа и возвращает результат в терминах Application."""
        ...
```

Infrastructure:

```python
class StripePaymentGateway(
    PaymentGatewayProtocol
):
    """Адаптирует платёжный API Stripe к контракту Application."""

    async def authorize(
        self,
        payment: PaymentRequest,
    ) -> PaymentAuthorization:
        """Вызывает API провайдера; вызов и преобразование ответа в примере опущены."""

        response = await self._client...
        ...
```

Application зависит от:

```python
# Application обращается к абстрактному порту платёжного провайдера.
PaymentGatewayProtocol
```

а не от:

```python
# Антипример: конкретный адаптер не должен становиться зависимостью Application.
StripePaymentGateway
```

##### Query side

Query не должен загружать Aggregate Root только ради отображения страницы.

Например для API:

```text
GET /orders
```

не нужно делать:

```text
SQL
↓
Order aggregate
↓
OrderItem entities
↓
DTO
↓
JSON
```

Read-side может напрямую читать projection.

###### Query DTO

```python
@dataclass(
    frozen=True,
    slots=True,
)
class OrderListItemDTO:
    """Передаёт готовые данные строки списка заказов без поведения Domain."""
    id: UUID
    number: str
    customer_name: str

    status: str

    items_count: int
    total: Decimal
    currency: str

    created_at: datetime
```

Это не Domain Entity.

DTO может быть специально оптимизирован под конкретный экран/API.

###### Query Repository Protocol

Query Repository следует располагать в Application layer.

Например:

```text
src/modules/orders/application/
└── order/
    └── port/
        └── query_repository.py
```

```python
class OrderQueryRepositoryProtocol(
    Protocol
):

    """Определяет чтение проекций для Application без восстановления агрегата."""
    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> OrderDetailsDTO | None:
        """Возвращает детали заказа в контексте tenant или None, если заказа нет."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        filters: OrderListFilters,
        pagination: Pagination,
    ) -> Page[OrderListItemDTO]:
        """Возвращает страницу проекций с учётом tenant, фильтров и параметров пагинации."""
        ...
```

Почему не Domain:

Domain ничего не знает о:

```text
table pages
API projections
filters
sorting
pagination
search results
```

Это application/read concern.

###### Query Handler

```python
@dataclass(
    frozen=True,
    slots=True,
)
class GetOrderQuery:
    """Передаёт параметры чтения деталей конкретного заказа в контексте tenant."""
    tenant_id: EntityIdVO
    order_id: OrderIdVO
```

Handler:

```python
class GetOrderHandler:

    """Выполняет сценарий чтения через порт проекций Application."""
    def __init__(
        self,
        repository: OrderQueryRepositoryProtocol,
    ) -> None:
        """Принимает порт чтения готовых DTO заказов."""
        self._repository = repository

    async def execute(
        self,
        query: GetOrderQuery,
    ) -> OrderDetailsDTO:

        """Возвращает детали заказа или преобразует отсутствие результата в ошибку."""
        result = (
            await self._repository.get_details(
                tenant_id=query.tenant_id,
                order_id=query.order_id,
            )
        )

        if result is None:
            raise OrderNotFoundError()

        return result
```

Query Handler не должен загружать Aggregate Root без необходимости.

#### Infrastructure layer

##### Infrastructure persistence model

SQLAlchemy Model — это persistence representation, а не Domain Entity.

```python
class OrderModel(
    AudienceMixin,
    TenantBase,
):
    """Описывает хранение полей заказа в SQLAlchemy, не реализуя бизнес-поведение."""
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        StringUUID,
        primary_key=True,
    )

    number: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
    )

    customer_id: Mapped[UUID] = mapped_column(
        StringUUID,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        sa.String(3),
        nullable=False,
    )
```

Нельзя передавать:

```python
# Антипример: ORM-модель не должна выходить за пределы Infrastructure.
OrderModel
```

в Application или Domain.

##### Persistence Mapper

Mapper является единственной точкой преобразования persistence representation → Domain.

```python
class OrderMapper:
    """Преобразует представление хранения в Domain и обратно без выполнения I/O."""

    @staticmethod
    def to_domain(
        order_row: Mapping[str, Any],
        item_rows: Sequence[
            Mapping[str, Any]
        ],
    ) -> Order:

        """Восстанавливает сохранённый агрегат с позициями, не создавая событие OrderCreated."""
        return Order(
            id=OrderIdVO.from_value(
                order_row["id"]
            ),
            customer_id=EntityIdVO.from_value(
                order_row["customer_id"]
            ),
            status=OrderStatus(
                order_row["status"]
            ),
            items=[
                OrderItemMapper.to_domain(row)
                for row in item_rows
            ],
            created_at=order_row[
                "created_at"
            ],
            updated_at=order_row[
                "updated_at"
            ],
        )

    @staticmethod
    def to_insert_values(
        order: Order,
    ) -> dict[str, Any]:

        """Извлекает поля заказа в словарь для вставки; сам INSERT не выполняет."""
        return {
            "id": order.id.uuid,
            "customer_id":
                order.customer_id.uuid,
            "status":
                order.status.value,
            "created_at":
                order.created_at,
            "updated_at":
                order.updated_at,
        }
```

Mapper:

```text
не делает SELECT;
не делает INSERT;
не вызывает Repository;
не делает commit;
не содержит business rules.
```

##### Domain Repository implementation

```python
class SqlAlchemyOrderRepository:

    """Загружает агрегат из таблиц, скрывая SQL и ORM от внутренних слоёв."""
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Принимает сессию внешнего UoW с привязанной tenant-схемой."""
        self._session = session

    async def get(
        self,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:

        """Читает заказ и его позиции в контексте tenant, затем восстанавливает агрегат."""
        orders = OrderModel.__table__
        items = OrderItemModel.__table__

        order_result = (
            await self._session.execute(
                select(orders)
                .where(
                    orders.c.id
                    == order_id.uuid
                )
            )
        )

        order_row = (
            order_result
            .mappings()
            .one_or_none()
        )

        if order_row is None:
            raise OrderNotFoundError()

        item_result = (
            await self._session.execute(
                select(items)
                .where(
                    items.c.order_id
                    == order_id.uuid
                )
                .order_by(
                    items.c.position
                )
            )
        )

        return OrderMapper.to_domain(
            order_row,
            tuple(
                item_result.mappings()
            ),
        )
```

Repository отвечает за persistence mechanics.

Aggregate отвечает за business rules.

###### Сохранение Aggregate

При сохранении repository сам разбирает Aggregate на persistence representation.

```python
async def save(
    self,
    tenant_id: EntityIdVO,
    order: Order,
) -> None:

    """Обновляет заказ и заменяет его позиции в общей транзакции, не выполняя commit."""
    orders = OrderModel.__table__
    items = OrderItemModel.__table__

    await self._session.execute(
        update(orders)
        .where(
            orders.c.id
            == order.id.uuid
        )
        .values(
            OrderMapper.to_update_values(
                order
            )
        )
    )

    await self._session.execute(
        delete(items)
        .where(
            items.c.order_id
            == order.id.uuid
        )
    )

    await self._session.execute(
        insert(items),
        [
            OrderItemMapper
            .to_insert_values(
                order.id,
                item,
            )
            for item in order.items
        ],
    )
```

Domain не знает, каким способом Aggregate сохраняется.

##### Query Repository implementation

Infrastructure может выполнять оптимизированный SQL напрямую.

```python
class SqlAlchemyOrderQueryRepository:

    """Читает SQL-проекции заказов и преобразует результат в DTO."""
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Принимает внешнюю сессию с привязанной tenant-схемой."""
        self._session = session

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> OrderDetailsDTO | None:

        """Соединяет таблицы, агрегирует позиции и возвращает DTO либо None."""
        orders = OrderModel.__table__
        customers = CustomerModel.__table__
        items = OrderItemModel.__table__

        statement = (
            select(
                orders.c.id,
                orders.c.number,
                orders.c.status,

                customers.c.name.label(
                    "customer_name"
                ),

                func.count(
                    items.c.id
                ).label("items_count"),

                func.sum(
                    items.c.total
                ).label("total"),

                orders.c.currency,
                orders.c.created_at,
            )
            .select_from(
                orders
                .join(
                    customers,
                    customers.c.id
                    == orders.c.customer_id,
                )
                .outerjoin(
                    items,
                    items.c.order_id
                    == orders.c.id,
                )
            )
            .where(
                orders.c.id
                == order_id.uuid
            )
            .group_by(
                orders.c.id,
                customers.c.name,
            )
        )

        result = await self._session.execute(
            statement
        )

        row = result.mappings().one_or_none()

        if row is None:
            return None

        return OrderQueryMapper.to_details(
            row
        )
```

Это нормальная архитектура.

На Query side допустимы:

```text
JOIN
GROUP BY
CTE
window functions
JSON aggregation
raw SQL при необходимости
materialized views
read replicas
```

Потому что Query Repository не отвечает за восстановление domain state.

###### Query Mapper

```python
class OrderQueryMapper:
    """Преобразует строки SQL-проекции в DTO без запросов к базе данных."""

    @staticmethod
    def to_details(
        row: Mapping[str, Any],
    ) -> OrderDetailsDTO:

        """Собирает детали заказа из именованных полей результата SQL."""
        return OrderDetailsDTO(
            id=row["id"],
            number=row["number"],
            customer_name=row[
                "customer_name"
            ],
            status=row["status"],
            items_count=row[
                "items_count"
            ],
            total=row["total"],
            currency=row["currency"],
            created_at=row[
                "created_at"
            ],
        )
```

Называть:

```python
# Имена отражают создание проекции для чтения, а не доменного объекта.
to_projection()
to_details()
to_list_item()
```

Не называть:

```python
# Антипример: это имя вводит в заблуждение, если метод возвращает DTO.
to_domain()
```

если Domain Entity фактически не создаётся.

##### Unit of Work

Repository не делает:

```python
# Управление транзакцией принадлежит UoW; Repository эти операции не вызывает.
commit()
rollback()
```

По умолчанию жизненным циклом UoW управляет внешняя сборка зависимостей.

1. При сборке Depends открывается UoW и создаётся его SQLAlchemy session.
2. Репозитории процесса, включая Outbox Repository, получают **эту же сессию**.
3. Use Case выполняется через переданные ему абстрактные порты.
4. После успешного выполнения процесса UoW коммитит транзакцию; при исключении
   откатывает её. Ошибка commit не должна превращаться в успешный результат.
5. Сессия закрывается при выходе из UoW context независимо от результата.

Один процесс не должен случайно получить разные UoW/session через разные Depends.
Все его репозитории собираются от одной общей зависимости `get_uow` с обычным
кешированием Depends. Фоновые задачи и CLI открывают собственный UoW во внешней
сборке на время процесса; request-scoped сессия в фоновую задачу не передаётся.

**Application-контракт UoW не зависит от SQLAlchemy:**

```python
from typing import Protocol


class UnitOfWorkProtocol(Protocol):
    """Даёт Application управление уже открытой транзакцией без доступа к сессии."""
    async def commit(self) -> None:
        """Фиксирует текущие изменения; при сбое передаёт исключение вызывающему коду."""
        ...

    async def rollback(self) -> None:
        """Отменяет незавершённые изменения, не затрагивая ранее выполненные commit."""
        ...
```

В этом контракте нет `session`, `AsyncSession`, session factory или методов
открытия контекста. Application получает только управление уже открытой
транзакцией. Если контракту нужны дополнительные зависимости, они описываются
абстрактными портами внутренних слоёв.

Конкретный `UnitOfWork` находится в Infrastructure. Его контекстный менеджер
реализует описанные выше commit/rollback/close, а `session` доступна внешней
сборке для создания репозиториев. Например, в `presentation/depends`:

```python
async def get_uow(request: Request) -> AsyncGenerator[UnitOfWork, None]:
    """Открывает UoW на tenant-соединении и завершает транзакцию до ответа."""
    connection = request.state.tenant_connection
    sessions = async_sessionmaker(connection, expire_on_commit=False)
    async with UnitOfWork(sessions) as uow:
        yield uow


UoWDep = Annotated[UnitOfWork, Depends(get_uow, scope="function")]


def get_order_repository(
    uow: UoWDep,
) -> OrderRepositoryProtocol:
    """Создаёт репозиторий заказов на сессии общего UoW."""
    return SqlAlchemyOrderRepository(uow.session)


def get_outbox_repository(uow: UoWDep) -> OutboxRepositoryProtocol:
    """Подключает Outbox к той же сессии для атомарной записи с заказом."""
    assert uow.session is not None
    return SqlAlchemyOutboxRepository(uow.session)


OrderRepositoryDep = Annotated[
    OrderRepositoryProtocol, Depends(get_order_repository)
]
OutboxRepositoryDep = Annotated[
    OutboxRepositoryProtocol, Depends(get_outbox_repository)
]


def get_confirm_order_handler(
    repository: OrderRepositoryDep,
    outbox: OutboxRepositoryDep,
) -> ConfirmOrderHandler:
    """Собирает обработчик из портов, не передавая ему инфраструктурную сессию."""
    return ConfirmOrderHandler(repository=repository, outbox=outbox)
```

Здесь `request.app.state.db` — настроенная внешним bootstrap фабрика сессий.
Это сокращённый пример сборки; выбор tenant connection также остаётся снаружи.
Конкретный тип `UnitOfWork` в `UoWDep` нужен сборке, а не Application.

**UoW передаётся в Use Case только при необходимости явно контролировать commit
или rollback**, например, зафиксировать данные перед следующим шагом процесса.
Тогда параметр Use Case имеет тип `UnitOfWorkProtocol`, а Depends передаёт тот же
уже открытый UoW, с которым связаны репозитории. Use Case вызывает
`await self._uow.commit()` / `await self._uow.rollback()`, не открывает UoW повторно
и не обращается к его сессии.

Явный commit завершает текущую транзакцию: последующий rollback не отменяет уже
зафиксированные изменения. Все сообщения Outbox для этих изменений должны быть
записаны до этого commit. Если после явного commit/rollback сценарий продолжает
работу с БД, дальнейшие изменения относятся к следующей транзакции и завершаются
внешним UoW по тем же правилам. Ошибки должны доходить до границы UoW; если Use Case
перехватывает ошибку и возвращает результат, он обязан обеспечить rollback
незавершённых изменений, которые нельзя фиксировать.

**Запись сообщения в Outbox должна происходить в одной транзакции с изменением
агрегата, до commit.** Это правило действует и при автоматическом завершении UoW,
и при явном commit из Use Case.

```text
изменить Aggregate
↓
сохранить Aggregate в общей транзакции
↓
записать сообщения в Outbox в этой же транзакции
↓
commit
↓
отдельный publisher доставляет зафиксированные сообщения
```

Запись Outbox после commit или через независимую сессию запрещена: изменение
агрегата и сообщение должны либо сохраниться вместе, либо вместе откатиться.
Создание Domain Event происходит в Domain, преобразование в интеграционное
сообщение — в Application, запись через порт Outbox — в общей транзакции.
Отправка в брокер выполняется отдельно после успешного commit. Publisher должен
поддерживать повторные попытки, а потребители — идемпотентную обработку.

#### Presentation layer

HTTP-слой должен быть тонким и явно разделённым по методам агрегата:

```text
presentation/<aggregate_root>/
├── router.py
├── depends.py
└── http/
    ├── controller/<scenario>.py
    ├── request/<scenario>.py
    └── response/<scenario>.py
```

`router.py` агрегата только регистрирует URL, HTTP-методы, статусы, response
schema при наличии тела ответа и внешние зависимости (например, authentication
и CSRF). Он напрямую
импортирует каждый controller и каждую response schema из файла определения.
`depends.py` собирает обработчики, порты и адаптеры, передавая репозиториям
сессию общего UoW; это composition root, а не место для бизнес-правил.

Каждый HTTP endpoint находится в отдельном файле
`http/controller/<scenario>.py`, например `patch_contact.py`.
Контроллер сам преобразует запрос и доверенный контекст в Command/Query, вызывает
Application handler, переводит ожидаемые ошибки в HTTP-статусы и явно создаёт
свою response schema из DTO. Даже если PUT и PATCH вызывают один Application
handler, их контроллеры остаются самостоятельными: общий HTTP-helper не должен
скрывать состав полей, семантику отсутствующего поля или обработку ошибок.
Повторение небольшого транспортного кода допустимо ради явного контракта метода.
Общие authentication, CSRF и UoW dependencies при этом остаются общими.

Каждая request или response schema определяется в отдельном файле с именем
сценария: `http/request/patch_contact.py`, `http/response/patch_contact.py`.
Схемы разных методов не объединяются только потому, что сегодня имеют одинаковые
поля. Для метода без тела запроса не создаётся фиктивная request schema; для
`204 No Content` не создаётся response schema с пустым телом. Пакетные
`__init__.py` остаются пустыми, импорты идут напрямую из файлов определений.

```python
# presentation/contact/router.py
router.add_api_route(
    "/{contact_id}",
    patch_contact,
    methods=["PATCH"],
    response_model=PatchContactResponse,
    dependencies=[Depends(require_authenticated_request_context), Depends(require_csrf)],
)

# presentation/contact/http/controller/patch_contact.py
async def patch_contact(
    contact_id: UUID,
    payload: PatchContactRequest,
    context: AuthenticatedRequestContextDep,
    handler: UpdateContactHandlerDep,
) -> PatchContactResponse:
    """Преобразует PATCH в команду и возвращает результат через свою HTTP-схему."""
    command = UpdateContactCommand(
        contact_id=ContactIdVO.from_value(contact_id),
        actor_id=EntityIdVO.from_value(context.principal.user_id),
        fields=frozenset(payload.model_fields_set),
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
    )
    result = await handler.execute(command)
    return PatchContactResponse.from_dto(result)
```

Здесь для краткости опущены импорты, проверка tenant-контекста и преобразование
ошибок; рабочая реализация контроллера выполняет их до ответа. Имена файлов,
схем и прямые импорты соответствуют модулю Contact.

Presentation отвечает за:

```text
HTTP request
authentication context
serialization
status codes
request validation
mapping application errors → transport errors
```

Presentation не содержит бизнес-правил.

### Потоки Command и Query

#### Полный путь Command

Для изменения заказа поток должен выглядеть так:

```text
POST /orders/{id}/confirm
        │
        ▼
Presentation
        │
        ▼
Depends: открыть UoW и собрать repositories на его session
        │
        ▼
ConfirmOrderCommand
        │
        ▼
ConfirmOrderHandler
        │
        ▼
OrderRepository.get()
        │
        ▼
Order Aggregate
        │
        ▼
order.confirm()
        │
        ▼
OrderRepository.save()
        │
        ▼
OutboxRepository.add() в той же транзакции
        │
        ▼
UnitOfWork.commit() при успешном завершении процесса
        │
        ▼
Отдельный publisher: доставка сообщений из Outbox
```

При исключении до commit UoW откатывает и изменения агрегата, и записи Outbox.
Если Use Case должен контролировать момент commit, ему передаётся
`UnitOfWorkProtocol` по правилу раздела [Unit of Work](#unit-of-work); порядок записи Outbox остаётся тем же.

#### Полный путь Query

Чтение:

```text
GET /orders/{id}
        │
        ▼
Presentation
        │
        ▼
GetOrderQuery
        │
        ▼
GetOrderHandler
        │
        ▼
OrderQueryRepository
        │
        ▼
SQL JOIN / aggregation
        │
        ▼
OrderDetailsDTO
        │
        ▼
HTTP response
```

Обратите внимание:

```text
Order Aggregate
```

здесь вообще может не участвовать.

Это нормально.

#### Command и Query repository нельзя смешивать концептуально

Write Repository:

```python
# Контракт записи отвечает за загрузку и сохранение агрегатов.
OrderRepositoryProtocol
```

работает с:

```python
# Агрегат хранит состояние и защищает бизнес-инварианты при изменениях.
Order
```

Query Repository:

```python
# Контракт чтения возвращает проекции под задачи потребителя.
OrderQueryRepositoryProtocol
```

работает с:

```python
# Детали, строки списка и страницы представляют разные результаты чтения.
OrderDetailsDTO
OrderListItemDTO
Page[OrderListItemDTO]
```

Это два разных назначения.

Не делать универсальный repository вида:

```python
# Антипример: один универсальный репозиторий смешивает запись, чтение и аналитику.
OrderRepository:
    get()
    save()
    list()
    search()
    statistics()
    dashboard()
    report()
```

Вместо этого:

```text
OrderRepository
    → Aggregate persistence

OrderQueryRepository
    → Read models

OrderStatisticsQueryRepository
    → Analytics, если понадобится
```

#### Эталонная архитектура Orders

Финально модуль должен восприниматься следующим образом:

```text
                        ORDERS
                           │
             ┌─────────────┴─────────────┐
             │                           │
         WRITE SIDE                  READ SIDE
             │                           │
             ▼                           ▼
        Application                  Application
         Commands                      Queries
             │                           │
             ▼                           ▼
      Domain Aggregate            Query Repository
             │                           │
       Order Repository                  ▼
             │                      optimized SQL
             ▼                           │
       Infrastructure                    ▼
        persistence                    DTO
             │                           │
             └───────────┬───────────────┘
                         ▼
                     PostgreSQL
```

Write path защищает бизнес-инварианты.

Read path оптимизирован под получение данных.

Их не нужно искусственно заставлять использовать одинаковую модель.

### Межмодульное взаимодействие

Например:

```text
Orders
Inventory
Payments
Customers
```

Orders не должен импортировать internal Entity другого bounded context.

Плохо:

```python
# Антипример: импорт внутреннего агрегата склада нарушает границу бизнес-модулей.
from modules.inventory.domain.stock.aggregate import Stock
```

Предпочтительно:

```python
# Порт изолирует Orders от внутренней реализации складского модуля.
InventoryGatewayProtocol
```

или application contract:

```python
# Контракт передаёт только согласованные данные о доступности товаров.
InventoryAvailability
```

или событие:

```text
OrderConfirmed
        ↓
Inventory Reservation Handler
```

Bounded Context должен сохранять автономность.

### Правила разработки

#### Где находится бизнес-логика

При принятии решения агент должен использовать следующий приоритет.

Если правило относится к состоянию одного Aggregate:

```python
# Поведение, изменяющее один агрегат, размещается в его доменных методах.
order.confirm()
order.cancel()
order.add_item()
```

оно принадлежит Aggregate.

Если правило относится к нескольким Domain Objects и является чистым бизнес-правилом:

```python
# Чистые правила для нескольких доменных объектов размещаются в сервисе или политике.
OrderPricingService
OrderEligibilityPolicy
```

оно принадлежит Domain Service / Policy.

Если задача состоит в координации:

```text
загрузить order
запросить inventory
вызвать domain
сохранить order
записать интеграционное сообщение в Outbox
при необходимости явно управлять commit через порт UoW
```

это Application Service / Handler.

Если задача:

```text
SQL
HTTP
Kafka
Redis
filesystem
external API
```

это Infrastructure.

#### Что агенту запрещено делать

1. Не импортировать SQLAlchemy в Domain или Application, включая контракты UoW.

2. Не отдавать ORM models из Repository наружу.

3. Не реализовывать business rules внутри Repository.

4. Не реализовывать business rules в HTTP controller.

5. Не изменять поля Aggregate напрямую из Application.

6. Не делать `commit()` внутри Repository.

7. Не делать `rollback()` внутри Repository.

8. Не использовать Query DTO как Domain Entity.

9. Не создавать Repository для каждой таблицы автоматически.

10. Не делать Repository для Entity, lifecycle которой принадлежит Aggregate Root.

11. Не превращать каждый helper в Domain Service.

12. Не делать Domain Service для orchestration инфраструктуры.

13. Не восстанавливать Aggregate Root для обычного списка/таблицы, если достаточно Query Repository.

14. Не передавать `AsyncSession` в Domain, Use Case или Application Service;
    не объявлять `session` или session factory в Application-контракте UoW.

15. Не использовать infrastructure exceptions как часть публичного Domain API.

16. Не создавать generic CRUD repository как основную абстракцию DDD.

17. Не создавать слой abstraction только ради abstraction.

18. Не открывать UoW повторно внутри Use Case, если он уже открыт внешней сборкой.
    Не передавать UoW в Use Case без необходимости явно управлять commit/rollback.

19. Не подключать репозитории одного атомарного процесса к разным сессиям UoW.

20. Не записывать сообщения Outbox после commit изменения агрегата или
    в независимой транзакции. Доставка сообщений выполняется после commit.

21. Не использовать `__post_init__` вне Value Objects. В Aggregate Root проверки
    создания и восстановления выполняются явными фабриками, изменения состояния —
    публичными domain-методами.

#### Именование

Использовать явные названия.

Domain:

```text
Order
OrderItem
OrderIdVO
OrderStatus
OrderPricingService
OrderRepositoryProtocol
OrderConfirmed
OrderNotFoundError
```

Application:

```text
CreateOrderCommand
CreateOrderHandler
GetOrderQuery
GetOrderHandler
OrderDetailsDTO
OrderQueryRepositoryProtocol
PaymentGatewayProtocol
```

Infrastructure:

```text
OrderModel
OrderItemModel
OrderMapper
OrderQueryMapper
SqlAlchemyOrderRepository
SqlAlchemyOrderQueryRepository
StripePaymentGateway
```

Presentation:

```text
CreateContactRequest
CreateContactResponse
GetContactResponse
ListContactItemResponse
PutContactRequest
PutContactResponse
PatchContactRequest
PatchContactResponse
router в presentation/contact/router.py
```

Из названия класса должно быть понятно, какую архитектурную роль и какой HTTP
сценарий он обслуживает. Совпадающие поля не требуют общего response-класса
для разных методов.

##### DTO naming

Не использовать один универсальный:

```python
# Антипример: универсальный DTO скрывает назначение данных и потребителя.
OrderDTO
```

для всего приложения.

Предпочитать use-case-specific DTO:

```python
# Каждый DTO именуется по конкретному сценарию или форме чтения.
OrderDetailsDTO
OrderListItemDTO
CreateOrderResultDTO
OrderSummaryDTO
OrderStatisticsDTO
```

Read model создаётся под потребность consumer.

##### Mapper naming

Для восстановления Domain:

```python
# Восстановление доменного агрегата обозначается явно.
OrderMapper.to_domain()
```

Для записи:

```python
# Для записи mapper подготавливает значения, но сам не выполняет SQL.
OrderMapper.to_insert_values()
OrderMapper.to_update_values()
```

Для Query projections:

```python
# Mapper чтения создаёт детали, строку списка или другую проекцию.
OrderQueryMapper.to_details()
OrderQueryMapper.to_list_item()
OrderQueryMapper.to_projection()
```

Не называть Query projection:

```python
# Антипример: имя восстановления Domain не подходит для создания Query DTO.
to_domain()
```

#### Общий принцип написания кода

Предпочитать:

```text
explicit > magic
composition > inheritance
business language > technical CRUD language
specific contracts > generic repositories
immutable Value Objects > primitive obsession
use-case DTO > universal DTO
domain behavior > anemic entities
```

Код должен показывать бизнес-намерение.

Плохо:

```python
# Антипример: техническое обновление поля скрывает бизнес-намерение подтверждения.
order.update(
    status="confirmed"
)
```

Хорошо:

```python
# Название доменного метода явно выражает бизнес-намерение.
order.confirm()
```

Плохо:

```python
# Антипример: обновление отдельного поля в Repository обходит поведение агрегата.
repository.update_field(
    "status",
    "confirmed",
)
```

Хорошо:

```python
# Сначала агрегат проверяет правила, затем Repository сохраняет его состояние без commit.
order.confirm()

await repository.save(
    tenant_id,
    order,
)
```

#### Алгоритм агента при реализации новой функции

Перед написанием кода агент должен определить:

```text
Use Case
   │
   ├── изменяет состояние?
   │       │
   │       ├── YES
   │       │    ↓
   │       │ Aggregate / Domain
   │       │ Command Handler
   │       │ Domain Repository
   │       │ UoW во внешней сборке Depends
   │       │ Outbox в общей транзакции, если нужны сообщения
   │       │ UoW port в Use Case только для явного commit/rollback
   │       │
   │       └── NO
   │            ↓
   │         Query
   │         Query Repository
   │         Projection DTO
   │
   ├── есть чистое бизнес-правило
   │   между несколькими domain objects?
   │       ↓
   │   Domain Service / Policy
   │
   ├── есть external dependency?
   │       ↓
   │   Application Port
   │       ↓
   │   Infrastructure Adapter
   │
   └── есть transport?
           ↓
       Presentation Adapter
```

Перед созданием нового класса агент должен уметь ответить:

```text
К какому слою он принадлежит?
Почему?
Какой слой имеет право его импортировать?
Является ли это business logic,
orchestration,
persistence или presentation?
```

Если ответа нет — архитектура класса, вероятно, выбрана неправильно.

### Стандарты и примеры логирования

Логи описывают выполнение сценариев и технические сбои. Они не заменяют Domain
Events, Outbox, метрики или отдельный аудит бизнес-действий.

#### Ответственность слоёв

| Слой | Что логировать |
| --- | --- |
| Domain | Ничего: Aggregate, Entity, Value Object, Domain Service и Policy не используют logger. Они возвращают результат, создают события или выбрасывают доменные ошибки. |
| Application | Значимые этапы сценария без SQL, HTTP payload и деталей конкретного провайдера. Завершение handler ещё не означает commit внешнего UoW. |
| Infrastructure | Диагностику адаптеров, длительность внешних операций и технические события хранения и доставки. |
| Presentation | Итог запроса, безопасный контекст корреляции и преобразование ошибки в транспортный ответ. |
| Bootstrap / Worker | Запуск, остановку, итог обработки задания, повторные попытки и окончательные сбои. |

Логирование не меняет направление зависимостей. Для новых примеров используется
стандартный `logging`: `logging.getLogger(__name__)` создаётся на уровне модуля.
Application не импортирует инфраструктурный адаптер логирования. Настройка
уровней, handlers, formatter и фильтров выполняется один раз в bootstrap.
Не вызывать `basicConfig()` внутри handler, repository или при импорте модуля.

#### Уровни и события

| Уровень | Назначение | Пример события |
| --- | --- | --- |
| `DEBUG` | Подробности диагностики, отключённые в обычном production-режиме. | `orders.confirm.started` |
| `INFO` | Значимый успешный результат или ожидаемый бизнес-отказ. | `orders.confirm.committed`, `orders.confirm.rejected` |
| `WARNING` | Временный сбой, деградация или запланированная повторная попытка. | `outbox.publish.retry_scheduled` |
| `ERROR` | Операция завершилась технической ошибкой или исчерпала попытки. | `orders.confirm.failed`, `outbox.publish.exhausted` |
| `CRITICAL` | Процесс не может продолжать работу, например из-за сбоя обязательной инициализации. | `worker.startup.failed` |

Ожидаемая ошибка валидации или бизнес-правила не является `ERROR` автоматически.
Не логировать каждый пустой poll worker на `INFO`: использовать `DEBUG`,
периодический агрегированный итог или метрику. Успешные массовые операции также
агрегировать, если запись на каждый элемент создаёт лишний шум.

Имя `event` стабильно и имеет вид `<module>.<operation>.<outcome>`.
Динамические значения передаются отдельными полями, а не включаются в имя события.
Сообщение коротко описывает факт; docstring и пояснения в примерах пишутся по-русски.

#### Формат и контекст

В production использовать структурированный JSON, одна запись на строку.
Для локальной разработки допустим читаемый текст с теми же полями контекста.
Formatter добавляет `timestamp` в UTC, `level`, `logger`, `message`, имя сервиса
и окружение. Вызов logger передаёт `event` и только относящиеся к операции поля:

| Поле | Смысл |
| --- | --- |
| `request_id` | Идентификатор запроса, проверенный или сгенерированный на входе. |
| `trace_id`, `correlation_id` | Связь операций и сообщений, если поддерживается tracing или корреляция. |
| `tenant_id`, `order_id` | Внутренние идентификаторы контекста и объекта операции. |
| `message_id`, `job_id` | Идентификатор сообщения или фонового задания. |
| `duration_ms` | Длительность этапа, измеренная монотонными часами. |
| `attempt`, `max_attempts`, `retry_in_seconds` | Номер попытки, лимит и задержка повторения. |
| `error_type`, `reason_code` | Тип исключения и стабильный безопасный код причины. |

UUID и Value Objects явно преобразуются в примитивные значения. Отсутствующие
поля опускаются. Произвольные DTO, ORM models, Command и Request целиком в лог
не передаются. Не использовать ключи `message`, `name`, `levelname` и другие
зарезервированные атрибуты `LogRecord` внутри `extra`.

`extra` добавляет поля в `LogRecord`, но само по себе не включает JSON-вывод:
bootstrap должен подключить formatter, который сериализует разрешённые поля.
Request/trace context передаётся явно или через `contextvars` с обязательным
сбросом в `finally`; mutable global context недопустим из-за смешивания запросов.
Корреляция фонового сообщения переносится через его envelope, а не через живой
объект HTTP Request или request-scoped session.

#### Ошибки, транзакции и безопасные данные

Одно исключение со stack trace записывается один раз на выбранной границе
обработки: HTTP middleware, worker либо внешняя обёртка сценария. Промежуточные
слои передают его выше или преобразуют с сохранением причины через `raise ...
from exc`. Не вызывать `logger.exception()` в каждом слое для одной ошибки.
Если граница уже записала сбой и пробросила исключение дальше, внешний обработчик
только преобразует его в ответ или результат задания, без повторного stack trace.

`logger.exception()` использовать внутри `except` для неожиданного сбоя.
Ожидаемый отказ логировать без stack trace. Отмену async-задачи не подавлять
и не записывать как обычную ошибку обработки.

Событие `*.committed` записывается только после успешного commit. В стандартном
сценарии из раздела [Unit of Work](#unit-of-work) это точка после выхода из внешнего `async with UnitOfWork(...)`.
Успех `repository.save()` или возврат handler не доказывают сохранение данных.
Запись сообщения в Outbox также не означает его доставку: publisher фиксирует
результат доставки отдельно, после подтверждения брокером. Повторные доставки
сохраняют исходный `message_id`, а номер попытки меняется.

Не писать пароли, токены, cookies, заголовки авторизации, OTP, платёжные реквизиты,
персональные данные и полные тела запросов, ответов или сообщений. Использовать
разрешённые внутренние ID и коды причин; внешние строки ограничивать по длине
и очищать от управляющих символов. Текст исключения и stack trace также могут
содержать секреты: перед выводом применять централизованную очистку, не включать
дампы локальных переменных и SQL-параметров. Доступ и срок хранения логов
настраиваются централизованно.

Для подстановки значений в текст использовать ленивое форматирование
`logger.info("Order %s committed", order_id)`, а не f-строки. При структурированном
выводе предпочитать постоянное сообщение с полями в `extra`.

#### Пример: итог команды после завершения UoW

Псевдокод внешней сборки для CLI или worker. Он использует те же порты и handler,
что и в разделе [Command Handler](#command-handler); здесь находится граница записи итогового события. В HTTP-сценарии
аналогичный лог должен учитывать завершение Depends/UoW, а не только возврат
контроллера. Импорты проектных типов опущены. Предполагается настроенный formatter
с очисткой чувствительных данных и отсутствие дублирующего логирования ошибки
в UoW, репозиториях и вызывающем коде.

```python
import logging
from time import perf_counter


logger = logging.getLogger(__name__)


async def run_confirm_order(
    command: ConfirmOrderCommand,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    request_id: str,
) -> None:
    """Собирает сценарий и логирует его итог с учётом результата commit.

    Заказ и Outbox используют общую транзакцию. Бизнес-отказ отличается
    от технического сбоя; исключения передаются вызывающему коду.
    """
    # session_factory заранее привязана к соединению нужного tenant.
    started_at = perf_counter()
    context = {
        "request_id": request_id,
        "tenant_id": str(command.tenant_id.uuid),
        "order_id": str(command.order_id.uuid),
    }

    try:
        async with UnitOfWork(session_factory) as uow:
            handler = ConfirmOrderHandler(
                repository=SqlAlchemyOrderRepository(uow.session),
                outbox=SqlAlchemyOutboxRepository(uow.session),
            )
            await handler.execute(command)
            # Выход из контекста выполняет commit; до него успех не логируется.
    except OrderError as exc:
        logger.info(
            "Order confirmation rejected",
            extra={
                **context,
                "event": "orders.confirm.rejected",
                "error_type": type(exc).__name__,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise
    except Exception as exc:
        # Эта граница единственная записывает stack trace данного сбоя.
        logger.exception(
            "Order confirmation failed",
            extra={
                **context,
                "event": "orders.confirm.failed",
                "error_type": type(exc).__name__,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise

    logger.info(
        "Order confirmation committed",
        extra={
            **context,
            "event": "orders.confirm.committed",
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
```

Пример записи, сформированной production formatter:

```json
{
  "timestamp": "2026-09-28T10:15:30.125Z",
  "level": "INFO",
  "logger": "orders.bootstrap",
  "service": "orders-worker",
  "environment": "production",
  "message": "Order confirmation committed",
  "event": "orders.confirm.committed",
  "request_id": "req-example-01",
  "tenant_id": "ea57f057-75b2-458e-808f-1b15cfdc915d",
  "order_id": "5d223a55-ffae-4c0b-b7c9-fb378ab856b3",
  "duration_ms": 18.42
}
```

JSON показан с отступами для чтения; в потоке логов это одна строка.

#### Пример: повторная доставка Outbox

Этот фрагмент выполняется в publisher после успешного планирования очередной
попытки существующим механизмом retry. Сам лог не планирует повтор и не меняет
состояние Outbox. В примере текущая попытка завершилась временным сбоем,
а её номер ещё меньше `max_attempts`.

```python
# Пишем безопасные метаданные повторения без payload и текста ответа брокера.
logger.warning(
    "Outbox publication retry scheduled",
    extra={
        "event": "outbox.publish.retry_scheduled",
        "message_id": str(message_id),
        "correlation_id": correlation_id,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "retry_in_seconds": retry_in_seconds,
        "reason_code": "broker_unavailable",
    },
)
```

При исчерпании попыток worker записывает `outbox.publish.exhausted` на `ERROR`
вместо `retry_scheduled`. После подтверждения доставки используется отдельное
событие `outbox.publish.delivered`; его нельзя писать сразу после записи в Outbox.

### Главное архитектурное правило

При написании любого кода агент должен исходить не из структуры таблиц, а из бизнес-модели.

Не:

```text
Есть таблица orders
→ создаём OrderRepository CRUD
→ создаём OrderService CRUD
→ создаём OrderController CRUD
```

А:

```text
Есть бизнес Aggregate Order

Он имеет:
create
add_item
remove_item
confirm
cancel

Есть use cases:
CreateOrder
AddOrderItem
ConfirmOrder
CancelOrder

Есть read cases:
GetOrderDetails
ListOrders
SearchOrders

После этого проектируются:
repositories
queries
persistence models
API
```

База данных является способом сохранения модели, а не источником архитектуры приложения.

## Фронтенд

Раздел будет дополнен.
