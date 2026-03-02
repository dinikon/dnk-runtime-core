## Цель

Реализовать метод:

* **`POST /api/admin/create-tenant`**

Метод должен в рамках **одной транзакции**:

1. создать `Tenant`;
2. создать первого `User` внутри tenant;
3. создать `UserEmail` как primary email пользователя;
4. создать `TenantDomain` как primary domain tenant;
5. если любой шаг падает — откатить всё.

---

# Что принимает метод

## HTTP payload

Метод принимает:

* `tenant.name`
* `tenant_domain.host`
* `user.last_name`
* `user.first_name`
* `user_emails.email`

---

## Pydantic Request Schema

Нужно создать входную HTTP-схему:

* `AdminCreateTenantRequestSchema`

Лучше в виде вложенной структуры:

* `TenantCreatePartSchema`
* `TenantDomainCreatePartSchema`
* `UserCreatePartSchema`
* `UserEmailCreatePartSchema`

Пример структуры:

```python
class TenantCreatePartSchema(BaseModel):
    name: str


class TenantDomainCreatePartSchema(BaseModel):
    host: str


class UserCreatePartSchema(BaseModel):
    last_name: str
    first_name: str


class UserEmailCreatePartSchema(BaseModel):
    email: EmailStr


class AdminCreateTenantRequestSchema(BaseModel):
    tenant: TenantCreatePartSchema
    tenant_domain: TenantDomainCreatePartSchema
    user: UserCreatePartSchema
    user_email: UserEmailCreatePartSchema
```

---

## Pydantic Response Schema

Нужно создать выходную HTTP-схему:

* `AdminCreateTenantResponseSchema`

Поля:

* `tenant_id`
* `user_id`
* `user_email_id`
* `tenant_domain_id`
* `tenant_status`
* `user_status`
* `tenant_domain_host`

---

# Слои и ответственность

---

## 1. Controller layer

## Что делает controller

Controller отвечает только за:

* HTTP endpoint
* Pydantic schema
* получение зависимостей через `Depends`
* преобразование request → application DTO
* вызов use case
* преобразование ошибок в HTTP response

## Чего controller не делает

Controller не должен:

* создавать `UnitOfWork` руками
* создавать repository/service руками
* открывать транзакцию
* содержать бизнес-логику
* работать с SQLAlchemy session напрямую

---

## Что нужно создать в controller

Файл:

* `src/presentation/api/admin_tenants.py`

Создать:

* `AdminCreateTenantRequestSchema`
* `AdminCreateTenantResponseSchema`
* endpoint `create_tenant()`

Сигнатура будет примерно такой:

```python
@router.post("/api/admin/create-tenant")
async def create_tenant(
    payload: AdminCreateTenantRequestSchema,
    use_case: CreateTenantUseCaseDep,
) -> AdminCreateTenantResponseSchema:
    ...
```

---

## 2. Application layer

Это слой сценария.

---

### 2.1. DTO

Нужно создать application DTO, чтобы Pydantic не уходил внутрь.

Файл:

* `src/application/admin_tenants/dto.py`

Создать:

* `CreateTenantCommandDTO`
* `CreateTenantResultDTO`

### `CreateTenantCommandDTO`

```python
@dataclass(frozen=True, slots=True)
class CreateTenantCommandDTO:
    tenant_name: str
    tenant_domain_host: str
    user_last_name: str
    user_first_name: str
    user_email: str
```

### `CreateTenantResultDTO`

```python
@dataclass(frozen=True, slots=True)
class CreateTenantResultDTO:
    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str
```

---

### 2.2. UseCase

Файл:

* `src/application/admin_tenants/use_cases/create_tenant.py`

Создать:

* `CreateTenantUseCase`

Метод:

* `execute(dto: CreateTenantCommandDTO) -> CreateTenantResultDTO`

---

## Роль UseCase

UseCase — это **оркестратор сценария**.

Он:

1. принимает DTO;
2. работает внутри одного `uow`;
3. вызывает сервисы в правильном порядке;
4. делает `commit`;
5. возвращает result DTO.

## Важно

UseCase не должен:

* знать про FastAPI
* знать про Pydantic
* создавать репозитории
* создавать session

---

## 3. Service layer

Сервисный слой — это **не слой DI** и **не слой транзакции**.

Он делает локальную бизнес-операцию в своей зоне.

---

### 3.1. TenantService

Файл:

* `src/application/admin_tenants/services/tenant_service.py`

Создать:

* `TenantServiceProtocol`
* `TenantService`

Метод:

* `create_tenant(name: str) -> Tenant`

### Ответственность

* проверить уникальность tenant по `name`
* создать domain entity `Tenant`
* сохранить через `TenantRepository`

---

### 3.2. UserService

Файл:

* `src/application/admin_tenants/services/user_service.py`

Создать:

* `UserServiceProtocol`
* `UserService`

Метод:

* `create_tenant_admin(tenant_id: UUID, first_name: str, last_name: str, email: str) -> User`

### Ответственность

* проверить уникальность email
* создать первого пользователя tenant
* создать primary email пользователя
* сохранить через `UserRepository`

---

### Важное DDD-решение

Для этого сценария **`UserEmail` лучше считать частью агрегата `User`**.

То есть:

* `User` — aggregate root
* `UserEmail` — дочерняя сущность внутри `User`

Тогда:

* отдельный `UserEmailRepository` для сценария `create-tenant` не нужен;
* `UserRepository` сохраняет и `User`, и его `emails`.

Даже если в БД это отдельная таблица — в доменной модели это всё равно может быть один aggregate.

---

### 3.3. TenantDomainService

Файл:

* `src/application/admin_tenants/services/tenant_domain_service.py`

Создать:

* `TenantDomainServiceProtocol`
* `TenantDomainService`

Метод:

* `create_primary_domain(tenant_id: UUID, host: str) -> TenantDomain`

### Ответственность

* проверить уникальность `host`
* создать primary domain
* сохранить через `TenantDomainRepository`

---

## Главное правило сервиса

Сервис:

* может вызывать repository;
* может создавать/изменять domain entity;
* **не делает commit**;
* **не работает с HTTP**;
* **не использует Depends**.

---

## 4. Domain layer

Тут живут чистые сущности и бизнес-правила.

---

### Что создать

Файлы:

* `src/domain/tenancy/entities.py`
* `src/domain/users/entities.py`
* `src/domain/common/errors.py`

---

### Domain entities

Создать чистые доменные сущности:

* `Tenant`
* `TenantDomain`
* `User`
* `UserEmail`

Это должны быть:

* dataclass / rich entities
* без SQLAlchemy
* без `Mapped`, `mapped_column`, `Base`

---

### Методы домена

#### `Tenant`

* `Tenant.create(name: str) -> Tenant`

#### `User`

* `User.create_tenant_admin(...) -> User`
* `User.add_email(...) -> UserEmail`

#### `TenantDomain`

* `TenantDomain.create_primary(...) -> TenantDomain`

---

### Domain errors

Создать ошибки:

* `ValidationError`
* `TenantNameAlreadyExistsError`
* `UserEmailAlreadyExistsError`
* `TenantDomainHostAlreadyExistsError`

---

## 5. Repository layer (ports)

Это контракты application/domain слоя.

Файл:

* `src/application/admin_tenants/ports/repositories.py`

Создать:

* `TenantRepositoryProtocol`
* `UserRepositoryProtocol`
* `TenantDomainRepositoryProtocol`

---

### `TenantRepositoryProtocol`

Методы:

* `add(tenant: Tenant) -> None`
* `get_by_id(tenant_id: UUID) -> Tenant | None`
* `get_by_name(name: str) -> Tenant | None`
* `exists_by_name(name: str) -> bool`

---

### `UserRepositoryProtocol`

Методы:

* `add(user: User) -> None`
* `get_by_id(user_id: UUID) -> User | None`
* `exists_by_email(email: str) -> bool`

---

### `TenantDomainRepositoryProtocol`

Методы:

* `add(domain: TenantDomain) -> None`
* `get_by_id(domain_id: UUID) -> TenantDomain | None`
* `get_by_host(host: str) -> TenantDomain | None`
* `exists_by_host(host: str) -> bool`

---

## 6. Unit of Work

С учетом твоего паттерна UoW должен использоваться как **транзакционная оболочка**, а репозитории — собираться отдельно через `depends.py` из `uow.session`.

---

### Что создать

Файл:

* `src/application/admin_tenants/ports/uow.py`

Создать:

* `UnitOfWorkProtocol`

### Какие методы должны быть

* `__aenter__`
* `__aexit__`
* `commit()`
* `rollback()`

### Что ещё должно быть в протоколе

Так как репозитории создаются из `uow.session`, у `UnitOfWorkProtocol` должен быть:

* `session: AsyncSession`

Минимально:

```python
class UnitOfWorkProtocol(Protocol):
    session: AsyncSession

    async def __aenter__(self) -> "UnitOfWorkProtocol": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

---

## Важное правило

### `commit()` делает только UseCase

Потому что именно UseCase владеет всем сценарием целиком.

* controller не коммитит
* service не коммитит
* repository не коммитит

---

## 7. Infrastructure layer

Это SQLAlchemy и PostgreSQL.

---

### Что у тебя уже есть

Сейчас у тебя есть ORM-модели:

* `Tenant`
* `User`
* `UserEmail`

Их лучше переименовать в инфраструктурном слое, чтобы не путать с доменом:

* `TenantModel`
* `UserModel`
* `UserEmailModel`

---

### Что ещё нужно добавить

Нужна ORM-модель:

* `TenantDomainModel`

Минимальные поля:

* `id`
* `tenant_id`
* `host`
* `is_primary`
* `status`
* `created_at`
* `updated_at`

---

### Что создать в infrastructure

Файлы:

* `src/infrastructure/admin_tenants/repositories.py`
* `src/infrastructure/admin_tenants/uow.py`

Создать:

* `SqlAlchemyTenantRepository`
* `SqlAlchemyUserRepository`
* `SqlAlchemyTenantDomainRepository`
* `UnitOfWork` (конкретная реализация `UnitOfWorkProtocol`)

---

## Что делает реализация UoW

Конкретный `UnitOfWork`:

* принимает `async_sessionmaker[AsyncSession]`
* открывает session в `__aenter__`
* кладёт session в `self.session`
* делает `commit/rollback`
* закрывает session в `__aexit__`

Именно такой UoW подходит под твой `get_uow()`.

---

# Сборка зависимостей через depends.py

Вот это теперь главный внешний composition root.

Файл:

* `src/presentation/depends.py`

---

## Что нужно создать в depends.py

### 1. `get_uow`

Создать UoW через `Request.app.state`:

```python
async def get_uow(request: Request) -> AsyncGenerator[UnitOfWorkProtocol, None]:
    session_factory = getattr(request.app.state, "db", db_helper.session_factory)
    typed_session_factory: async_sessionmaker[AsyncSession] = session_factory
    async with UnitOfWork(typed_session_factory) as uow:
        yield uow
```

Тип-алиас:

```python
UoWDep = Annotated[UnitOfWorkProtocol, Depends(get_uow)]
```

---

### 2. Repository dependencies

Поскольку репозитории строятся от `uow.session`, нужно создать:

* `get_tenants_repository(uow: UoWDep) -> TenantRepositoryProtocol`
* `get_users_repository(uow: UoWDep) -> UserRepositoryProtocol`
* `get_tenant_domains_repository(uow: UoWDep) -> TenantDomainRepositoryProtocol`

Пример:

```python
def get_tenants_repository(uow: UoWDep) -> TenantRepositoryProtocol:
    return SqlAlchemyTenantRepository(uow.session)
```

```python
def get_users_repository(uow: UoWDep) -> UserRepositoryProtocol:
    return SqlAlchemyUserRepository(uow.session)
```

```python
def get_tenant_domains_repository(uow: UoWDep) -> TenantDomainRepositoryProtocol:
    return SqlAlchemyTenantDomainRepository(uow.session)
```

Тип-алиасы:

* `TenantsRepositoryDep`
* `UsersRepositoryDep`
* `TenantDomainsRepositoryDep`

---

### 3. Service dependencies

Сервисы создаются из репозиториев:

* `get_tenant_service(tenants_repository: TenantsRepositoryDep) -> TenantServiceProtocol`
* `get_user_service(users_repository: UsersRepositoryDep) -> UserServiceProtocol`
* `get_tenant_domain_service(tenant_domains_repository: TenantDomainsRepositoryDep) -> TenantDomainServiceProtocol`

Тип-алиасы:

* `TenantServiceDep`
* `UserServiceDep`
* `TenantDomainServiceDep`

---

### 4. UseCase dependency

UseCase должен получить:

* `uow`
* `tenant_service`
* `user_service`
* `tenant_domain_service`

Создать:

* `get_create_tenant_use_case(...) -> CreateTenantUseCase`

И type alias:

* `CreateTenantUseCaseDep`

---

## Почему это работает корректно

Потому что в рамках одного HTTP-запроса FastAPI кеширует dependency graph.

Значит:

* `get_uow()` вызовется один раз;
* один и тот же `uow` попадёт:

  * в repository factories,
  * и в use case;
* все репозитории будут работать на **одной session**;
* `use case` закоммитит ровно ту транзакцию, внутри которой работали сервисы.

Это как раз то, что тебе нужно.

---

# Обновлённый flow вызовов

Теперь уже в точности под твой паттерн.

---

## Шаг 1. HTTP request → Controller

Controller получает `AdminCreateTenantRequestSchema`.

---

## Шаг 2. Controller → DTO

Controller собирает:

* `CreateTenantCommandDTO`

---

## Шаг 3. Controller → UseCase

Controller вызывает:

* `CreateTenantUseCase.execute(dto)`

UseCase уже приходит готовым через `depends.py`.

---

## Шаг 4. UseCase открывает transaction scope

`uow` уже создан dependency-фабрикой `get_uow()`.

UseCase работает с ним как с единым transaction scope и в конце происходит автокомит:

```
async def get_uow(request: Request) -> AsyncGenerator[UnitOfWorkProtocol, None]:
    session_factory = getattr(request.app.state, "db", db_helper.session_factory)
    typed_session_factory: async_sessionmaker[AsyncSession] = session_factory
    async with UnitOfWork(typed_session_factory) as uow:
        yield uow

UoWDep = Annotated[UnitOfWorkProtocol, Depends(get_uow)]

```

Если исключение — UoW делает rollback в `__aexit__`.

---

## Шаг 5. UseCase вызывает сервисы

Порядок:

1. `tenant_service.create_tenant(...)`
2. `user_service.create_tenant_admin(...)`
3. `tenant_domain_service.create_primary_domain(...)`

---

## Шаг 6. Service вызывает Repository

Каждый сервис вызывает только свой репозиторий:

* `TenantService` → `TenantRepository`
* `UserService` → `UserRepository`
* `TenantDomainService` → `TenantDomainRepository`

Репозитории работают на `uow.session`, переданной через `depends.py`.

---

## Шаг 7. Repository работает с ORM

Репозиторий:

* маппит domain ↔ ORM
* сохраняет данные в PostgreSQL
* не коммитит

---

## Шаг 8. UseCase делает commit

Потом UseCase собирает:

* `CreateTenantResultDTO`

И возвращает его в controller.

---

## Шаг 9. Controller возвращает HTTP response

Controller конвертирует `CreateTenantResultDTO` в:

* `AdminCreateTenantResponseSchema`

---

# Декларативный список: что именно создать

---

## `src/presentation/api/admin_tenants.py`

Создать:

* `TenantCreatePartSchema`
* `TenantDomainCreatePartSchema`
* `UserCreatePartSchema`
* `UserEmailCreatePartSchema`
* `AdminCreateTenantRequestSchema`
* `AdminCreateTenantResponseSchema`
* endpoint `create_tenant()`

---

## `src/presentation/depends.py`

Создать:

* `get_uow`

* `UoWDep`

* `get_tenants_repository`

* `TenantsRepositoryDep`

* `get_users_repository`

* `UsersRepositoryDep`

* `get_tenant_domains_repository`

* `TenantDomainsRepositoryDep`

* `get_tenant_service`

* `TenantServiceDep`

* `get_user_service`

* `UserServiceDep`

* `get_tenant_domain_service`

* `TenantDomainServiceDep`

* `get_create_tenant_use_case`

* `CreateTenantUseCaseDep`

---

## `src/application/admin_tenants/dto.py`

Создать:

* `CreateTenantCommandDTO`
* `CreateTenantResultDTO`

---

## `src/application/admin_tenants/use_cases/create_tenant.py`

Создать:

* `CreateTenantUseCase`

Метод:

* `execute(dto: CreateTenantCommandDTO) -> CreateTenantResultDTO`

---

## `src/application/admin_tenants/services/tenant_service.py`

Создать:

* `TenantServiceProtocol`
* `TenantService`

Метод:

* `create_tenant(name: str) -> Tenant`

---

## `src/application/admin_tenants/services/user_service.py`

Создать:

* `UserServiceProtocol`
* `UserService`

Метод:

* `create_tenant_admin(tenant_id: UUID, first_name: str, last_name: str, email: str) -> User`

---

## `src/application/admin_tenants/services/tenant_domain_service.py`

Создать:

* `TenantDomainServiceProtocol`
* `TenantDomainService`

Метод:

* `create_primary_domain(tenant_id: UUID, host: str) -> TenantDomain`

---

## `src/application/admin_tenants/ports/repositories.py`

Создать:

* `TenantRepositoryProtocol`
* `UserRepositoryProtocol`
* `TenantDomainRepositoryProtocol`

---

## `src/application/admin_tenants/ports/uow.py`

Создать:

* `UnitOfWorkProtocol`

Свойства:

* `session`

Методы:

* `__aenter__`
* `__aexit__`
* `commit`
* `rollback`

---

## `src/domain/tenancy/entities.py`

Создать:

* `Tenant`
* `TenantDomain`

Методы:

* `Tenant.create(...)`
* `TenantDomain.create_primary(...)`

---

## `src/domain/users/entities.py`

Создать:

* `User`
* `UserEmail`

Методы:

* `User.create_tenant_admin(...)`
* `User.add_email(...)`

---

## `src/domain/common/errors.py`

Создать:

* `ValidationError`
* `TenantNameAlreadyExistsError`
* `UserEmailAlreadyExistsError`
* `TenantDomainHostAlreadyExistsError`

---

## `src/infrastructure/db/models.py`

Создать / перенести ORM-модели:

* `TenantModel`
* `UserModel`
* `UserEmailModel`
* `TenantDomainModel`

---

## `src/infrastructure/admin_tenants/repositories.py`

Создать:

* `SqlAlchemyTenantRepository`
* `SqlAlchemyUserRepository`
* `SqlAlchemyTenantDomainRepository`

---

## `src/infrastructure/admin_tenants/uow.py`

Создать:

* `UnitOfWork`

Он должен принимать `async_sessionmaker[AsyncSession]`.

---

# Итоговая архитектурная формула

С учетом твоего DI-паттерна правильная цепочка такая:

**Controller**
принимает `Pydantic Schema`

→ **Controller**
собирает `CreateTenantCommandDTO`

→ **UseCase**
получает `uow + services` через `depends.py`

→ **Services**
получают `repositories` через `depends.py`

→ **Repositories**
получают `uow.session`

→ **UoW**
держит одну транзакцию на весь сценарий

→ **UseCase**
делает `commit()`

Это чистая и практичная схема для FastAPI.