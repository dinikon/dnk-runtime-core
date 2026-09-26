# Архитектурные правила проекта

Проект строится по принципам **Domain-Driven Design + Clean Architecture**.

Основная единица организации кода — **бизнес-модуль / bounded context**.

Например:

```text
src/modules/
├── orders/
├── catalog/
├── customers/
├── payments/
└── contact_points/
```

Каждый модуль делится на четыре слоя:

```text
module/
├── domain/
├── application/
├── infrastructure/
└── presentation/
```

Важно: Aggregate Root существует только в `domain`.

Не создавать отдельные версии Aggregate Root в `application`, `infrastructure` или `presentation`.

Остальные слои работают с Aggregate Root через публичные domain-контракты.

---

# 1. Направление зависимостей

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

---

# 2. Структура модуля

Пример полного модуля `Orders`:

```text
src/modules/orders/
│
├── domain/
│   ├── order/
│   │   ├── aggregate.py
│   │   ├── entity/
│   │   │   └── order_item.py
│   │   ├── value_object/
│   │   │   ├── identifier.py
│   │   │   ├── status.py
│   │   │   ├── number.py
│   │   │   └── quantity.py
│   │   ├── event/
│   │   │   ├── order_created.py
│   │   │   └── order_confirmed.py
│   │   ├── error.py
│   │   └── repository.py
│   │
│   ├── service/
│   │   ├── pricing_service.py
│   │   └── order_policy.py
│   │
│   └── shared/
│
├── application/
│   ├── command/
│   │   ├── create_order/
│   │   │   ├── command.py
│   │   │   ├── handler.py
│   │   │   └── dto.py
│   │   │
│   │   ├── add_order_item/
│   │   │   ├── command.py
│   │   │   └── handler.py
│   │   │
│   │   └── confirm_order/
│   │       ├── command.py
│   │       └── handler.py
│   │
│   ├── query/
│   │   ├── get_order/
│   │   │   ├── query.py
│   │   │   ├── handler.py
│   │   │   └── dto.py
│   │   │
│   │   └── list_orders/
│   │       ├── query.py
│   │       ├── handler.py
│   │       └── dto.py
│   │
│   ├── service/
│   │   └── order_application_service.py
│   │
│   ├── port/
│   │   ├── query_repository.py
│   │   ├── payment_gateway.py
│   │   └── inventory_gateway.py
│   │
│   └── unit_of_work.py
│
├── infrastructure/
│   ├── persistence/
│   │   ├── models.py
│   │   ├── mappers.py
│   │   ├── repository.py
│   │   ├── query_repository.py
│   │   └── migrations/
│   │
│   ├── payment/
│   │   └── stripe_gateway.py
│   │
│   └── inventory/
│       └── inventory_gateway.py
│
└── presentation/
    ├── http/
    │   ├── router.py
    │   ├── request.py
    │   └── response.py
    │
    └── consumer/
        └── events.py
```

Не обязательно создавать все каталоги заранее.

Создавать только те элементы, которые реально необходимы модулю.

---

# 3. Domain layer

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

---

# 4. Aggregate Root

Для `Orders` Aggregate Root — `Order`.

```python
@dataclass(slots=True)
class Order:
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
        self._ensure_editable()

        ...

    def confirm(self) -> None:
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
        return sum(
            item.total
            for item in self.items
        )

    def pull_events(
        self,
    ) -> tuple[DomainEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def _ensure_editable(self) -> None:
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
order.status = OrderStatus.CONFIRMED
```

из Application Service.

Правильно:

```python
order.confirm()
```

---

# 5. Entity внутри Aggregate

Например `OrderItem`.

```python
@dataclass(slots=True)
class OrderItem:
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
        return cls(
            id=OrderItemIdVO.generate(),
            product_id=product_id,
            quantity=quantity,
            unit_price=price,
        )

    @property
    def total(self) -> MoneyVO:
        return self.unit_price * self.quantity.value

    def increase(
        self,
        quantity: QuantityVO,
    ) -> None:
        self.quantity = self.quantity + quantity
```

`OrderItem` не имеет собственного Repository, если его lifecycle полностью принадлежит `Order`.

Нельзя загружать:

```python
OrderItemRepository.get(item_id)
```

если `OrderItem` является внутренней entity агрегата.

Он загружается через:

```python
OrderRepository.get(order_id)
```

---

# 6. Value Objects

Value Object должен описывать значение, а не строку/число технически.

Например:

```python
@dataclass(
    frozen=True,
    slots=True,
)
class QuantityVO:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidQuantityError()

    def __add__(
        self,
        other: "QuantityVO",
    ) -> "QuantityVO":
        return QuantityVO(
            self.value + other.value
        )
```

Другой пример:

```python
class OrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
```

Value Objects желательно делать immutable.

---

# 7. Domain Errors

Ошибки бизнес-правил принадлежат Domain.

```python
class OrderError(DomainError):
    pass


class OrderNotFoundError(OrderError):
    pass


class EmptyOrderCannotBeConfirmedError(OrderError):
    pass


class OrderCannotBeModifiedError(OrderError):
    pass
```

Не использовать:

```python
HTTPException
IntegrityError
ValueError
```

как публичные бизнес-ошибки domain layer.

---

# 8. Domain Events

Domain Event описывает факт, который уже произошёл.

```python
@dataclass(
    frozen=True,
    slots=True,
)
class OrderConfirmed(DomainEvent):
    order_id: OrderIdVO
```

Aggregate создаёт событие:

```python
def confirm(self) -> None:
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

---

# 9. Domain Repository

Domain Repository работает с Aggregate Root.

Контракт расположен в `domain`.

```python
class OrderRepositoryProtocol(Protocol):

    async def get(
        self,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:
        ...

    async def add(
        self,
        tenant_id: EntityIdVO,
        order: Order,
    ) -> None:
        ...

    async def save(
        self,
        tenant_id: EntityIdVO,
        order: Order,
    ) -> None:
        ...
```

Repository возвращает:

```python
Order
```

а не:

```python
OrderModel
Row
dict
OrderDTO
```

Domain Repository предназначен для изменения бизнес-состояния.

---

# 10. Domain Service

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

    def calculate(
        self,
        *,
        items: tuple[OrderItem, ...],
        discount: DiscountVO | None,
    ) -> MoneyVO:
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

    def ensure_can_confirm(
        self,
        order: Order,
        customer: CustomerSnapshot,
    ) -> None:
        if customer.is_blocked:
            raise CustomerCannotPlaceOrderError()

        if order.calculate_total().is_zero:
            raise ZeroTotalOrderError()
```

---

# 11. Application layer

Application отвечает за use cases.

Он:

```text
принимает Command/Query;
загружает Aggregate;
вызывает domain methods;
координирует repositories;
координирует external ports;
управляет transaction boundary через UoW;
возвращает DTO/result.
```

Application не должен содержать бизнес-инварианты.

Плохо:

```python
if order.status == "draft" and len(order.items) > 0:
    order.status = "confirmed"
```

Правильно:

```python
order.confirm()
```

---

# 12. Command

Command описывает намерение изменить систему.

```python
@dataclass(
    frozen=True,
    slots=True,
)
class ConfirmOrderCommand:
    tenant_id: EntityIdVO
    order_id: OrderIdVO
    actor_id: EntityIdVO
```

Command не содержит SQLAlchemy model или HTTP Request.

---

# 13. Command Handler

```python
class ConfirmOrderHandler:

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        repository: OrderRepositoryProtocol,
        payment_gateway: PaymentGatewayProtocol,
    ) -> None:
        self._uow = uow
        self._repository = repository
        self._payment_gateway = payment_gateway

    async def execute(
        self,
        command: ConfirmOrderCommand,
    ) -> None:

        async with self._uow:

            order = await self._repository.get(
                tenant_id=command.tenant_id,
                order_id=command.order_id,
            )

            order.confirm()

            await self._repository.save(
                tenant_id=command.tenant_id,
                order=order,
            )

            await self._uow.commit()
```

Handler отвечает за сценарий:

```text
load
↓
invoke domain
↓
persist
↓
commit
```

Но не реализует правило `можно ли подтвердить заказ`.

---

# 14. Application Service

Application Service используется, когда use case сложнее простого handler.

Например:

```python
class OrderApplicationService:

    def __init__(
        self,
        *,
        order_repository: OrderRepositoryProtocol,
        inventory: InventoryGatewayProtocol,
        payment: PaymentGatewayProtocol,
    ) -> None:
        self._orders = order_repository
        self._inventory = inventory
        self._payment = payment

    async def confirm(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:

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

---

# 15. Query side

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

---

# 16. Query DTO

```python
@dataclass(
    frozen=True,
    slots=True,
)
class OrderListItemDTO:
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

---

# 17. Query Repository Protocol

Query Repository следует располагать в Application layer.

Например:

```text
application/
└── port/
    └── query_repository.py
```

```python
class OrderQueryRepositoryProtocol(
    Protocol
):

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> OrderDetailsDTO | None:
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        filters: OrderListFilters,
        pagination: Pagination,
    ) -> Page[OrderListItemDTO]:
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

---

# 18. Query Repository implementation

Infrastructure может выполнять оптимизированный SQL напрямую.

```python
class SqlAlchemyOrderQueryRepository:

    def __init__(
        self,
        session: AsyncSession,
        naming: TenantSchemaNaming,
    ) -> None:
        self._session = session
        self._naming = naming

    async def get_details(
        self,
        *,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> OrderDetailsDTO | None:

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
            .execution_options(
                **tenant_execution_options(
                    self._naming,
                    tenant_id,
                )
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

---

# 19. Query Mapper

```python
class OrderQueryMapper:

    @staticmethod
    def to_details(
        row: Mapping[str, Any],
    ) -> OrderDetailsDTO:

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
to_projection()
to_details()
to_list_item()
```

Не называть:

```python
to_domain()
```

если Domain Entity фактически не создаётся.

---

# 20. Query Handler

```python
@dataclass(
    frozen=True,
    slots=True,
)
class GetOrderQuery:
    tenant_id: EntityIdVO
    order_id: OrderIdVO
```

Handler:

```python
class GetOrderHandler:

    def __init__(
        self,
        repository: OrderQueryRepositoryProtocol,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        query: GetOrderQuery,
    ) -> OrderDetailsDTO:

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

---

# 21. Infrastructure persistence model

SQLAlchemy Model — это persistence representation, а не Domain Entity.

```python
class OrderModel(
    AudienceMixin,
    TenantBase,
):
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
OrderModel
```

в Application или Domain.

---

# 22. Persistence Mapper

Mapper является единственной точкой преобразования persistence representation → Domain.

```python
class OrderMapper:

    @staticmethod
    def to_domain(
        order_row: Mapping[str, Any],
        item_rows: Sequence[
            Mapping[str, Any]
        ],
    ) -> Order:

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

---

# 23. Domain Repository implementation

```python
class SqlAlchemyOrderRepository:

    def __init__(
        self,
        session: AsyncSession,
        naming: TenantSchemaNaming,
    ) -> None:
        self._session = session
        self._naming = naming

    async def get(
        self,
        tenant_id: EntityIdVO,
        order_id: OrderIdVO,
    ) -> Order:

        orders = OrderModel.__table__
        items = OrderItemModel.__table__

        order_result = (
            await self._session.execute(
                select(orders)
                .where(
                    orders.c.id
                    == order_id.uuid
                )
                .execution_options(
                    **tenant_execution_options(
                        self._naming,
                        tenant_id,
                    )
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
                .execution_options(
                    **tenant_execution_options(
                        self._naming,
                        tenant_id,
                    )
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

---

# 24. Сохранение Aggregate

При сохранении repository сам разбирает Aggregate на persistence representation.

```python
async def save(
    self,
    tenant_id: EntityIdVO,
    order: Order,
) -> None:

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
        .execution_options(
            **tenant_execution_options(
                self._naming,
                tenant_id,
            )
        )
    )

    await self._session.execute(
        delete(items)
        .where(
            items.c.order_id
            == order.id.uuid
        )
        .execution_options(...)
    )

    await self._session.execute(
        insert(items)
        .execution_options(...),
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

---

# 25. Unit of Work

Repository не делает:

```python
commit()
rollback()
```

Transaction boundary принадлежит Application/UoW.

```python
class UnitOfWork:

    async def __aenter__(self):
        self.session = (
            self._session_factory()
        )
        return self

    async def __aexit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        try:
            if (
                self.session
                and self.session.in_transaction()
            ):
                await self.session.rollback()
        finally:
            if self.session:
                await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
```

Использование:

```python
async with uow:

    order = await repository.get(
        tenant_id,
        order_id,
    )

    order.confirm()

    await repository.save(
        tenant_id,
        order,
    )

    await uow.commit()
```

Commit должен быть явным.

---

# 26. External Ports

Application не должен импортировать конкретные Stripe, Nova Poshta, Prom, Redis и т.п.

Контракт:

```python
class PaymentGatewayProtocol(
    Protocol
):

    async def authorize(
        self,
        payment: PaymentRequest,
    ) -> PaymentAuthorization:
        ...
```

Infrastructure:

```python
class StripePaymentGateway(
    PaymentGatewayProtocol
):

    async def authorize(
        self,
        payment: PaymentRequest,
    ) -> PaymentAuthorization:

        response = await self._client...
        ...
```

Application зависит от:

```python
PaymentGatewayProtocol
```

а не от:

```python
StripePaymentGateway
```

---

# 27. Presentation layer

HTTP слой должен быть максимально тонким.

```python
@router.post(
    "/orders/{order_id}/confirm"
)
async def confirm_order(
    order_id: UUID,
    request: Request,
    handler: ConfirmOrderHandler,
) -> OrderResponse:

    command = ConfirmOrderCommand(
        tenant_id=request.tenant_id,
        order_id=OrderIdVO(
            order_id
        ),
        actor_id=request.actor_id,
    )

    await handler.execute(command)

    return OrderResponse(
        id=order_id,
        status="confirmed",
    )
```

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

---

# 28. Полный путь Command

Для изменения заказа поток должен выглядеть так:

```text
POST /orders/{id}/confirm
        │
        ▼
Presentation
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
UnitOfWork.commit()
        │
        ▼
Domain Events / Outbox
```

---

# 29. Полный путь Query

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

---

# 30. Command и Query repository нельзя смешивать концептуально

Write Repository:

```python
OrderRepositoryProtocol
```

работает с:

```python
Order
```

Query Repository:

```python
OrderQueryRepositoryProtocol
```

работает с:

```python
OrderDetailsDTO
OrderListItemDTO
Page[OrderListItemDTO]
```

Это два разных назначения.

Не делать универсальный repository вида:

```python
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

---

# 31. Где находится бизнес-логика

При принятии решения агент должен использовать следующий приоритет.

Если правило относится к состоянию одного Aggregate:

```python
order.confirm()
order.cancel()
order.add_item()
```

оно принадлежит Aggregate.

Если правило относится к нескольким Domain Objects и является чистым бизнес-правилом:

```python
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
отправить command
commit
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

---

# 32. Что агенту запрещено делать

1. Не импортировать SQLAlchemy в Domain.

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

14. Не передавать `AsyncSession` в Domain или Application Service.

15. Не использовать infrastructure exceptions как часть публичного Domain API.

16. Не создавать generic CRUD repository как основную абстракцию DDD.

17. Не создавать слой abstraction только ради abstraction.

---

# 33. Именование

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
CreateOrderRequest
OrderResponse
orders_router
```

Из названия класса должно быть понятно, какую архитектурную роль он выполняет.

---

# 34. DTO naming

Не использовать один универсальный:

```python
OrderDTO
```

для всего приложения.

Предпочитать use-case-specific DTO:

```python
OrderDetailsDTO
OrderListItemDTO
CreateOrderResultDTO
OrderSummaryDTO
OrderStatisticsDTO
```

Read model создаётся под потребность consumer.

---

# 35. Mapper naming

Для восстановления Domain:

```python
OrderMapper.to_domain()
```

Для записи:

```python
OrderMapper.to_insert_values()
OrderMapper.to_update_values()
```

Для Query projections:

```python
OrderQueryMapper.to_details()
OrderQueryMapper.to_list_item()
OrderQueryMapper.to_projection()
```

Не называть Query projection:

```python
to_domain()
```

---

# 36. Aggregate boundary

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
order_id: OrderIdVO
```

но не должен содержать прямой Python reference:

```python
payment.order: Order
```

Связи между Aggregate Roots осуществляются через IDs.

---

# 37. Межмодульное взаимодействие

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
from modules.inventory.domain.stock.aggregate import Stock
```

Предпочтительно:

```python
InventoryGatewayProtocol
```

или application contract:

```python
InventoryAvailability
```

или событие:

```text
OrderConfirmed
        ↓
Inventory Reservation Handler
```

Bounded Context должен сохранять автономность.

---

# 38. Domain snapshots

Если Domain Order должен использовать информацию из другого context, но она нужна для принятия domain decision, использовать специализированный immutable snapshot.

Например:

```python
@dataclass(
    frozen=True,
    slots=True,
)
class CustomerOrderSnapshot:
    customer_id: EntityIdVO
    is_blocked: bool
    customer_type: CustomerType
```

А не передавать:

```python
CustomerAggregate
```

из другого bounded context.

---

# 39. Общий принцип написания кода

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
order.update(
    status="confirmed"
)
```

Хорошо:

```python
order.confirm()
```

Плохо:

```python
repository.update_field(
    "status",
    "confirmed",
)
```

Хорошо:

```python
order.confirm()

await repository.save(
    tenant_id,
    order,
)
```

---

# 40. Алгоритм агента при реализации новой функции

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
   │       │ UoW
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

---

# 41. Эталонная архитектура Orders

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

---

# Главное архитектурное правило

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