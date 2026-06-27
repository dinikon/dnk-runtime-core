# Coding Style Manual: DDD + Clean Architecture

## 0. Назначение документа
Этот документ задает строгие правила написания и рефакторинга кода в проекте, построенном по принципам Domain-Driven Design и Clean Architecture.
Цель документа — обеспечить архитектурное качество 10/10:
* бизнес-логика находится в Domain;
* сценарии приложения находятся в Application;
* технические реализации находятся в Infrastructure;
* HTTP/API/CLI/Workers являются внешними адаптерами;
* зависимости всегда направлены внутрь;
* фреймворки не протекают в бизнес-логику;
* код тестируется без реальной инфраструктуры;
* каждый слой имеет четкую ответственность.
Документ обязателен к соблюдению при:
* создании нового модуля;
* добавлении новой бизнес-фичи;
* рефакторинге существующего кода;
* генерации кода через AI;
* code review.

## 1. Главный архитектурный закон

### 1.1. Направление зависимостей
Разрешенное направление зависимостей:

```
Presentation / Worker / CLI
        ↓
Application
        ↓
Domain
```

Infrastructure подключается снаружи через интерфейсы/порты:

```
Application → Port / Protocol ← Infrastructure Adapter
```

Bootstrap / Composition Root собирает зависимости:

```
Bootstrap
    ├── создает infrastructure adapters
    ├── создает use cases
    └── передает use cases во внешние entrypoints
```

### 1.2. Запрещенное направление зависимостей
Запрещено:

```
Domain → Application
Domain → Infrastructure
Domain → Presentation
Application → Infrastructure
Application → Presentation
Infrastructure → Presentation
```

### 1.3. Абсолютное правило
Внутренний слой никогда не должен знать о внешнем слое.
Если Domain или Application импортирует FastAPI, Redis, SQLAlchemy, HTTPX, Pydantic request model, Celery, Kafka, S3, boto3, aiohttp, Starlette, Flask или любой другой внешний инструмент — архитектура нарушена.

## 2. Каноническая структура модуля
Каждый bounded context / модуль должен иметь структуру:

```
src/modules/<module_name>/
├── domain/
│   ├── <aggregate>/
│   │   ├── entity.py
│   │   ├── value_objects.py
│   │   ├── events.py
│   │   ├── errors.py
│   │   ├── policies.py
│   │   └── services.py
│   └── shared/
│
├── application/
│   └── <aggregate>/
│       ├── commands/
│       ├── queries/
│       ├── use_cases/
│       ├── ports/
│       ├── dto/
│       ├── errors.py
│       └── services/
│
├── infrastructure/
│   └── <aggregate>/
│       ├── persistence/
│       ├── queue/
│       ├── http/
│       ├── external/
│       ├── mappers/
│       └── config/
│
├── presentation/
│   ├── http/
│   │   └── <aggregate>/
│   │       ├── controllers/
│   │       ├── requests/
│   │       ├── responses/
│   │       └── routes.py
│   ├── cli/
│   └── workers/
│
└── bootstrap/
    ├── container.py
    ├── settings.py
    └── lifespan.py
```


## 3. Domain Layer

### 3.1. Ответственность Domain
Domain отвечает только за бизнес-модель и бизнес-правила.
Domain содержит:
* Aggregates;
* Entities;
* Value Objects;
* Domain Events;
* Domain Errors;
* Domain Services;
* Policies;
* Specifications;
* бизнес-инварианты;
* правила переходов состояния;
* правила создания и изменения объектов.
Domain не знает:
* где данные хранятся;
* через какой API пришел запрос;
* какой используется фреймворк;
* какая база данных используется;
* как отправляется HTTP callback;
* как работает очередь;
* какой формат JSON у внешнего API.

### 3.2. Что разрешено в Domain
Разрешено:

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Self
from uuid import UUID
```

Разрешены:
* стандартная библиотека Python;
* собственные domain-типы;
* собственные domain-errors;
* собственные domain-events;
* чистые алгоритмы без внешних side effects.

### 3.3. Что запрещено в Domain
Запрещено импортировать:

```
fastapi
pydantic
sqlalchemy
redis
httpx
requests
aiohttp
celery
kombu
boto3
pytest
logging
os
dotenv
```

Запрещено:
* делать SQL-запросы;
* читать env;
* отправлять HTTP;
* публиковать события в брокер;
* сериализовать под конкретный внешний API;
* возвращать HTTP status codes;
* использовать Pydantic request/response models;
* принимать dict вместо Value Object там, где есть бизнес-смысл;
* мутировать entity напрямую снаружи.

## 4. Entity

### 4.1. Назначение Entity
Entity — объект с идентичностью и жизненным циклом.
Entity должна:
* иметь ID;
* защищать свои инварианты;
* изменяться только через методы;
* не позволять внешнему коду ломать состояние;
* генерировать domain events при важных изменениях.

### 4.2. Правила Entity
Entity создается только через factory method:

```python
@dataclass(slots=True)
class MessageEntity:
    id: MessageIdVO
    status: MessageStatusVO
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: MessageIdVO,
        created_at: datetime,
    ) -> "MessageEntity":
        return cls(
            id=id,
            status=MessageStatusVO.accepted(),
            created_at=created_at,
        )
```

Если entity восстанавливается из базы/Redis, должен быть отдельный метод:

```python
@classmethod
def restore(
    cls,
    *,
    id: MessageIdVO,
    status: MessageStatusVO,
    created_at: datetime,
) -> "MessageEntity":
    return cls(
        id=id,
        status=status,
        created_at=created_at,
    )
```

### 4.3. Запрещено
Запрещено:

```python
message.status = "delivered"
message.callback_sent_at = datetime.now()
```

Разрешено:

```python
message.mark_delivered(occurred_at=now)
message.mark_callback_sent(sent_at=now)
```

Внешний код не должен напрямую менять состояние entity.

## 5. Aggregate Root

### 5.1. Назначение Aggregate Root
Aggregate Root — главный объект, через который изменяются связанные сущности.
Все изменения внутри aggregate должны проходить через root.
Пример:

```
MessageAggregate
├── MessageEntity
├── StatusHistoryItem
└── DomainEvents
```

### 5.2. Правила Aggregate
Aggregate Root обязан:
* защищать consistency boundary;
* не отдавать внутренние mutable-коллекции наружу;
* иметь методы бизнес-действий;
* валидировать переходы состояния;
* генерировать domain events.
Пример:

```python
def mark_as_delivered(self, *, occurred_at: datetime) -> None:
    if not self.status.can_transition_to(MessageStatus.DELIVERED):
        raise InvalidMessageStatusTransitionError()

    self.status = MessageStatusVO.delivered()
    self._add_status_history(MessageStatus.DELIVERED, occurred_at)
    self._record_event(MessageDeliveredEvent(message_id=self.id))
```

### 5.3. Запрещено
Запрещено:
* изменять дочерние entity напрямую из Application;
* позволять Infrastructure менять поля aggregate;
* делать aggregate просто анемичной dataclass без поведения;
* размещать use case logic внутри aggregate.

## 6. Value Object

### 6.1. Назначение Value Object
Value Object — неизменяемый объект, который описывает значение и его правила.
Value Object должен быть:
* immutable;
* validated;
* сравнимым по значению;
* без ID;
* без side effects.

### 6.2. Правила Value Object

```python
@dataclass(frozen=True, slots=True)
class EmailVO:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()

        if "@" not in normalized:
            raise InvalidEmailError(value=self.value)

        object.__setattr__(self, "value", normalized)
```

### 6.3. Запрещено
Запрещено:
* хранить сырой str, если значение имеет бизнес-смысл;
* валидировать email/phone/url в controller;
* передавать dict вместо VO;
* делать VO mutable;
* добавлять в VO infrastructure-зависимости.

## 7. Domain Events

### 7.1. Когда нужны события
Domain Event создается, когда в бизнесе произошло значимое событие:
* MessageAccepted;
* MessageDelivered;
* MessageRead;
* CallbackFailed;
* BroadcastStarted;
* FileUploaded;
* TenantBucketCreated.

### 7.2. Правила Domain Event
Domain Event должен быть immutable dataclass:

```python
@dataclass(frozen=True, slots=True)
class MessageDeliveredEvent:
    message_id: MessageIdVO
    occurred_at: datetime
```

Aggregate записывает событие внутрь себя:

```python
def _record_event(self, event: DomainEvent) -> None:
    self._events.append(event)
```

Application забирает события после успешного сохранения aggregate:

```python
events = message.pull_events()
await event_publisher.publish(events)
```

### 7.3. Запрещено
Domain Event не должен:
* отправлять себя в Kafka/RabbitMQ/Redis;
* знать routing key;
* знать HTTP endpoint;
* содержать JSON внешнего API;
* зависеть от инфраструктуры.

## 8. Domain Services и Policies

### 8.1. Когда создавать Domain Service
Domain Service нужен, если бизнес-правило:
* не принадлежит одной entity;
* использует несколько aggregates;
* является чистым бизнес-алгоритмом;
* не требует I/O.
Пример:

```python
class MessageStatusPolicy:
    def next_status_for_channel(
        self,
        *,
        channel: MessageChannelVO,
        current_status: MessageStatusVO,
    ) -> list[MessageStatusVO]:
        ...
```

### 8.2. Когда создавать Policy
Policy нужна для вариативных бизнес-правил:
* какие статусы разрешены для канала;
* сколько callback attempts разрешено;
* можно ли отправлять маркетинговое сообщение;
* можно ли повторить операцию;
* какой лимит применить.

### 8.3. Запрещено
Domain Service / Policy не должны:
* ходить в базу;
* читать Redis;
* отправлять HTTP;
* логировать технические ошибки;
* принимать DTO из API;
* возвращать response model.

## 9. Application Layer

### 9.1. Ответственность Application
Application отвечает за сценарии использования системы.
Application содержит:
* Commands;
* Queries;
* Use Cases;
* Application Services;
* Ports / Protocols;
* DTO / Results;
* Transaction boundaries;
* Authorization checks;
* Idempotency orchestration;
* Domain event publishing orchestration.
Application не содержит технических деталей реализации.

### 9.2. Use Case
Use Case — один бизнес-сценарий.
Примеры:

```
SendMessageUseCase
ProcessDueCallbacksUseCase
CreateBroadcastUseCase
UploadFileUseCase
GetFileDownloadUrlUseCase
```

Use Case должен:
* принимать Command или Query;
* создавать Value Objects;
* загружать aggregates через repository port;
* вызывать методы domain objects;
* сохранять результат через repository port;
* вызывать external ports;
* возвращать Result DTO;
* не знать конкретную инфраструктуру.

### 9.3. Command
Command описывает намерение изменить систему.

```python
@dataclass(frozen=True, slots=True)
class SendMessageCommand:
    channel: str
    recipient: str
    text: str
    callback_url: str
    client_message_id: str | None = None
```

Command:
* immutable;
* не содержит FastAPI/Pydantic;
* не содержит domain entity;
* не содержит Redis/SQLAlchemy models;
* может содержать primitive values;
* преобразуется в VO внутри Use Case.

### 9.4. Query
Query описывает намерение прочитать данные.

```python
@dataclass(frozen=True, slots=True)
class GetMessageQuery:
    message_id: str
```

Query не должен менять состояние.

### 9.5. Result DTO
Use Case возвращает Result DTO:

```python
@dataclass(frozen=True, slots=True)
class SendMessageResult:
    message_id: str
    status: str
```

Result DTO:
* не является domain entity;
* безопасен для presentation;
* не содержит infrastructure models.

### 9.6. Ports / Protocols
Application определяет интерфейсы, которые нужны use cases.

```python
class MessageRepositoryProtocol(Protocol):
    async def save(self, message: MessageEntity) -> None:
        ...

    async def get_by_id(self, message_id: MessageIdVO) -> MessageEntity | None:
        ...
class CallbackSenderProtocol(Protocol):
    async def send(self, callback_url: CallbackUrlVO, payload: CallbackPayloadDTO) -> CallbackSendResult:
        ...
```

Infrastructure реализует эти порты.
Application не импортирует infrastructure-реализации.

### 9.7. Запрещено в Application
Запрещено:

```python
import fastapi
import redis
import sqlalchemy
import httpx
import requests
import boto3
```

Запрещено:
* создавать Redis client;
* открывать SQL connection;
* читать env;
* формировать HTTP response;
* использовать Pydantic request model;
* импортировать FastAPI Depends;
* знать Docker/Kubernetes/ArgoCD;
* сериализовать domain entity в формат базы.

## 10. Infrastructure Layer

### 10.1. Ответственность Infrastructure
Infrastructure отвечает за техническую реализацию портов.
Infrastructure содержит:
* Redis repositories;
* SQL repositories;
* S3 adapters;
* HTTP clients;
* queue adapters;
* message broker producers/consumers;
* ORM models;
* row mappers;
* external API clients;
* serializers для хранения;
* retry transport logic;
* infrastructure config.

### 10.2. Правила Infrastructure
Infrastructure может импортировать:

```
redis
sqlalchemy
httpx
boto3
aio_pika
asyncpg
```

Infrastructure может зависеть от:

```
domain
application ports
```

Infrastructure не должна зависеть от Presentation.

### 10.3. Repository Adapter
Repository adapter должен:
* реализовать application port;
* не содержать бизнес-правила;
* мапить persistence model ↔ domain model;
* не возвращать ORM/Redis dict наружу;
* не принимать FastAPI schemas.
Пример:

```python
class RedisMessageRepository(MessageRepositoryProtocol):
    async def save(self, message: MessageEntity) -> None:
        data = MessageRedisMapper.to_record(message)
        await self._redis.set(message.id.value, json.dumps(data))

    async def get_by_id(self, message_id: MessageIdVO) -> MessageEntity | None:
        raw = await self._redis.get(message_id.value)
        if raw is None:
            return None

        return MessageRedisMapper.to_domain(json.loads(raw))
```

### 10.4. Mapper
Mapper должен быть отдельным классом/модулем.

```python
class MessageRedisMapper:
    @staticmethod
    def to_record(message: MessageEntity) -> dict[str, Any]:
        ...

    @staticmethod
    def to_domain(data: dict[str, Any]) -> MessageEntity:
        return MessageEntity.restore(...)
```

Запрещено:
* размещать mapping logic внутри Use Case;
* размещать mapping logic внутри Entity;
* возвращать dict из repository;
* создавать domain object через обход инвариантов без явного restore().

### 10.5. External API Adapter
HTTP adapter должен:
* реализовать application port;
* скрывать httpx/requests;
* переводить network errors в application-level result/error;
* не бросать наружу сырые HTTPX exceptions;
* не содержать domain business rules.
Пример:

```python
class HttpCallbackSender(CallbackSenderProtocol):
    async def send(self, url: CallbackUrlVO, payload: CallbackPayloadDTO) -> CallbackSendResult:
        try:
            response = await self._client.post(url.value, json=payload.to_dict())
        except httpx.HTTPError as exc:
            return CallbackSendResult.failed(reason=str(exc))

        if response.status_code >= 500:
            return CallbackSendResult.failed(reason="server_error")

        return CallbackSendResult.success()
```


## 11. Presentation Layer

### 11.1. Ответственность Presentation
Presentation отвечает за внешний интерфейс приложения:
* HTTP routes;
* FastAPI controllers;
* request/response schemas;
* CLI commands;
* worker entrypoints;
* webhook entrypoints;
* API error mapping.
Presentation не содержит бизнес-логики.

### 11.2. HTTP Controller
Controller должен:
* принять request;
* провалидировать транспортный формат;
* создать Command/Query;
* вызвать Use Case;
* преобразовать Result в Response;
* обработать application/domain errors через exception mapper.
Пример:

```python
@router.post("/messages/sms")
async def send_sms(
    request: SendSmsRequest,
    use_case: SendMessageUseCase = Depends(get_send_message_use_case),
) -> SendMessageResponse:
    result = await use_case.execute(
        SendMessageCommand(
            channel="sms",
            recipient=request.recipient,
            text=request.text,
            callback_url=str(request.callback_url),
            client_message_id=request.client_message_id,
        )
    )

    return SendMessageResponse(
        message_id=result.message_id,
        status=result.status,
    )
```

### 11.3. Request/Response Schemas
Pydantic models разрешены только в Presentation и Config.

```python
class SendSmsRequest(BaseModel):
    recipient: str
    text: str
    callback_url: AnyUrl
    client_message_id: str | None = None
```

Pydantic schema не должна использоваться в Domain/Application.

### 11.4. Запрещено в Presentation
Запрещено:
* писать бизнес-логику;
* создавать domain entity напрямую;
* работать с Redis/SQLAlchemy/S3;
* отправлять HTTP callback;
* принимать решение о статусах;
* делать retry policy;
* реализовывать idempotency;
* импортировать infrastructure adapters напрямую, кроме DI/bootstrap boundary.

## 12. Worker / Background Jobs

### 12.1. Worker — это Presentation Adapter
Worker является внешним entrypoint, как HTTP controller.
Worker должен:
* получить сигнал выполнения;
* вызвать Use Case;
* не содержать бизнес-логику;
* не работать напрямую с domain без use case;
* получать зависимости из bootstrap/container.
Правильно:

```python
async def run_worker() -> None:
    container = build_container()
    use_case = container.process_due_callbacks_use_case

    while True:
        await use_case.execute(ProcessDueCallbacksCommand(limit=100))
        await asyncio.sleep(1)
```

Неправильно:

```python
async def run_worker() -> None:
    redis = Redis(...)
    messages = await redis.get(...)
    # бизнес-логика прямо в worker
```


## 13. Bootstrap / Composition Root

### 13.1. Ответственность Bootstrap
Bootstrap отвечает за сборку приложения.
Bootstrap содержит:
* settings;
* создание клиентов Redis/DB/HTTP;
* создание repositories;
* создание queues;
* создание use cases;
* wiring для FastAPI;
* lifespan hooks.

### 13.2. Правила Bootstrap
Bootstrap может знать обо всех слоях.
Это единственное место, где допустимо соединять:

```
UseCase + Infrastructure Adapter
```

Пример:

```python
def build_container(settings: Settings) -> Container:
    redis = Redis.from_url(settings.redis_url)
    repository = RedisMessageRepository(redis)
    queue = RedisDelayedCallbackQueue(redis)
    callback_sender = HttpCallbackSender()

    send_message_use_case = SendMessageUseCase(
        repository=repository,
        queue=queue,
        clock=SystemClock(),
        id_generator=UuidMessageIdGenerator(),
    )

    return Container(
        send_message_use_case=send_message_use_case,
    )
```

### 13.3. Запрещено
Запрещено размещать bootstrap в:

```
presentation/depends/wiring.py
```

Лучше:

```
bootstrap/container.py
bootstrap/settings.py
```

Presentation может только получать готовые use cases из container.

## 14. Shared Kernel

### 14.1. Что можно хранить в Shared
Shared Kernel допускается только для действительно общих примитивов:
* EntityIdVO;
* TenantIdVO;
* ClockProtocol;
* IdGeneratorProtocol;
* base domain event;
* base errors;
* pagination DTO;
* transaction protocol.

### 14.2. Что запрещено хранить в Shared
Запрещено превращать shared в мусорный пакет.
Нельзя хранить:
* бизнес-логику конкретного модуля;
* DTO конкретного use case;
* repository конкретного модуля;
* FastAPI dependencies;
* infrastructure adapters;
* SQLAlchemy base конкретной базы;
* глобальные singleton-объекты.

## 15. Ошибки и исключения

### 15.1. Domain Errors
Domain errors описывают нарушение бизнес-правил.

```python
class InvalidMessageStatusTransitionError(DomainError):
    pass
```

Domain error не содержит HTTP status code.

### 15.2. Application Errors
Application errors описывают ошибки сценария:

```python
class MessageNotFoundError(ApplicationError):
    pass
```

Application error не содержит FastAPI response.

### 15.3. Presentation Error Mapper
HTTP status code задается только в Presentation.

```python
@app.exception_handler(MessageNotFoundError)
async def handle_message_not_found(request: Request, exc: MessageNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "message_not_found"},
    )
```

### 15.4. Запрещено
Запрещено:

```python
raise HTTPException(...)
```

в Domain/Application.

## 16. DTO, Schema, Model: строгие различия

### 16.1. Entity
Domain object с бизнес-идентичностью.

```
domain/message/entity.py
```

### 16.2. Value Object
Domain object без identity.

```
domain/message/value_objects.py
```

### 16.3. Command / Query
Application input.

```
application/commands/send_message.py
application/queries/get_message.py
```

### 16.4. Result DTO
Application output.

```
application/dto/message_result.py
```

### 16.5. Request / Response Schema
Presentation model.

```
presentation/http/schemas/send_message.py
```

### 16.6. ORM / Persistence Model
Infrastructure model.

```
infrastructure/persistence/models.py
```

### 16.7. Запрещено смешивать
Запрещено:
* использовать Pydantic request как Command;
* использовать ORM model как Entity;
* возвращать Entity прямо из Controller;
* сохранять Response Schema в базу;
* передавать SQLAlchemy model в Domain.

## 17. Репозитории

### 17.1. Repository Port
Repository port описывает намерение работы с aggregate.

```python
class MessageRepositoryProtocol(Protocol):
    async def save(self, message: MessageEntity) -> None:
        ...

    async def get_by_id(self, message_id: MessageIdVO) -> MessageEntity | None:
        ...
```

### 17.2. Repository Adapter
Repository adapter реализует port.

```python
class PostgresMessageRepository(MessageRepositoryProtocol):
    ...
```

### 17.3. Правила
Repository должен работать с Aggregate Root.
Запрещено:
* делать repository на каждый VO;
* возвращать dict;
* возвращать ORM model;
* принимать Pydantic schema;
* реализовывать бизнес-правила;
* коммитить transaction внутри каждого метода, если используется Unit of Work.

## 18. Unit of Work / Transactions

### 18.1. Когда нужен Unit of Work
Unit of Work обязателен, если use case:
* меняет несколько aggregates;
* пишет в несколько таблиц;
* публикует события после commit;
* требует атомарности;
* использует outbox.

### 18.2. Правило
Use Case управляет transaction boundary через UoW port.

```python
async with self._uow:
    message = await self._uow.messages.get_by_id(command.message_id)
    message.mark_delivered(occurred_at=now)
    await self._uow.messages.save(message)
    await self._uow.commit()
```

Infrastructure реализует UoW.

## 19. Idempotency

### 19.1. Когда обязательна идемпотентность
Idempotency обязательна для:
* отправки сообщений;
* создания файлов;
* запуска рассылки;
* создания платежа;
* callback/webhook обработки;
* повторяемых jobs.

### 19.2. Где реализуется
Application отвечает за orchestration идемпотентности.
Domain может содержать бизнес-правило уникальности, но не должен знать Redis/Postgres lock.
Infrastructure реализует lock/storage.

### 19.3. Правило
Если Command содержит client_message_id или idempotency_key, use case обязан:
1. проверить существующий результат;
2. захватить lock;
3. повторно проверить существующий результат;
4. выполнить операцию;
5. сохранить idempotency record;
6. вернуть стабильный результат.

## 20. Валидация

### 20.1. Уровни валидации
Presentation validation
Проверяет транспортный формат:
* поле есть / нет;
* JSON валиден;
* URL похож на URL;
* тип данных корректен.
Application validation
Проверяет сценарий:
* пользователь имеет доступ;
* объект существует;
* команда применима;
* idempotency соблюдена.
Domain validation
Проверяет бизнес-инварианты:
* статус может перейти в другой статус;
* SMS не может иметь subject;
* Email обязан иметь subject;
* private file нельзя открыть без разрешения;
* marketing communication limit не превышен.

### 20.2. Запрещено
Запрещено держать бизнес-инварианты только в Pydantic schemas.

## 21. Naming Conventions

### 21.1. Domain

```
MessageEntity
MessageIdVO
MessageStatusVO
MessageDeliveredEvent
InvalidMessageStatusTransitionError
MessageStatusPolicy
```

### 21.2. Application

```
SendMessageCommand
SendMessageUseCase
SendMessageResult
MessageRepositoryProtocol
CallbackSenderProtocol
```

### 21.3. Infrastructure

```
RedisMessageRepository
PostgresMessageRepository
HttpCallbackSender
MessageRedisMapper
SqlAlchemyMessageMapper
```

### 21.4. Presentation

```
SendSmsRequest
SendSmsResponse
send_sms_controller
message_router
```

### 21.5. Файлы
Файлы называются snake_case:

```
send_message.py
message_repository.py
message_status_policy.py
redis_message_repository.py
```


## 22. Async rules

### 22.1. Domain
Domain должен быть sync.
Запрещено:

```python
async def mark_delivered(...)
```

Domain не делает I/O, поэтому async там не нужен.

### 22.2. Application
Use Cases могут быть async, если используют async ports.

```python
async def execute(self, command: SendMessageCommand) -> SendMessageResult:
    ...
```

### 22.3. Infrastructure
Infrastructure может быть async.

## 23. Logging

### 23.1. Где можно логировать
Логирование разрешено в:
* Infrastructure;
* Presentation;
* Bootstrap;
* Worker.
Application может логировать только сценарные события, но без технического шума.
Domain не логирует.

### 23.2. Запрещено
Запрещено использовать logger внутри Entity/VO.

## 24. Configuration

### 24.1. Где читать env
Env читается только в:

```
bootstrap/settings.py
infrastructure/config/
```

### 24.2. Запрещено
Запрещено:

```python
os.getenv(...)
```

в Domain/Application/Controller.
Controller должен получать уже собранный use case.

## 25. Тестирование

### 25.1. Domain tests
Domain tests должны:
* тестировать Value Objects;
* тестировать Entity methods;
* тестировать status transitions;
* тестировать policies;
* не использовать Redis/DB/FastAPI.
Пример:

```python
def test_sms_message_cannot_have_subject():
    with pytest.raises(InvalidMessageContentError):
        MessageContentVO.for_channel(
            channel=MessageChannelVO.sms(),
            text="Hello",
            subject="Forbidden",
        )
```

### 25.2. Application tests
Application tests должны использовать fake/in-memory ports.

```python
repository = InMemoryMessageRepository()
queue = InMemoryDelayedCallbackQueue()
clock = FixedClock(...)
```

Запрещено в application tests:
* реальный Redis;
* реальный Postgres;
* реальный HTTP;
* sleep;
* random без фиксации.

### 25.3. Infrastructure tests
Infrastructure tests проверяют реальные adapters.
Можно использовать:
* testcontainers;
* docker compose;
* локальный Redis;
* временную БД.

### 25.4. Presentation tests
Presentation tests проверяют HTTP слой через TestClient/AsyncClient.
Use Cases можно подменять fake-объектами.

## 26. CI Quality Gate
Каждый pull request должен проходить:

```
ruff / lint
black / formatter
mypy / pyright
pytest
coverage
docker build
```

Минимальные требования:
* Domain coverage: 90%+
* Application coverage: 85%+
* Infrastructure coverage: по ключевым adapters
* Presentation coverage: основные endpoints и error mapping

## 27. Code Review Checklist
Перед merge проверить:
Architecture
*  Domain не импортирует Application/Infrastructure/Presentation.
*  Application не импортирует Infrastructure/Presentation.
*  Infrastructure не содержит бизнес-правил.
*  Presentation не содержит бизнес-логики.
*  Bootstrap является единственным местом сборки зависимостей.
Domain
*  Есть Value Objects для значимых значений.
*  Entity создается через create().
*  Persistence восстановление идет через restore().
*  Бизнес-изменения идут через методы entity/aggregate.
*  Нет прямой мутации полей извне.
*  Ошибки являются domain-specific.
*  Domain не знает внешний JSON/API формат.
Application
*  Use Case имеет один понятный сценарий.
*  Use Case принимает Command/Query.
*  Use Case возвращает Result DTO.
*  Все внешние зависимости являются ports/protocols.
*  Idempotency учтена там, где нужна.
*  Transaction boundary определен явно.
Infrastructure
*  Adapter реализует port.
*  Mapping вынесен отдельно.
*  Adapter не возвращает dict/ORM наружу.
*  Infrastructure errors переведены в application-level result/error.
*  Нет бизнес-решений внутри adapter.
Presentation
*  Controller тонкий.
*  Pydantic используется только для request/response.
*  Controller не создает entity напрямую.
*  HTTP errors мапятся через exception handler.
*  Нет except Exception as e: raise e.
Tests
*  Domain tests покрывают бизнес-инварианты.
*  Application tests работают через fake ports.
*  Infrastructure tests проверяют adapters.
*  Presentation tests проверяют endpoints.
*  Нет тестов, завязанных на случайный порядок/random/sleep.

## 28. Запрещенные анти-паттерны

### 28.1. Anemic Domain Model
Плохо:

```python
message.status = "delivered"
repository.save(message)
```

Хорошо:

```python
message.mark_delivered(occurred_at=now)
await repository.save(message)
```

### 28.2. Fat Controller
Плохо:

```python
@router.post("/send")
async def send(request):
    redis = Redis(...)
    message = {...}
    await redis.set(...)
    await httpx.post(...)
```

Хорошо:

```python
@router.post("/send")
async def send(request: SendMessageRequest, use_case: SendMessageUseCase):
    result = await use_case.execute(command)
    return response
```

### 28.3. Infrastructure in Application
Плохо:

```python
class SendMessageUseCase:
    def __init__(self):
        self.redis = Redis(...)
```

Хорошо:

```python
class SendMessageUseCase:
    def __init__(self, repository: MessageRepositoryProtocol):
        self._repository = repository
```

### 28.4. Domain knows external API
Плохо:

```python
class MessageEntity:
    def to_callback_json(self) -> dict:
        return {
            "provider": "mock",
            "external_id": self.id.value,
        }
```

Хорошо:

```python
class CallbackPayloadMapper:
    def to_payload(self, message: MessageEntity) -> CallbackPayloadDTO:
        ...
```

### 28.5. Pydantic as Domain
Плохо:

```python
class MessageEntity(BaseModel):
    ...
```

Хорошо:

```python
@dataclass(slots=True)
class MessageEntity:
    ...
```

Pydantic используется только на границе ввода/вывода.

## 29. Правило добавления новой фичи
При добавлении новой фичи порядок работы строго такой:
1. Описать бизнес-сценарий.
2. Определить aggregate/entity/value objects.
3. Описать domain errors.
4. Описать domain behavior.
5. Написать domain tests.
6. Создать command/query.
7. Создать use case.
8. Определить нужные ports.
9. Написать application tests через fake ports.
10. Реализовать infrastructure adapters.
11. Написать infrastructure tests.
12. Создать presentation schema/controller.
13. Написать endpoint tests.
14. Подключить зависимости в bootstrap/container.
15. Проверить CI.
Запрещено начинать фичу с базы данных или HTTP controller, если бизнес-правила еще не описаны.

## 30. Правило рефакторинга
При рефакторинге запрещено:
* переносить бизнес-логику наружу из domain;
* усиливать зависимость application от infrastructure;
* смешивать DTO разных слоев;
* добавлять прямые импорты infrastructure в controllers;
* обходить use cases;
* удалять tests без замены;
* упрощать архитектуру за счет нарушения dependency rule.
Любой рефакторинг должен улучшать хотя бы один пункт:
* ясность business model;
* чистоту зависимостей;
* тестируемость;
* изоляцию infrastructure;
* читаемость use cases;
* надежность transaction/idempotency.

## 31. Definition of Done для кода 10/10
Код считается архитектурно готовым, если:
* Domain полностью независим от фреймворков.
* Application полностью независим от infrastructure.
* Все внешние зависимости описаны через ports.
* Infrastructure реализует ports и не содержит бизнес-правил.
* Presentation тонкий и не содержит use case logic.
* Bootstrap централизованно собирает зависимости.
* Entity защищает свои инварианты.
* Value Objects валидируют значимые значения.
* Есть create() и restore() там, где нужно.
* Ошибки разделены на Domain/Application/Presentation.
* Есть idempotency для повторяемых команд.
* Есть tests для Domain/Application/Infrastructure/Presentation.
* CI запускает lint/typecheck/tests.
* Нет forbidden imports между слоями.
* Нет внешнего JSON/API контракта внутри Domain.
* Нет прямой мутации aggregate state извне.

## 32. Краткая инструкция для AI/code generation
При генерации нового кода строго соблюдай:
1. Сначала Domain: Entity, VO, Errors, Events, Policies.
2. Затем Application: Command/Query, UseCase, Ports, Result DTO.
3. Затем Infrastructure: adapters, mappers, persistence.
4. Затем Presentation: request/response schemas, controllers.
5. Затем Bootstrap: wiring/container.
6. Затем Tests.
Не используй FastAPI/Pydantic/Redis/HTTPX в Domain/Application.
Не возвращай domain entity из HTTP controller.
Не создавай infrastructure clients внутри use case.
Не храни business rules в controller, repository или mapper.
Все бизнес-инварианты должны быть в Domain.
Все сценарии должны быть в Application.
Все технические детали должны быть в Infrastructure.
Все внешние входы должны проходить через Presentation.
Все зависимости должны собираться в Bootstrap.
Если правило нарушается — код считается архитектурно неправильным.
