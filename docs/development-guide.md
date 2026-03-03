# Development Guide

## Зачем нужен этот документ

Этот файл — стартовая точка для разработки в `dnk-runtime-core`.

Его цель:

- быстро объяснить, как устроен проект;
- показать, где в проекте должен жить новый код;
- зафиксировать правила по слоям, use case'ам, сервисам, репозиториям и HTTP-роутам;
- снизить риск смешивания бизнес-логики, инфраструктуры и transport-слоя.

Документ описывает текущее фактическое устройство проекта, а не абстрактную "идеальную" архитектуру.

## Коротко о проекте

`dnk-runtime-core` — backend на `FastAPI` + `SQLAlchemy AsyncIO`, построенный вокруг модульной архитектуры в `src/modules`.

На март 2026 года в проекте реально работают:

- `tenancy`
- `identity`

Каркасами без прикладной логики пока остаются:

- `crm`
- `catalog`
- `org`

Главные архитектурные опоры проекта:

- проект делится на bounded contexts по модулям;
- каждый модуль имеет слои `presentation`, `application`, `domain`, `infrastructure`;
- один HTTP request должен проходить через один `UoW` и одну SQLAlchemy session;
- `shared` хранит только технические cross-module механизмы;
- межмодульное взаимодействие идет через application-контракты и adapters, а не через прямой доступ к чужим ORM-моделям.

## Точки входа

Актуальные входные файлы:

- `src/app.py` — экспортирует `app`;
- `src/app_factory.py` — собирает приложение;
- `src/dnk_app.py` — тип приложения;
- `src/modules/router.py` — общий API router.

В `lifespan` приложения сейчас происходит:

1. регистрация `session_factory` в `app.state.db`;
2. регистрация `db_helper` в `app.state.db_helper`;
3. создание схемы БД через `create_all()`;
4. освобождение ресурсов через `dispose()` при остановке.

Дополнительно через `app.state` могут переопределяться технические зависимости:

- `token_manager`
- `email_sender`

Это активно используется в тестах.

## Актуальная структура проекта

```text
src/
  app.py
  app_factory.py
  dnk_app.py
  config/
  modules/
    router.py
    shared/
    tenancy/
    identity/
    crm/
    catalog/
    org/
test/
docs/
```

Ключевая рабочая зона проекта — `src/modules`.

Если начинаешь новую бизнес-фичу, почти всегда твоя работа будет внутри одного из каталогов:

- `src/modules/<module_name>/domain`
- `src/modules/<module_name>/application`
- `src/modules/<module_name>/infrastructure`
- `src/modules/<module_name>/presentation`

## Как мыслить модулем

Модуль в этом проекте — это bounded context со своей ответственностью.

Примеры:

- `tenancy` владеет `Tenant`, `TenantDomain`, статусами tenant/domain и resolve tenant по host;
- `identity` владеет `User`, `UserEmail`, tenant-scoped auth-flow и OTP/session поведением.

Практическое следствие:

- если правило относится к tenant lifecycle, оно должно жить в `tenancy`;
- если правило относится к user/email/login, оно должно жить в `identity`;
- если логика нужна многим модулям, но она предметная, не нужно уносить ее в `shared`;
- в `shared` можно класть только технические механизмы общего назначения.

## Главные архитектурные правила

### 1. Не смешивай слои

- `presentation` принимает/отдает HTTP и собирает зависимости;
- `application` orchestrates use cases и межслойные вызовы;
- `domain` хранит бизнес-сущности и правила;
- `infrastructure` работает с БД и внешними системами.

### 2. Не читай чужой модуль напрямую через ORM

Если модулю `identity` нужен tenant-context, он не лезет в `tenancy` persistence-модели напрямую.

Правильный путь:

1. определить порт в `application`;
2. реализовать adapter в `presentation/depends`;
3. вызвать use case другого модуля.

В проекте так уже сделано:

- `TenantContextReaderPort`
- `TenancyTenantContextReaderAdapter`

### 3. Один request = один UoW

Все репозитории внутри запроса должны работать на одной `uow.session`.

Для этого используются:

- `src/modules/shared/uow.py`
- `src/modules/shared/depends/uow.py`

### 4. DTO и transport-схемы не смешиваются

В проекте есть два разных типа объектов:

- Pydantic-схемы для HTTP;
- dataclass DTO для application-слоя.

Маршрут:

1. принимает `RequestSchema`;
2. маппит его в `CommandDTO` или `QueryDTO`;
3. вызывает use case;
4. маппит `ResultDTO` в `ResponseSchema`.

### 5. Бизнес-ошибки должны быть доменными

Бизнес-ограничения выражаются через domain/application errors, а не через `HTTPException` внутри domain/application.

`HTTPException` допустим только в `presentation`.

## Request Flow: как проходит запрос

Типичный request flow в проекте выглядит так:

1. router принимает HTTP-запрос;
2. FastAPI dependencies собирают `UoW`, repositories, services, use cases;
3. route маппит Pydantic payload в application DTO;
4. use case выполняет сценарий;
5. при необходимости application использует domain entities, ports и services;
6. infrastructure repositories читают/пишут БД;
7. route маппит результат в response schema;
8. route преобразует domain/application ошибки в HTTP-ответ.

Примеры:

- `POST /api/admin/create-tenant`
- `POST /api/console/auth/request-otp`
- `POST /api/console/auth/confirm-otp`
- `GET /api/console/tenants/resolve`

## Слой `domain`

### Что хранить в `domain`

В `domain` должны жить:

- сущности;
- value objects;
- доменные методы;
- доменные ошибки;
- инварианты и проверки корректности.

Примеры:

- `Tenant.create(...)`
- `Tenant.allows_login()`
- `TenantDomain.create_primary(...)`
- `User.create_tenant_admin(...)`
- `User.add_email(...)`
- `User.mark_email_verified(...)`

### Чего не должно быть в `domain`

В `domain` не должно быть:

- `FastAPI`;
- `Request`, `Response`, `Depends`;
- `HTTPException`;
- SQLAlchemy `select`, `update`, ORM models;
- работы с Redis;
- чтения config из `dnk_config`.

### Как писать domain entity

Текущий стиль проекта:

- использовать `@dataclass(slots=True)` для сущностей;
- использовать classmethod-конструкторы вроде `create(...)`, `create_primary(...)`, `create_tenant_admin(...)`;
- нормализовать входные данные внутри доменной операции;
- валидировать инварианты сразу;
- бросать `ValidationError` или специализированные наследники.

Пример существующего паттерна:

- строки нормализуются через `strip()`;
- email нормализуется через `strip().lower()`;
- host нормализуется через `strip().lower()`;
- пустые обязательные значения приводят к `ValidationError`.

### Какой метод должен быть у сущности

Метод сущности уместен, если он:

- меняет состояние этой же сущности;
- проверяет ее бизнес-правила;
- не требует инфраструктуры;
- делает правило более явным, чем размазывание `if` по use case'ам.

Хорошие примеры:

- `user.can_login()`
- `tenant.allows_write_business_data()`
- `user.get_primary_email(email)`
- `user.mark_email_verified(user_email_id)`

Плохие примеры:

- `tenant.save()`
- `user.load_by_email()`
- `tenant.send_email()`

### Value Objects

Если в модуле есть устойчивый набор предметных значений, он выносится в value objects.

В `tenancy` это уже сделано через enum-like объекты:

- `TenantStatus`
- `TenantDomainStatus`
- `TenantDomainKind`
- `TenantServiceType`
- `TenantDomainTlsMode`

Если новое правило строится вокруг конечного набора состояний, сначала подумай, не нужен ли новый value object.

## Слой `application`

`application` — это слой прикладных сценариев.

Он отвечает на вопрос: "как именно система исполняет конкретный сценарий".

### Как устроен `application`

В проекте application организован слайсами.

Примеры:

- `tenancy/application/admin_onboarding`
- `tenancy/application/resolve_tenant_by_host`
- `tenancy/application/request_context_by_host`
- `identity/application/auth`
- `identity/application/provisioning`

Это правильный ориентир и для новых фич: не складывать всё в один общий файл, а делать отдельный slice на конкретный сценарий или группу тесно связанных сценариев.

### Что хранить в `application`

В `application` должны жить:

- DTO команд, запросов и результатов;
- use case'ы;
- application services;
- ports/protocols для внешних зависимостей;
- orchestration-логика;
- транзакционные границы write-сценариев.

### DTO

В проекте application DTO оформляются так:

- `@dataclass(frozen=True, slots=True)`
- отдельные типы для command/query/result

Примеры:

- `CreateTenantCommandDTO`
- `CreateTenantResultDTO`
- `ResolveTenantByHostQueryDTO`
- `ConfirmEmailOtpCommandDTO`
- `LogoutCurrentSessionResultDTO`

Правило:

- DTO не содержат поведения;
- DTO не знают про HTTP;
- DTO не должны быть SQLAlchemy models;
- DTO нужны для явного контракта между route и use case.

### Use Case

Use case — это основной исполнитель прикладного сценария.

Текущий стиль проекта:

- отдельный класс на сценарий;
- основной публичный метод — `execute(...)`;
- вход — DTO;
- выход — DTO;
- зависимости приходят через конструктор;
- use case зависит от protocol/port, а не от конкретной инфраструктуры.

Примеры:

- `CreateTenantUseCase.execute(dto)`
- `ResolveTenantByHostUseCase.execute(dto)`
- `GetTenantRequestContextByHostUseCase.execute(dto)`
- `RequestEmailOtpUseCase.execute(dto)`
- `ConfirmEmailOtpUseCase.execute(dto)`

### Когда нужен service внутри `application`

Application service нужен, если:

- часть бизнес-логики переиспользуется в нескольких сценариях;
- use case становится перегружен деталями;
- нужно выделить предметную операцию поверх entity/repository.

В проекте так уже сделано:

- `TenantService.create_tenant(...)`
- `TenantDomainService.create_primary_domain(...)`
- `UserService.create_tenant_admin(...)`

Правило:

- service не должен знать про HTTP;
- service может знать про repository protocol;
- service не должен тянуть в себя transport-концепции.

### Ports / Protocols

Порты описываются через `Protocol`.

Их задача — отделить use case от конкретной реализации.

В проекте есть несколько характерных групп:

- repository ports;
- service protocols;
- cross-module ports;
- external-system ports.

Примеры:

- `TenantRepositoryProtocol`
- `TenantDomainRepositoryProtocol`
- `UserRepositoryProtocol`
- `AuthUserRepositoryPort`
- `TenantContextReaderPort`
- `OtpChallengeStorePort`
- `SessionStorePort`
- `EmailSenderPort`

Правило:

- если use case зависит от базы или внешней системы, он должен зависеть от порта;
- конкретный SQLAlchemy/Redis/adapter код должен оставаться вне use case.

### Границы транзакции

Write-сценарии в текущем проекте используют `UnitOfWorkProtocol`.

Практический паттерн:

1. use case получает `uow`;
2. вызывает сервисы и репозитории;
3. на успешном пути делает `commit()`;
4. при ошибке делает `rollback()` и пробрасывает исключение дальше.

Так сейчас работают как минимум:

- `CreateTenantUseCase`
- `ConfirmEmailOtpUseCase`

Правило для новых write use case'ов:

- если сценарий меняет постоянное состояние, держи транзакционную оркестрацию в use case;
- не размазывай `commit()` по роутам;
- не прячь бизнес-транзакцию в repository.

### Read Use Case

Read use case должен быть максимально прямым:

- получить данные;
- собрать result DTO;
- не писать в БД;
- не делать лишних side effects.

Хороший пример:

- `ResolveTenantByHostUseCase`

### Разница между query и strict context use case

В проекте есть два показательных паттерна:

- `ResolveTenantByHostUseCase` возвращает read-model и не кидает ошибку для обычного `not_found`;
- `GetTenantRequestContextByHostUseCase` нужен внутренним сценариям и кидает доменные ошибки, если host/tenant невалидны.

Это полезный ориентир:

- внешний UI-read endpoint часто удобнее делать tolerant;
- внутренний security/business use case должен быть строгим.

## Слой `infrastructure`

### Что хранить в `infrastructure`

В `infrastructure` должны жить:

- SQLAlchemy persistence models;
- repositories;
- mapping domain <-> persistence;
- adapters к Redis и другим внешним системам;
- техническая интеграция с runtime.

### Persistence Models

ORM-модели живут в `infrastructure/persistence`.

Примеры:

- `TenantModel`
- `TenantDomainModel`
- `UserModel`
- `UserEmailModel`

Правило:

- ORM-модель описывает таблицу;
- ORM-модель не должна содержать бизнес-логику bounded context;
- название должно быть `<EntityName>Model`.

### Repository

Репозиторий в проекте:

- получает `AsyncSession` в конструктор;
- реализует application protocol;
- делает минимально необходимый SQLAlchemy-запрос;
- маппит ORM-model в domain entity;
- не занимается HTTP-ошибками;
- не должен принимать `Request`.

Текущие примеры:

- `SqlAlchemyTenantRepository`
- `SqlAlchemyTenantDomainRepository`
- `SqlAlchemyUserRepository`

### Правила для методов репозитория

- имя метода должно описывать предметный запрос, а не SQL-деталь;
- метод должен возвращать domain entity или примитив, который нужен use case;
- если нужен `exists`, пусть это будет явный `exists_*` метод;
- если нужен update, он должен быть узким и явным.

Хорошие примеры:

- `exists_by_name`
- `exists_by_external_id`
- `get_by_tenant_and_primary_email`
- `mark_email_verified`
- `get_api_host_by_tenant_id`

### Mapping

Mapping сейчас хранится рядом с repository, обычно через приватные методы:

- `_map_tenant(...)`
- `_map_domain(...)`
- `_map_user(...)`
- `_map_email(...)`

Это хороший текущий стандарт для проекта:

- mapping остается локальным;
- use case не должен знать, как SQLAlchemy превращается в domain entity.

## Слой `presentation`

`presentation` — это HTTP-граница и composition root модуля.

### Что хранить в `presentation`

В `presentation` должны жить:

- routers;
- request/response schemas;
- FastAPI dependencies;
- adapters, собирающие application dependencies;
- преобразование доменных ошибок в HTTP-ответы.

### Router

Текущий стиль:

- у каждого набора endpoint'ов свой `APIRouter`;
- модульный `presentation/api/router.py` агрегирует внутренние роутеры;
- `src/modules/router.py` агрегирует модульные router'ы.

Примеры:

- `tenancy/presentation/api/admin_tenants.py`
- `tenancy/presentation/api/console_tenants.py`
- `identity/presentation/api/console_auth.py`

### Request / Response Schema

HTTP-схемы лежат отдельно:

- `presentation/api/requests/*`
- `presentation/api/responses/*`

Текущий стиль:

- использовать `pydantic.BaseModel`;
- применять transport-level типы вроде `EmailStr`;
- не тянуть эти классы в domain.

### Что должен делать route handler

Route handler в этом проекте должен:

1. принять Pydantic schema и зависимости;
2. преобразовать transport payload в DTO;
3. вызвать use case;
4. отловить доменные ошибки;
5. превратить их в `HTTPException`;
6. собрать response schema;
7. при необходимости выставить cookie или headers.

Route handler не должен:

- писать SQLAlchemy-запросы;
- реализовывать бизнес-правила;
- напрямую манипулировать ORM-model;
- искать tenant или user вручную, если уже есть use case.

### FastAPI Depends как composition root

Сборка зависимостей сосредоточена в `presentation/depends`.

Показательный паттерн:

- `repositories.py` — отдает repository implementations;
- `services.py` — собирает application services;
- `use_cases.py` или `auth_use_cases.py` — собирает use case;
- `auth_repositories.py` — адаптеры под auth ports;
- `control_plane_auth.py` — transport/security dependency.

Это важное правило проекта:

- wiring зависимостей не должен жить в `application`;
- wiring — обязанность `presentation`.

### Annotated dependency aliases

В проекте активно используются алиасы вида:

```python
SomethingDep = Annotated[SomethingProtocol, Depends(get_something)]
```

Это хороший локальный стандарт. Для новых зависимостей придерживайся той же формы.

## Слой `shared`

`shared` — только для технических cross-module штук.

Сейчас сюда относятся:

- `shared.db`
- `shared.uow`
- `shared.http`
- `shared.tokens`

### Что допустимо класть в `shared`

- базовые DB helpers;
- общие типы для persistence;
- request host extraction/normalization;
- token/session storage infrastructure;
- общие технические протоколы.

### Что нельзя класть в `shared`

- правила tenant lifecycle;
- правила auth/login;
- `User`, `Tenant`, `TenantDomain`;
- статусы конкретного bounded context;
- бизнес-ошибки конкретного модуля.

Критерий простой:

- если код имеет предметный смысл только для одного bounded context, ему не место в `shared`.

## Слой `config`

`src/config` агрегирует runtime settings через `DnkConfig`.

Основные группы:

- `DatabaseConfig`
- `RedisConfig`
- `IdentityAuthConfig`
- `ControlPlaneConfig`
- `PackagingInfo`

Практические правила:

- новый runtime config сначала нужно отнести к подходящей config-группе;
- не разбрасывать чтение env напрямую по модулям;
- в коде использовать `dnk_config`, а не `os.environ`;
- nested auth-настройки задаются через `AUTH__...`.

## Как выбрать слой для нового кода

Ниже быстрый ориентир "что куда класть".

| Что добавляешь | Куда класть |
| --- | --- |
| Новое бизнес-правило сущности | `domain` |
| Новый enum/value object статусов | `domain/value_objects` |
| Новую бизнес-ошибку модуля | `domain/errors.py` |
| Новый сценарий чтения/записи | `application/<slice>/use_case.py` |
| Новые DTO сценария | `application/<slice>/dto.py` |
| Новый repository contract | `application/.../ports/...` |
| Новый domain-oriented service | `application/.../services/...` |
| SQLAlchemy model | `infrastructure/persistence` |
| SQLAlchemy repository implementation | `infrastructure/repositories.py` |
| HTTP endpoint | `presentation/api/*.py` |
| HTTP request/response schema | `presentation/api/requests|responses` |
| DI wiring и adapters | `presentation/depends/*.py` |
| Технический общий helper | `shared/*` |

## Как писать новые методы

### Domain methods

Пиши domain method, если он:

- работает на самой сущности;
- поддерживает инварианты;
- не требует внешней инфраструктуры.

Рекомендации:

- название должно выражать бизнес-действие;
- внутри метода нормализуй вход;
- обновляй `updated_at`, если состояние меняется;
- бросай доменные ошибки, если операция недопустима.

Примеры имен:

- `create_*`
- `add_*`
- `mark_*`
- `allows_*`
- `can_*`
- `get_*`

### Service methods

Пиши application service method, если нужно:

- сделать проверку через repository;
- сконструировать entity;
- сохранить entity;
- переиспользовать этот шаг в разных use case'ах.

Рекомендации:

- сервис должен возвращать domain entity или специальный application result;
- не зашивай HTTP-коды;
- не скрывай неявные side effects.

### Use case methods

У use case в этом проекте стандартный интерфейс:

- один основной публичный метод `execute(...)`.

Рекомендации:

- принимай DTO, а не произвольный набор параметров;
- use case должен описывать цель сценария, а не внутреннюю механику;
- не делай внутри него сложный SQLAlchemy mapping;
- для write-flow держи commit/rollback рядом с orchestration.

### Repository methods

Рекомендации:

- метод должен быть узким и конкретным;
- не делай "универсальные" query builders без необходимости;
- по возможности следуй существующему словарю имен:
  - `add`
  - `get_by_id`
  - `get_by_*`
  - `exists_by_*`
  - `mark_*`

### Route methods

Рекомендации:

- держи route тонким;
- маппинг ошибок в HTTP делай явно и рядом;
- технические вещи вроде cookie ставь в route, не в domain;
- сложную логику не выноси в dependency только ради сокрытия сложности.

## Нормализация данных

В проекте уже есть выраженные паттерны нормализации. Новому коду важно им следовать.

### Email

- использовать `strip().lower()`;
- login искать по primary email;
- deleted email не должен участвовать в login.

### Host

- использовать `normalize_host(...)` из `shared.http.host`;
- host должен быть приведен к lowercase;
- port должен быть отброшен;
- из `Request` host нужно доставать через `RequestHostDep`, а не руками.

### Текстовые обязательные поля

- `name`, `external_id`, `first_name`, `last_name` и подобные значения очищаются через `strip()`;
- пустые строки должны валидироваться как ошибка.

## Ошибки и их преобразование

### Где бросать ошибки

- `domain` и `application` бросают предметные исключения;
- `presentation` переводит их в HTTP semantics.

### Текущие паттерны статусов

Из существующих route'ов уже видно соглашение:

- `409 Conflict` — дубликаты и conflicts;
- `422 Unprocessable Entity` — domain validation;
- `404 Not Found` — tenant/email не найден;
- `403 Forbidden` — login/tenant недоступен;
- `401 Unauthorized` — невалидный OTP или auth failure.

Для новых endpoint'ов придерживайся этого словаря, если нет веской причины сделать иначе.

## Межмодульное взаимодействие

Если одному модулю нужен другой, следуй этому порядку:

1. сначала найди application use case в owning module;
2. если прямого use case нет, добавь application contract;
3. реализуй adapter в `presentation/depends`;
4. не тащи чужой `infrastructure/persistence/*` в свой код.

Хороший существующий пример:

- `identity` использует `tenancy` через `TenantContextReaderPort` и adapter.

## Как добавлять новую фичу

Ниже рекомендуемый чеклист для новой прикладной возможности.

### Шаг 1. Выбери owning module

Сначала ответь на вопрос:

"Кто владеет этой бизнес-сущностью и правилом?"

Если ответ неясен, не начинай с кода. Сначала зафиксируй границы.

### Шаг 2. Определи тип сценария

- `read scenario`
- `write scenario`
- `cross-module scenario`

Это влияет на:

- нужен ли `UoW`;
- нужны ли ports;
- нужны ли side effects;
- как строить result DTO.

### Шаг 3. Добавь или обнови `domain`

Если фича меняет бизнес-модель:

- добавь метод сущности;
- добавь value object;
- добавь доменную ошибку;
- обнови инварианты.

### Шаг 4. Создай application slice

Рекомендуемая структура:

```text
application/
  <slice_name>/
    dto.py
    use_case.py
    ports/
    services/
    __init__.py
```

Если slice маленький, часть файлов может отсутствовать, но принцип разделения лучше сохранять.

### Шаг 5. Опиши ports

Если use case зависит от:

- БД;
- Redis;
- другого модуля;
- email/SMS/внешнего API;

сначала опиши port/protocol в `application`.

### Шаг 6. Реализуй infrastructure adapter

Если это persistence или внешняя интеграция:

- добавь concrete implementation в `infrastructure` или в adapter-файл внутри `presentation/depends`, если речь про wiring к другому use case.

### Шаг 7. Собери dependency graph

В `presentation/depends`:

- repository provider;
- service provider;
- use case provider;
- adapter provider при необходимости.

### Шаг 8. Добавь route и transport schemas

В `presentation/api`:

- request schema;
- response schema;
- route;
- error mapping.

### Шаг 9. Добавь тесты

Минимум проверь:

- happy path;
- ключевые validation/conflict случаи;
- граничные состояния доступа или статусов;
- поведение side effects.

## Как тестировать код в этом проекте

Текущая тестовая база построена на `unittest`.

### Что уже используется

- `unittest.TestCase` для endpoint tests;
- `unittest.IsolatedAsyncioTestCase` для async unit tests;
- `FastAPI TestClient`;
- временная SQLite БД через `aiosqlite`;
- переопределение runtime dependencies через `app.state`.

### Текущие паттерны тестов

Endpoint tests:

- поднимают `DnkApp`;
- подключают общий router;
- подставляют временную `session_factory` в `app.state.db`;
- при необходимости подменяют:
  - `app.state.token_manager`
  - `app.state.email_sender`

Service/repository tests:

- создают временную SQLite БД;
- инициализируют schema через `Base.metadata.create_all`;
- работают с реальными repository implementations или in-memory doubles.

### Что тестировать обязательно

Для write use case или endpoint:

- успешный сценарий;
- rollback/conflict сценарий;
- нормализацию входных данных, если она критична;
- корректность side effects.

Для read use case:

- `found`;
- `not_found`;
- пограничные статусы.

## Naming conventions

Проект уже имеет устойчивые шаблоны имен. Их лучше продолжать.

### Классы

- `*UseCase`
- `*Service`
- `*Protocol`
- `*Port`
- `*Adapter`
- `*Model`
- `*Schema`
- `*DTO`

### Файлы

- `snake_case.py`
- имя файла обычно отражает один сценарий или один объект ответственности

Примеры:

- `create_tenant.py`
- `request_email_otp.py`
- `logout_current_session.py`
- `repositories.py`
- `tenant_domain_service.py`

### Dependency aliases

- `UoWDep`
- `UsersRepositoryDep`
- `AuthSettingsDep`
- `RequestEmailOtpUseCaseDep`

## Практические do / don't

### Do

- держать бизнес-правила в `domain` и `application`;
- использовать `Protocol` для зависимостей use case'ов;
- нормализовать email/host единообразно;
- держать HTTP слой тонким;
- маппить ORM -> domain внутри infrastructure;
- использовать `RequestHostDep` для host;
- использовать `UoWDep` для request-scoped session;
- добавлять отдельные DTO для команд и результатов.

### Don't

- не импортировать чужие ORM-модели в другой bounded context;
- не класть бизнес-логику в `shared`;
- не писать SQLAlchemy-код в route;
- не бросать `HTTPException` из `domain` и `application`;
- не использовать Pydantic schema как внутренний application DTO;
- не читать env напрямую в бизнес-коде;
- не делать repository "богом-объектом" со всей логикой сразу.

## Рекомендуемый шаблон для новой write-фичи

```text
src/modules/<module_name>/
  application/
    <slice_name>/
      dto.py
      use_case.py
      ports/
      services/
  infrastructure/
    persistence/
    repositories.py
  presentation/
    api/
      requests/
      responses/
      <feature>.py
    depends/
      repositories.py
      services.py
      use_cases.py
```

Минимальный сценарий обычно выглядит так:

1. route принимает payload;
2. route строит `CommandDTO`;
3. use case вызывает services/repositories/ports;
4. write use case фиксирует транзакцию;
5. route возвращает `ResponseSchema`.

## Рекомендуемый шаблон для новой read-фичи

Обычно достаточно:

```text
application/
  <slice_name>/
    dto.py
    use_case.py
presentation/
  api/
    requests/
    responses/
    <feature>.py
  depends/
    repositories.py
    use_cases.py
```

Если чтение требует внешнего источника или другого модуля, добавляй port/adapters так же, как для write-сценария.

## Что считать хорошим признаком в новом коде

Новый код вписывается в проект, если:

- по структуре сразу понятно, в каком слое он находится;
- route можно прочитать за минуту;
- use case выражает сценарий, а не детали SQLAlchemy;
- сущности содержат понятные бизнес-методы;
- межмодульная связь идет через port/adapter;
- тесты покрывают happy path и ключевые ограничения;
- новый разработчик может найти фичу по имени модуля и сценария.

## Что считать тревожным признаком

Стоит остановиться и пересмотреть решение, если:

- route начал содержать бизнес-ветвления;
- application начал импортировать `fastapi`;
- domain начал импортировать SQLAlchemy;
- shared начал обрастать tenant/user-логикой;
- новый модуль зависит от чужих persistence-моделей;
- один repository содержит и query logic, и бизнес-валидацию, и транзакции;
- для понимания сценария нужно читать пять unrelated файлов из разных модулей без явного контракта.

## Итоговый ориентир

Если коротко, правильный способ писать код в этом проекте такой:

1. начни с owning module;
2. оформи бизнес-правила в `domain`;
3. собери сценарий в `application`;
4. реализуй БД и внешние интеграции в `infrastructure`;
5. подключи HTTP и DI в `presentation`;
6. оставь `shared` только для технической общей инфраструктуры;
7. закрепи поведение тестами.

Если сомневаешься, смотри на уже реализованные потоки как на эталон:

- create tenant flow в `tenancy`;
- request/confirm/logout OTP flow в `identity`;
- tenant resolve/request context flow в `tenancy`.
