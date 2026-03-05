# Identity Module

## Ответственность

`src/modules/identity` — bounded context, который владеет:

- `User`
- `UserEmail`
- tenant-scoped проверкой email
- auth-flow по email OTP

## Структура

```text
identity/
  application/
    provisioning/
    auth/
  domain/
  infrastructure/
  presentation/
```

## Domain

Ключевые файлы:

- [`src/modules/identity/domain/entities.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/entities.py)
- [`src/modules/identity/domain/errors.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/errors.py)

Ключевые методы:

```python
User.create_tenant_admin(...)
User.add_email(...)
User.can_login() -> bool
User.get_primary_email(email: str) -> UserEmail | None
User.mark_email_verified(user_email_id: UUID) -> None

UserEmail.mark_verified() -> None
```

Бизнес-правила:

- email нормализуется как `strip().lower()`
- login идет только по primary email
- deleted email не участвует в login
- user должен быть в status `active`

## Application

### `provisioning`

Назначение:

- создание tenant admin пользователя для onboarding tenant

Сервис:

- [`UserService.create_tenant_admin(...)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/provisioning/services/user_service.py)

Контракт:

```python
async def create_tenant_admin(
    tenant_id: UUID,
    first_name: str,
    last_name: str,
    email: str,
) -> User
```

### `auth`

Назначение:

- email OTP login
- session creation
- logout
- current user profile read by session cookie

#### DTO

Файл:

- [`src/modules/identity/application/auth/dto.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/dto.py)

Основные DTO:

```python
RequestEmailOtpCommandDTO(host: str, email: str)
RequestEmailOtpResultDTO(token: str, expires_in: int)

ConfirmEmailOtpCommandDTO(host: str, email: str, token: str, code: str)
ConfirmEmailOtpResultDTO(ok: bool, user_id: UUID, tenant_id: UUID, session_token: str, expires_in: int)

LogoutCurrentSessionCommandDTO(host: str, session_token: str | None)
LogoutCurrentSessionResultDTO(ok: bool)

GetCurrentUserCommandDTO(host: str, session_token: str | None)
GetCurrentUserResultDTO(
    id: UUID,
    status: str,
    last_name: str,
    first_name: str,
    middle_name: str | None,
    avatar: str | None,
    interface_language: str,
    interface_theme: str | None,
    timezone: str,
    emails: list[GetCurrentUserEmailDTO],
)
```

#### Ports

Файлы:

- [`ports/repositories.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/ports/repositories.py)
- [`ports/tenant_context.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/ports/tenant_context.py)
- [`ports/token_store.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/ports/token_store.py)
- [`ports/email_sender.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/ports/email_sender.py)

Контракты:

```python
class AuthUserRepositoryPort(Protocol):
    async def get_by_id(user_id: UUID) -> User | None: ...
    async def get_by_tenant_and_primary_email(tenant_id: UUID, email: str) -> User | None: ...
    async def mark_email_verified(user_email_id: UUID) -> None: ...

class TenantContextReaderPort(Protocol):
    async def get_by_host(host: str) -> TenantRequestContext: ...

class OtpChallengeStorePort(Protocol):
    async def create_challenge(challenge: OtpChallenge, ttl_seconds: int) -> None: ...
    async def get_challenge(tenant_id: UUID, token: str) -> OtpChallenge | None: ...
    async def invalidate_challenge(tenant_id: UUID, token: str) -> None: ...

class SessionStorePort(Protocol):
    async def create_session(session: SessionRecord, ttl_seconds: int) -> None: ...
    async def get_session(tenant_id: UUID, token: str) -> SessionRecord | None: ...
    async def invalidate_session(tenant_id: UUID, token: str) -> None: ...

class EmailSenderPort(Protocol):
    async def send_login_code(email: str, code: str) -> None: ...
```

#### Services

Файлы:

- [`services/otp_service.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/services/otp_service.py)
- [`services/session_service.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/services/session_service.py)

Контракты:

```python
class OtpServiceProtocol(Protocol):
    def generate() -> GeneratedOtp
    def verify_code(*, code: str, code_hash: str) -> bool

class SessionServiceProtocol(Protocol):
    def generate(*, ttl_seconds: int) -> GeneratedSession
```

#### Use cases

- [`RequestEmailOtpUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/use_cases/request_email_otp.py)
- [`ConfirmEmailOtpUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/use_cases/confirm_email_otp.py)
- [`GetCurrentUserUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/use_cases/get_current_user.py)
- [`LogoutCurrentSessionUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/application/auth/use_cases/logout_current_session.py)

Контракт поведения:

- `request_otp`
  - получает tenant-context через `TenantContextReaderPort`
  - ищет user внутри tenant
  - создает OTP challenge
  - не возвращает code наружу
- `confirm_otp`
  - повторно валидирует tenant-context
  - проверяет token/code/email/host
  - создает session
  - инвалидирует OTP
  - помечает email verified
- `logout`
  - валидирует session в tenant-context
  - инвалидирует session
  - ведет себя идемпотентно при отсутствии session
- `current_user`
  - валидирует session cookie в tenant-context
  - проверяет соответствие `tenant/domain/host`
  - загружает пользователя по `user_id` из session
  - проверяет статус пользователя (`active`)
  - возвращает профиль и `emails` c фильтром `is_deleted = False`

## Infrastructure

Файлы:

- [`src/modules/identity/infrastructure/persistence/user.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/infrastructure/persistence/user.py)
- [`src/modules/identity/infrastructure/persistence/user_email.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/infrastructure/persistence/user_email.py)
- [`src/modules/identity/infrastructure/repositories.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/infrastructure/repositories.py)

Репозиторий:

- `SqlAlchemyUserRepository`

Поддерживаемые методы:

```python
async def add(user: User) -> None
async def get_by_id(user_id: UUID) -> User | None
async def get_by_tenant_and_primary_email(tenant_id: UUID, email: str) -> User | None
async def mark_email_verified(user_email_id: UUID) -> None
async def exists_by_tenant_and_email(tenant_id: UUID, email: str) -> bool
```

## Presentation

Роуты:

- [`POST /api/console/auth/request-otp`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/presentation/api/console_auth.py)
- [`POST /api/console/auth/confirm-otp`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/presentation/api/console_auth.py)
- [`GET /api/console/auth/me`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/presentation/api/console_auth.py)
- [`POST /api/console/auth/logout`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/identity/presentation/api/console_auth.py)

Схемы request/response вынесены в:

- `presentation/api/requests/*`
- `presentation/api/responses/*`

DI:

- repositories -> `presentation/depends/repositories.py`
- provisioning service -> `presentation/depends/services.py`
- auth adapters -> `presentation/depends/auth_repositories.py`
- auth services -> `presentation/depends/auth_services.py`
- auth use cases -> `presentation/depends/auth_use_cases.py`

## Важное ограничение модуля

`identity` не должен сам определять tenant по ORM tenancy. Для этого он использует `TenantContextReaderPort`, адаптер которого живет в presentation/depends и вызывает tenancy application use case.
