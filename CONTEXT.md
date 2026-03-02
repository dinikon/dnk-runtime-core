# CONTEXT

## Назначение проекта

`dnk-runtime-core` — backend-сервис на `FastAPI` + `SQLAlchemy AsyncIO`.

Сейчас в проекте реализован один полноценный бизнес-сценарий:

- `POST /api/admin/create-tenant`

Сценарий создает в рамках одного запроса:

1. `Tenant`
2. первого `User` внутри tenant
3. `UserEmail` как primary email пользователя
4. `TenantDomain` как primary domain tenant

Текущая архитектура уже разложена по слоям и должна дальше расширяться в том же стиле.

---

## Технологический стек

- Python `>=3.12`
- FastAPI
- SQLAlchemy `asyncio`
- asyncpg
- Pydantic / pydantic-settings
- uuid6
- aiosqlite для локальной разработки и тестов
- unittest как текущий test runner

Основные зависимости описаны в [pyproject.toml](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/pyproject.toml).

---

## Точка входа

- Приложение создается в [src/app_factory.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/app_factory.py)
- Экспорт `app` находится в [src/app.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/app.py)
- Класс приложения: [src/dnk_app.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/dnk_app.py)

Текущий `lifespan` делает:

1. кладет `session_factory` в `app.state.db`
2. вызывает `create_all()`
3. при остановке делает `dispose()`

Это важно для dependency graph: `UoW` и репозитории получают одну и ту же session factory через `request.app.state.db`.

---

## Структура проекта

Актуальная рабочая структура:

```text
src/
  app.py
  app_factory.py
  dnk_app.py
  application/
    admin_tenants/
      dto.py
      ports/
        repositories.py
      services/
        tenant_service.py
        user_service.py
        tenant_domain_service.py
      use_cases/
        create_tenant.py
  common/
    uow.py
    db/
      base.py
      helper.py
      types/
        string_uuid.py
        long_text.py
  config/
    app_config.py
    infrastructure/__init__.py
  domain/
    common/
      errors.py
    tenancy/
      entities.py
    users/
      entities.py
    value_object/
      *.py
  infrastructure/
    admin_tenants/
      repositories.py
    persistence/
      tenant.py
      user.py
      user_email.py
      tenant_domain.py
  presentation/
    api/
      admin_tenants.py
      router.py
    depends/
      uow.py
      repositories.py
      services.py
      use_cases.py
test/
  test_admin_create_tenant_endpoint.py
  test_user_service.py
```

---

## Слои и их ответственность

### 1. Presentation layer

Файлы:

- [src/presentation/api/admin_tenants.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/api/admin_tenants.py)
- [src/presentation/api/router.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/api/router.py)
- [src/presentation/depends/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends)

Что делает:

- объявляет HTTP endpoint
- описывает request/response schema
- маппит request в application DTO
- получает use case через `Depends`
- конвертирует доменные ошибки в HTTP-ответ

Чего не делает:

- не создает `UnitOfWork` руками
- не создает репозитории руками
- не работает с SQLAlchemy session напрямую
- не содержит бизнес-логику

### 2. Application layer

Файлы:

- [src/application/admin_tenants/dto.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/application/admin_tenants/dto.py)
- [src/application/admin_tenants/use_cases/create_tenant.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/application/admin_tenants/use_cases/create_tenant.py)
- [src/application/admin_tenants/services/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/application/admin_tenants/services)
- [src/application/admin_tenants/ports/repositories.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/application/admin_tenants/ports/repositories.py)

Что делает:

- orchestrates use cases
- описывает DTO
- задает контракты репозиториев
- держит прикладные сервисы

Чего не делает:

- не знает про FastAPI
- не знает про Pydantic
- не знает про ORM-детали
- не открывает соединения сам

### 3. Domain layer

Файлы:

- [src/domain/tenancy/entities.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/tenancy/entities.py)
- [src/domain/users/entities.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/users/entities.py)
- [src/domain/common/errors.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/common/errors.py)
- [src/domain/value_object/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/value_object)

Что делает:

- хранит чистые доменные сущности
- валидирует инварианты на уровне сущностей
- хранит доменные ошибки
- хранит value objects / enum’ы

Чего не делает:

- не использует SQLAlchemy
- не использует FastAPI
- не знает о DI

### 4. Infrastructure layer

Файлы:

- [src/infrastructure/persistence/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/persistence)
- [src/infrastructure/admin_tenants/repositories.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/admin_tenants/repositories.py)

Что делает:

- ORM-модели
- SQLAlchemy repository implementation
- mapping domain ↔ DB model

---

## Как сейчас проходит запрос

Для `POST /api/admin/create-tenant` цепочка такая:

1. HTTP приходит в `presentation/api/admin_tenants.py`
2. Pydantic schema конвертируется в `CreateTenantCommandDTO`
3. контроллер получает `CreateTenantUseCaseDep`
4. dependency graph собирает:
   - `UoW`
   - repositories
   - services
   - use case
5. use case вызывает сервисы в порядке:
   - `TenantService`
   - `UserService`
   - `TenantDomainService`
6. сервисы вызывают repository implementation
7. repositories делают `flush()`, но не делают `commit()`
8. use case делает `commit()` в конце сценария
9. при исключении выполняется `rollback()`

Ключевая идея: один HTTP request должен использовать один `UoW` и одну SQLAlchemy session.

---

## Текущая бизнес-логика create-tenant

### Вход

Метод принимает:

```json
{
  "tenant": {
    "name": "dnk-003.dniko.net"
  },
  "tenant_domain": {
    "host": "dnk-003.dniko.net"
  },
  "user": {
    "last_name": "Doe",
    "first_name": "John"
  },
  "user_email": {
    "email": "john@example.com"
  }
}
```

### Выход

Метод возвращает:

- `tenant_id`
- `user_id`
- `user_email_id`
- `tenant_domain_id`
- `tenant_status`
- `user_status`
- `tenant_domain_host`

### Актуальные правила

На момент написания документа действуют такие правила:

- `tenant.name` должен быть уникален глобально
- `tenant_domain.host` должен быть уникален глобально
- `user_email.email` должен быть уникален только внутри конкретного tenant
- `user_email.email` проверяется только среди `is_deleted = false`
- одинаковый email в разных tenant разрешен
- primary email пользователя создается внутри агрегата `User`

### Нормализация значений

- `tenant.name`: `.strip()`
- `tenant_domain.host`: `.strip().lower()`
- `user.first_name`: `.strip()`
- `user.last_name`: `.strip()`
- `user_email.email`: `.strip().lower()`

---

## Domain model

### Tenant

Находится в [src/domain/tenancy/entities.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/tenancy/entities.py).

Фабрика:

```python
tenant = Tenant.create(name="Acme")
```

Поведение:

- валидирует непустое имя
- создает `uuid7`
- выставляет `status="active"`

### User и UserEmail

Находятся в [src/domain/users/entities.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/users/entities.py).

Пример:

```python
user = User.create_tenant_admin(
    tenant_id=tenant.id,
    first_name="John",
    last_name="Doe",
)
user.add_email("john@example.com", is_primary=True)
```

Правила:

- пользователь создается как активный
- email добавляется как дочерняя сущность пользователя
- второй primary email запрещен

### TenantDomain

Находится в [src/domain/tenancy/entities.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/tenancy/entities.py).

Пример:

```python
domain = TenantDomain.create_primary(
    tenant_id=tenant.id,
    host="acme.example.com",
)
```

По умолчанию:

- `service_type = console`
- `kind = default`
- `status = active`
- `verification_status = verified`
- `tls_mode = managed`
- `is_primary = True`

---

## Ошибки

Доменные ошибки находятся в [src/domain/common/errors.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/common/errors.py).

Используются сейчас:

- `ValidationError`
- `TenantNameAlreadyExistsError`
- `UserEmailAlreadyExistsError`
- `TenantDomainHostAlreadyExistsError`

Роутер переводит их в:

- `409 Conflict` для конфликтов уникальности
- `422 Unprocessable Entity` для ошибок валидации домена

---

## Use case и транзакции

Общий `UnitOfWork` находится в [src/common/uow.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/common/uow.py).

Dependency для него находится в [src/presentation/depends/uow.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends/uow.py).

Правило проекта:

- `UoW` общий для проекта
- `UseCase` владеет сценарием целиком
- `services` не коммитят
- `repositories` не коммитят

Текущая реализация сценария:

```python
try:
    tenant = await self._tenant_service.create_tenant(dto.tenant_name)
    user = await self._user_service.create_tenant_admin(...)
    tenant_domain = await self._tenant_domain_service.create_primary_domain(...)
    await self._uow.commit()
except Exception:
    await self._uow.rollback()
    raise
```

Важно:

- repository может делать `flush()`
- `flush()` не равен `commit()`
- бизнес-смысл транзакции остается один на весь сценарий

---

## Dependency injection

Dependency graph разбит по типам:

- [src/presentation/depends/uow.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends/uow.py)
- [src/presentation/depends/repositories.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends/repositories.py)
- [src/presentation/depends/services.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends/services.py)
- [src/presentation/depends/use_cases.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/presentation/depends/use_cases.py)

Правило:

- каждый файл dependencies отвечает только за один тип зависимостей

Пример:

```python
def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    return SqlAlchemyUserRepository(uow.session)
```

---

## Persistence и ORM

ORM-модели находятся в:

- [src/infrastructure/persistence/tenant.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/persistence/tenant.py)
- [src/infrastructure/persistence/user.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/persistence/user.py)
- [src/infrastructure/persistence/user_email.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/persistence/user_email.py)
- [src/infrastructure/persistence/tenant_domain.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/persistence/tenant_domain.py)

Текущее правило именования:

- ORM-модели называются `*Model`
- доменные сущности называются `Tenant`, `User`, `UserEmail`, `TenantDomain`

### Кастомные DB types

Сейчас они вынесены в:

- [src/common/db/types/string_uuid.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/common/db/types/string_uuid.py)
- [src/common/db/types/long_text.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/common/db/types/long_text.py)

`StringUUID` нужен для совместимого хранения UUID:

- PostgreSQL: native UUID
- SQLite: `CHAR(36)`

### Регистрация ORM в metadata

В [src/common/db/helper.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/common/db/helper.py) есть важный side-effect import:

```python
import src.infrastructure.persistence  # noqa: F401
```

Он нужен, чтобы SQLAlchemy увидел все ORM-классы и добавил их в `Base.metadata` до `create_all()`.

Не удалять этот импорт, если не заменили его на эквивалентную регистрацию моделей.

---

## SQLAlchemy repositories

Реализация портов находится в [src/infrastructure/admin_tenants/repositories.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/infrastructure/admin_tenants/repositories.py).

Правила репозиториев:

- работают только через переданный `AsyncSession`
- не делают `commit()`
- маппят domain ↔ ORM
- проверяют existence запросами вида `select(...).limit(1)`

Пример проверки email в tenant:

```python
select(UserEmailModel.id)
    .join(UserModel, UserModel.id == UserEmailModel.user_id)
    .where(UserModel.tenant_id == str(tenant_id))
    .where(UserEmailModel.email == email)
    .where(UserEmailModel.is_deleted.is_(False))
    .limit(1)
```

---

## Конфигурация

Конфигурация собирается через:

- [src/config/app_config.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/config/app_config.py)
- [src/config/infrastructure/__init__.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/config/infrastructure/__init__.py)

Источники:

1. init values
2. env
3. dotenv (`.env`)
4. file secrets
5. `pyproject.toml`

Шаблоны:

- [temaplate.dev.env](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/temaplate.dev.env)
- [temaplate.env](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/temaplate.env)

Локальная разработка по умолчанию ориентирована на SQLite.

---

## Тесты

Текущие тесты находятся в:

- [test/test_admin_create_tenant_endpoint.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_admin_create_tenant_endpoint.py)
- [test/test_user_service.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_user_service.py)

Используется `unittest`, не `pytest`.

Что проверяется:

- happy-path create-tenant
- rollback целого сценария при конфликте на последнем шаге
- одинаковый email в разных tenant разрешен
- одинаковый email в одном tenant запрещен
- удаленный email не участвует в проверке уникальности

Запуск:

```bash
./.venv/bin/python -m unittest discover -s test -v
```

Форматирование:

```bash
./.venv/bin/python -m black src test
```

---

## Правила продолжения разработки

### 1. Добавление нового HTTP-сценария

Для нового сценария создавай тот же набор слоев:

1. `presentation/api/<feature>.py`
2. `application/<feature>/dto.py`
3. `application/<feature>/ports/*.py`
4. `application/<feature>/services/*.py`
5. `application/<feature>/use_cases/*.py`
6. `infrastructure/<feature>/repositories.py`
7. DI в `presentation/depends/`
8. router registration в `presentation/api/router.py`
9. тесты

### 2. Не смешивать слои

- не тянуть Pydantic в application/domain
- не тянуть SQLAlchemy models в domain
- не писать бизнес-логику в роутере
- не делать `commit()` в сервисах и репозиториях

### 3. Именование

- domain: `Tenant`, `User`, `TenantDomain`
- ORM: `TenantModel`, `UserModel`, `TenantDomainModel`, `UserEmailModel`
- DI aliases: `*Dep`
- repository implementation: `SqlAlchemy*Repository`

### 4. Работа с UUID

- в домене использовать `UUID`
- в ORM использовать `StringUUID`
- при raw SQLAlchemy query фильтрах ориентироваться на текущую модель поля
- в проекте уже есть helper `_to_uuid(...)` для чтения ORM результатов

### 5. Нормализация входных данных

Для новых сценариев нормализовать вход до создания сущности:

- строковые имена через `.strip()`
- email/host через `.strip().lower()`, если это идентификатор без кейс-сенситивности

### 6. DI-файлы

Не складывать все dependencies в один файл.

Текущее правило:

- `uow.py` — только UoW
- `repositories.py` — только repository dependencies
- `services.py` — только service dependencies
- `use_cases.py` — только use case dependencies

### 7. Роутеры

Каждый feature router живет отдельно, но подключается в общий router aggregator:

- feature route: `presentation/api/admin_tenants.py`
- общий API router: `presentation/api/router.py`

### 8. Тесты при изменениях

При изменении сценария:

- добавить/обновить endpoint test
- добавить/обновить service или repository test
- проверять rollback отдельно

---

## Пример добавления нового use case

Минимальная схема:

```python
# application/foo/dto.py
@dataclass(frozen=True, slots=True)
class FooCommandDTO:
    name: str
```

```python
# application/foo/use_cases/create_foo.py
class CreateFooUseCase:
    def __init__(self, uow: UnitOfWorkProtocol, foo_service: FooServiceProtocol):
        self._uow = uow
        self._foo_service = foo_service

    async def execute(self, dto: FooCommandDTO) -> FooResultDTO:
        try:
            foo = await self._foo_service.create(dto.name)
            await self._uow.commit()
        except Exception:
            await self._uow.rollback()
            raise
        return FooResultDTO(foo_id=foo.id)
```

```python
# presentation/depends/use_cases.py
def get_create_foo_use_case(
    uow: UoWDep,
    foo_service: FooServiceDep,
) -> CreateFooUseCase:
    return CreateFooUseCase(uow=uow, foo_service=foo_service)
```

```python
# presentation/api/foo.py
@router.post("/api/foo")
async def create_foo(
    payload: FooRequestSchema,
    use_case: CreateFooUseCaseDep,
) -> FooResponseSchema:
    result = await use_case.execute(FooCommandDTO(name=payload.name))
    return FooResponseSchema(foo_id=result.foo_id)
```

---

## Известные особенности и замечания

### 1. В проекте есть legacy-папка `src/domain/entity`

Сейчас активная архитектура использует:

- [src/domain/tenancy/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/tenancy)
- [src/domain/users/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/domain/users)

Папка `src/domain/entity` выглядит как старый слой и в текущем сценарии не используется. Для новой разработки ориентироваться на новые каталоги `domain/tenancy` и `domain/users`.

### 2. В проекте нет pytest-инфраструктуры

На данный момент стандартный и подтвержденный путь — `unittest`.

### 3. Таблицы создаются автоматически через `create_all()`

Это удобно для локальной разработки и тестов, но для production-сценариев обычно потребуется миграционная стратегия.

---

## Краткий чеклист перед новой задачей

1. Определи, к какому feature относится задача.
2. Проверь, есть ли уже domain entity/value objects для этого feature.
3. Добавь DTO и use case в application.
4. Добавь ports и infrastructure repository implementation.
5. Собери dependencies в `presentation/depends/*`.
6. Добавь feature router и подключи его в `presentation/api/router.py`.
7. Напиши минимум один happy-path test и один negative-path test.
8. Запусти:

```bash
./.venv/bin/python -m unittest discover -s test -v
```

---

## Основной принцип проекта

Проект развивается как layered backend с явным разделением ответственности:

- HTTP отдельно
- orchestration отдельно
- domain отдельно
- SQLAlchemy отдельно
- DI отдельно

Если новая логика начинает тянуть SQLAlchemy в controller, Pydantic в domain или `commit()` в repository/service — это сигнал, что структура нарушается.
