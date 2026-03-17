# Правила написания кода в проекте

## 1. Общие принципы

Проект строится по принципам:

* **DDD**
* **Clean Architecture**
* **строгое разделение слоёв**
* **явная модульность по bounded context / feature module**
* **dependency wiring только в отдельном слое сборки**

Каждый бизнес-контекст должен быть расположен в **отдельном модуле**.
Примеры контекстов:

* `channel`
* `message`
* `customer`
* `order`
* `tenant`
* `workspace`

Каждый такой модуль должен иметь собственную реализацию слоёв:

* `Domain`
* `Application`
* `Presentation`
* `Infrastructure`

Нельзя смешивать код разных слоёв и разных контекстов в одном файле или одном модуле.

---

## 2. Обязательная структура проекта

Каждый контекст оформляется как отдельный модуль.

Пример:

```text
src/modules/
├── channel/
│   ├── domain/
│   ├── application/
│   ├── presentation/
│   │   ├── http/
│   │   └── depends/
│   │       ├── application.py
│   │       ├── infrastructure.py
│   │       └── security.py
│   ├── infrastructure/
│   └── ...
│
├── message/
│   ├── domain/
│   ├── application/
│   ├── presentation/
│   │   └── router.py
│   │   └── depends/
│   │       ├── application.py
│   │       └── infrastructure.py
│   ├── infrastructure/
│   └── ...
```
---

## 3. Правило модульности

### 3.1. Один контекст = один модуль

Каждый bounded context реализуется в собственном модуле.

### 3.2. Контексты не должны напрямую использовать инфраструктуру друг друга

Например:

* модуль `message` не должен импортировать ORM-модели из `channel.infrastructure`
* модуль `channel` не должен зависеть от контроллеров `message.presentation`

### 3.3. Связь между контекстами только через:

* value objects / ids
* application contracts
* domain contracts
* orchestrating use cases
* domain services, если это действительно доменное правило

---

## 4. Обязательные слои внутри каждого модуля

Каждый модуль должен содержать 4 слоя:

```text
<module>/
├── domain/
├── application/
├── presentation/
└── infrastructure/
```

---

# 5. Правила для слоя Domain

Слой `Domain` содержит только бизнес-модель предметной области.

## 5.1. В Domain разрешено размещать

* `Entity`
* `Aggregate Root`
* `Value Object`
* `Domain Service`
* `Repository Protocol`
* `Domain Error`
* `Domain Event` при необходимости

## 5.2. В Domain запрещено размещать

* ORM модели
* SQLAlchemy
* FastAPI
* Pydantic-схемы для HTTP
* session / transaction manager
* JSON response models
* DI контейнер
* работу с сетью
* работу с файловой системой
* HTTP/REST/gRPC transport code

## 5.3. Domain не должен знать о технических деталях

Domain не должен зависеть от:

* базы данных
* ORM
* web framework
* брокеров сообщений
* кэша
* инфраструктурных библиотек

## 5.4. Domain должен содержать инварианты

Вся бизнес-валидация, которая относится к предметной модели, должна жить в Domain.

Примеры:

* пустой `title` недопустим
* опубликованное сообщение нельзя редактировать
* сущность не может перейти в недопустимое состояние

## 5.5. Репозитории в Domain — только как Protocol

В Domain описываются только контракты репозиториев, без реализации.

Пример:

```python
class ChannelRepository(Protocol):
    async def get_by_id(self, channel_id: ChannelIdVO) -> ChannelEntity | None:
        ...
```

## 5.6. Domain Service

Domain service допускается только если:

* логика действительно доменная
* логика не принадлежит естественным образом одной сущности
* логика координирует несколько агрегатов или доменных объектов

Domain service не должен:

* читать из БД
* создавать session
* выполнять commit / rollback
* знать про repository implementation

Domain service работает только с уже загруженными доменными объектами.

## 5.7. Нормализация и парсинг в Domain

Любая технически простая, но доменно значимая нормализация должна жить в `Value Object`:

* `strip()/trim`
* приведение строк к каноническому виду
* парсинг `str -> enum/VO`
* локальная валидация формата (`uuid`, `snake_case`, ограничения длины и т.д.)

В `entities.py` запрещено держать дублирующие свободные функции вида
`_parse_*`, `_validate_*`, если эту же ответственность можно инкапсулировать в VO.

## 5.8. Правило `__post_init__` для dataclass в Domain

Если `Entity` или `Value Object` реализованы через `@dataclass`, то:

* инварианты и нормализация состояния должны выполняться в `__post_init__`
* фабрики (`create`) должны оркестрировать создание (id, время, дефолты), а не дублировать валидацию
* объект после `__post_init__` должен всегда находиться в валидном доменном состоянии

Это гарантирует одинаковое поведение как при создании через фабрику, так и при прямой инициализации.

---

# 6. Правила для слоя Application

Слой `Application` описывает сценарии использования системы.

## 6.1. В Application разрешено размещать

* `UseCase`
* `Command`
* `Query`
* `DTO`
* `UnitOfWork` contract
* application-level policies
* orchestration logic

## 6.2. В Application запрещено размещать

* ORM модели
* SQL запросы
* FastAPI endpoints
* HTTP request/response модели
* конкретные реализации repository
* создание engine/session
* wiring зависимостей

## 6.3. Задача UseCase

UseCase должен:

* открыть транзакционную границу через `UnitOfWork`
* загрузить агрегаты через repository contracts
* вызвать методы доменных сущностей или domain service
* сохранить изменения через repository
* выполнить `commit`
* вернуть `DTO`

UseCase не должен:

* напрямую работать с ORM
* содержать HTTP-логику
* содержать SQL
* импортировать инфраструктурную реализацию репозитория

## 6.4. Application использует только абстракции

UseCase должен зависеть от:

* `UnitOfWork` protocol
* `Repository` protocol
* domain entities
* domain services

Нельзя зависеть от `SqlAlchemyRepository`, `AsyncSession`, `FastAPI Depends` и т.д.

## 6.5. DTO

DTO используются для возврата данных из application в presentation.

DTO не должны быть ORM моделями и не должны быть HTTP transport schema.

## 6.6. Commands и Queries

Для каждого use case входные данные должны быть оформлены явно:

* `Command` — для операций изменения состояния
* `Query` — для операций чтения

Нельзя передавать в use case сырой request object из FastAPI.

---

# 7. Правила для слоя Presentation

Слой `Presentation` отвечает только за транспорт.

## 7.1. В Presentation разрешено размещать

* controllers / routers
* `depends/*` wiring-композицию по слоям (application/infrastructure/security)
* request schema
* response schema
* mapping transport → command/query
* mapping DTO → response
* mapping domain/application errors → HTTP errors

## 7.2. В Presentation запрещено размещать

* бизнес-логику
* SQL
* ORM
* транзакции
* domain state mutation
* repository implementation

## 7.3. Controller должен быть тонким

Controller должен:

* принять HTTP request
* провалидировать transport schema
* создать `Command` или `Query`
* вызвать нужный `UseCase`
* преобразовать результат в response schema
* отобразить ошибки в HTTP status

Controller не должен:

* управлять транзакцией
* вызывать session.commit
* содержать бизнес-правила
* напрямую читать или писать в БД

## 7.4. Presentation ничего не знает о деталях persistence

Контроллер не должен импортировать:

* ORM models
* SQLAlchemy repositories
* session factory

---

# 8. Правила для слоя Infrastructure

Слой `Infrastructure` реализует технические детали.

## 8.1. В Infrastructure разрешено размещать

* ORM models
* repository implementations
* mappers
* session factory
* database adapters
* внешние gateway implementations
* integrations

ORM-модели должны храниться в `src/modules/*/infrastructure/persistence/*` каждого модуля.
Прямые импорты ORM допустимы только из `infrastructure/persistence/*`.

## 8.2. В Infrastructure запрещено размещать бизнес-логику

Infrastructure не должна принимать бизнес-решения.

Она должна только:

* сохранять
* загружать
* сериализовать
* маппить
* вызывать внешние системы

## 8.3. Repository implementation

Реализация репозитория обязана:

* реализовывать contract из Domain
* возвращать domain entity, а не ORM object
* не протаскивать ORM object наружу

## 8.4. Mapper обязателен

Преобразование между ORM и Domain должно выполняться через mapper.

Нельзя:

* возвращать ORM model в Application
* мутировать Domain из Presentation
* хранить ORM в Domain

---

# 9. Правила для Wiring

`Wiring` — это отдельное место для сборки зависимостей.
В проекте wiring размещается в `presentation/depends/*` и декомпозируется по слоям.

## 9.1. Wiring обязан быть явным

Все зависимости собираются только в `presentation/depends/*`.

Примеры:

* создание session factory
* создание repository implementations
* создание UoW implementation
* создание domain service
* создание use cases
* создание controllers
* подключение router к app

## 9.2. Запрещено создавать инфраструктурные зависимости внутри use case и controller

Нельзя делать так:

```python
class CreateChannelUseCase:
    def __init__(self):
        self.session = AsyncSession(...)
```

или

```python
@router.post(...)
async def create():
    repo = SqlAlchemyChannelRepository(...)
```

Это нарушение архитектуры.

## 9.3. Wiring — единственная точка композиции

Только wiring (`presentation/depends/*`) знает о concrete classes.

---

# 10. Правила работы с агрегатами

## 10.1. Сначала определить границу агрегата

При проектировании новой сущности сначала определить:

* это отдельный агрегат
* это child entity внутри существующего aggregate root

## 10.2. Если это отдельный агрегат

Тогда:

* у агрегата свой repository
* у агрегата свой CRUD
* ссылки на другие агрегаты только через ID / ValueObject
* координация между агрегатами через use case и при необходимости domain service

## 10.3. Если это часть одного агрегата

Тогда:

* отдельный repository для child entity не создаётся
* работа идёт через aggregate root
* изменение child entity происходит через методы root

## 10.4. Нельзя размывать границы агрегатов

Если `Message` — отдельный агрегат, нельзя:

* держать его ORM-жизненный цикл внутри `Channel` application layer
* обновлять его напрямую из `ChannelController`
* обходить собственный repository/use case

---

# 11. Правила CRUD

Для каждой aggregate root сущности CRUD должен быть реализован через отдельные use cases.

Минимальный набор:

* `Create<Entity>UseCase`
* `Get<Entity>UseCase`
* `List<Entity>UseCase`
* `Update<Entity>UseCase`
* `Delete<Entity>UseCase`

## 11.1. Каждый use case — отдельный класс

Один use case = один класс = один сценарий.

## 11.2. Нельзя делать “универсальный сервис на всё”

Запрещены классы вида:

* `ChannelService` со всеми методами CRUD
* `MessageManager`
* `UniversalCrudService`

Если это application layer, сценарии должны быть разделены на отдельные use case classes.

---

# 12. Правила именования

## 12.1. Domain

* `ChannelEntity`
* `MessageEntity`
* `ChannelIdVO`
* `MessageBodyVO`
* `ChannelRepository`
* `ChannelNotFoundError`

## 12.2. Application

* `CreateChannelCommand`
* `UpdateMessageCommand`
* `GetChannelQuery`
* `ListMessagesByChannelQuery`
* `ChannelDTO`
* `CreateChannelUseCase`

## 12.3. Infrastructure

* `ChannelORM`
* `MessageORM`
* `SqlAlchemyChannelRepository`
* `SqlAlchemyUnitOfWork`
* `ChannelMapper`

## 12.4. Presentation

* `CreateChannelRequest`
* `ChannelResponse`
* `ChannelController`

---

# 13. Правила файловой организации внутри модуля

Рекомендуемая структура:

```text
channel/
├── domain/
│   ├── entities.py
│   ├── value_objects.py
│   ├── repositories.py
│   ├── errors.py
│   └── services.py
│
├── application/
│   ├── dto.py
│   ├── commands.py
│   ├── queries.py
│   └── use_cases/
│       ├── create_channel.py
│       ├── update_channel.py
│       ├── delete_channel.py
│       ├── get_channel.py
│       └── list_channels.py
│
├── presentation/
│   ├── http/
│   │   ├── schemas.py
│   │   └── controller.py
│   └── depends/
│       ├── application.py
│       ├── infrastructure.py
│       └── security.py
│
├── infrastructure/
│   ├── persistence/
│   │   ├── channel.py
│   │   └── message.py
│   ├── mappers.py
│   ├── repositories.py
│   └── session.py
```

Для сложных модулей допускается дальнейшая декомпозиция, но границы слоёв должны оставаться очевидными.

---

# 14. Правила импортов

## 14.1. Допустимые направления зависимостей

Разрешено:

```text
presentation -> application
application -> domain
infrastructure -> domain
infrastructure -> application
presentation/depends (wiring) -> application + infrastructure + domain
```

## 14.2. Запрещённые направления зависимостей

Запрещено:

```text
domain -> application
domain -> infrastructure
domain -> presentation

application -> infrastructure
application -> presentation

presentation -> infrastructure
```

`presentation/http/*` может знать только application abstractions.
`presentation/depends/*` как wiring может знать concrete infra classes.

---

# 15. Правила ошибок

## 15.1. Domain errors

Ошибки бизнес-правил должны быть описаны в Domain.

Примеры:

* `ChannelNotFoundError`
* `MessageAlreadyPublishedError`
* `InvalidChannelTitleError`

## 15.2. Presentation делает transport mapping

Только presentation решает, что:

* `ChannelNotFoundError` → `404`
* `InvalidChannelTitleError` → `400`
* `MessageAlreadyPublishedError` → `409`

## 15.3. Нельзя бросать HTTPException в Domain или Application

Это строго запрещено.

---

# 16. Правила транзакций

## 16.1. Транзакция управляется в Application через UoW

UseCase открывает границу транзакции через:

```python
async with self._uow:
    ...
    await self._uow.commit()
```

## 16.2. Domain не управляет транзакцией

Сущности и domain service не знают о commit/rollback.

## 16.3. Controller не управляет транзакцией

Транзакции не должны жить в presentation.

---

# 17. Правила маппинга

Должно быть явное разделение моделей:

* Domain Entity
* DTO
* ORM Model
* HTTP Request/Response Schema

Они не взаимозаменяемы.

## 17.1. Запрещено

* использовать ORM как DTO
* возвращать Domain Entity напрямую как JSON
* использовать Pydantic request schema как domain entity
* протаскивать ORM models в domain/application

## 17.2. Обязательно

* ORM ↔ Domain через mapper
* DTO → Response schema в presentation
* Request schema → Command/Query в presentation

---

# 18. Правила написания кода Agent

Agent обязан:

## 18.1. При создании нового контекста

* создавать отдельный модуль
* создавать все 4 слоя
* добавлять `presentation/depends/*` для wiring
* не смешивать код других контекстов

## 18.2. При добавлении новой сущности

сначала определить:

* aggregate root это или нет
* нужен ли отдельный repository
* нужен ли отдельный CRUD
* является ли связь между сущностями межагрегатной или внутри агрегата

## 18.3. При добавлении межагрегатной логики

* использовать orchestration в use case
* использовать domain service только если есть доменное правило
* не помещать межагрегатную логику в ORM/repository/controller

## 18.4. При написании кода

Agent не должен:

* сокращать архитектуру в “service layer only”
* смешивать use case и repository в одном классе
* писать “fat controller”
* писать доменную логику в infrastructure
* использовать глобальные session внутри domain/application

---

# 19. Базовый шаблон разработки нового модуля

Для каждого нового модуля Agent должен идти в таком порядке:

## Шаг 1. Определить aggregate root

Определить главную доменную сущность.

## Шаг 2. Описать Domain

Создать:

* entity
* value objects
* errors
* repository protocols
* domain services при необходимости

## Шаг 3. Описать Application

Создать:

* commands
* queries
* dto
* use cases
* uow contract, если он общий — использовать существующий

## Шаг 4. Описать Infrastructure

Создать:

* orm model
* mapper
* repository implementation
* uow implementation / подключение к существующему

## Шаг 5. Описать Presentation

Создать:

* request schema
* response schema
* controller/router

## Шаг 6. Сделать Wiring

Собрать зависимости в `presentation/depends/*` и подключить модуль к приложению.

---

# 20. Эталон качества кода

Каждая реализация должна соответствовать следующим требованиям:

* код читается по слоям
* зависимости направлены только внутрь
* доменная модель изолирована
* инфраструктура не протекает наружу
* use case решает один сценарий
* wiring отделён
* каждый контекст автономен
* межагрегатная логика явно оформлена
* CRUD реализован через отдельные use case
* никакого смешивания transport / domain / persistence моделей

---

# 21. Краткое правило для Agent

При генерации кода всегда соблюдать:

1. **Один контекст = один отдельный модуль**
2. **В модуле всегда 4 слоя: Domain, Application, Presentation, Infrastructure**
3. **Все зависимости собираются только в `presentation/depends/*` (wiring)**
4. **Domain не знает ни о чём кроме бизнес-модели**
5. **Application оркестрирует сценарии и работает только через абстракции**
6. **Presentation только принимает/отдаёт данные**
7. **Infrastructure только реализует технические детали**
8. **Никакого смешивания слоёв**
9. **Никакого fat controller / fat repository / universal service**
10. **Любая межагрегатная логика должна быть явно оформлена через use case и при необходимости domain service**
