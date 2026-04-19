# CONTEXT

## Назначение проекта

`dnk-runtime-core` — backend-сервис на `FastAPI` + `SQLAlchemy AsyncIO`, построенный вокруг модульной структуры `src/modules`.

Сейчас в проекте реализованы несколько рабочих направлений:

1. `tenancy`
   - server-to-server создание tenant через `POST /api/admin/create-tenant`
   - resolve tenant по host через `GET /api/console/tenants/resolve`
2. `identity`
   - tenant-bound auth-flow по email OTP:
     - `POST /api/console/auth/request-otp`
     - `POST /api/console/auth/confirm-otp`
     - `GET /api/console/auth/me`
     - `PATCH /api/console/auth/me`
     - `POST /api/console/auth/logout`
3. `schema_registry`
    - bootstrap tenant runtime schema из seed
    - diff tenant runtime schema через `dnk-manage schema-registry diff`
4. `runtime_data`
    - tenant-scoped доступ к runtime-таблицам и данным
5. `crm`
    - CRUD операций над `contact` поверх runtime data

Ключевая бизнес-идея приложения:

- tenant всегда определяется по `host`;
- `tenancy` владеет `Tenant` и `TenantDomain`;
- `identity` владеет `User` и `UserEmail`;
- `shared` хранит только технические cross-module механизмы;
- один HTTP request должен проходить через один `UoW` и одну SQLAlchemy session.

---

## Технологический стек

- Python `>=3.12`
- FastAPI
- SQLAlchemy `asyncio`
- asyncpg
- pydantic / pydantic-settings
- uuid6
- Redis как целевое хранилище token/session state
- PostgreSQL (asyncpg) как единственный SQL backend
- unittest как текущий test runner

Основные зависимости описаны в [pyproject.toml](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/pyproject.toml).

---

## Точка входа

- приложение создается в [src/app_factory.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/app_factory.py)
- экспорт `app` находится в [src/app.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/app.py)
- класс приложения: [src/dnk_app.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/dnk_app.py)
- общий router собирается
  в [src/modules/router.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/router.py)

Текущий `lifespan`:

1. кладет `session_factory` в `app.state.db`
2. кладет `db_helper` в `app.state.db_helper`
3. вызывает `create_all()`
4. при остановке делает `dispose()`

`token_manager` и `email_sender` при необходимости могут быть переопределены через `app.state.*`, что активно используется в тестах.

---

## Актуальная структура проекта

```text
src/
  app.py
  app_factory.py
  dnk_app.py
  config/
    app_config.py
    auth_config.py
    control_plane.py
    redis_config.py
    infrastructure/
    packaging/
  modules/
    router.py
    persistence.py
    shared/
      db/
      depends/
      domain/
      http/
      tokens/
      uow.py
    tenancy/
      application/
        ports/
        tenant/
          command/
          dto/
          use_case/
        tenant_domain/
          dto/
          query/
          use_case/
      domain/
        service/
        tenant/
          value_object/
        tenant_domain/
          value_object/
      infrastructure/
        adapter/
        mapper/
        persistence/
        repository/
      presentation/
        depends/
        http/
          admin_tenant/
            controller/
            requests/
            responses/
          console_tenant/
            controller/
            responses/
    identity/
      application/
        auth/
          command/
          dto/
          service/
          use_case/
        ports/
        user/
          dto/
          service/
      domain/
        auth/
        user/
      infrastructure/
        adapter/
        mapper/
        persistence/
        repository/
      presentation/
        depends/
        http/
          console_auth/
            controller/
            requests/
            responses/
    crm/
    runtime_data/
    schema_registry/
test/
  test_architecture_boundaries.py
  test_identity_use_cases.py
  test_identity_http_router.py
  test_tenancy_create_tenant_use_case.py
  test_tenant_schema_bootstrap_boundary.py
  test_tenancy_http_router.py
  test_schema_registry_*.py
  test_crm_*.py
```

`crm`, `runtime_data`, `schema_registry`, `identity` и `tenancy` содержат текущую рабочую прикладную логику проекта.

---

## Конфигурация

Все конфиги агрегируются
через [src/config/app_config.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/config/app_config.py) в
`DnkConfig`.

Сейчас проект использует несколько config-групп:

- `DatabaseConfig`
  - SQLAlchemy connection и pool settings
- `RedisConfig`
  - `REDIS_HOST`
  - `REDIS_PORT`
  - `REDIS_USERNAME`
  - `REDIS_PASSWORD`
  - `REDIS_USE_SSL`
  - `REDIS_DB`
- `IdentityAuthConfig`
  - `AUTH.otp_code_length`
  - `AUTH.otp_token_ttl_seconds`
  - `AUTH.session_ttl_seconds`
  - `AUTH.session_cookie_name`
- `ControlPlaneConfig`
  - `CONTROL_PLANE_API_KEY`
- `PackagingInfo`
  - packaging metadata из `pyproject.toml`

Конфиг читается из:

1. init values
2. env
3. `.env`
4. file secrets
5. `pyproject.toml`

Для nested-настроек включен `env_nested_delimiter="__"`, поэтому auth-параметры можно задавать как:

- `AUTH__OTP_CODE_LENGTH`
- `AUTH__OTP_TOKEN_TTL_SECONDS`
- `AUTH__SESSION_TTL_SECONDS`
- `AUTH__SESSION_COOKIE_NAME`

---

## Shared слой

`shared` содержит только технические кросс-модульные компоненты:

- [src/modules/shared/db/helper.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/db/helper.py)
  - создание engine
  - session factory
  - `create_all()`
- [src/modules/shared/uow.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/uow.py)
  - request-scoped `UnitOfWork`
- [src/modules/shared/depends/uow.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/depends/uow.py)
  - FastAPI dependency для `UoW`
- [src/modules/shared/http/host.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/http/host.py)
  - общая нормализация `host`
  - извлечение `host` из `Request`
- [src/modules/shared/depends/request_host.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/depends/request_host.py)
  - dependency `RequestHostDep`
- [src/modules/shared/tokens/](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens)
  - `TokenManager`
  - in-memory backend
  - Redis repository
  - Redis adapter

`TokenManager` — технический storage manager для OTP/session token state. Это не domain-service `identity`.

---

## Модуль `tenancy`

### Ответственность

`tenancy` владеет:

- `Tenant`
- `TenantDomain`
- статусами tenant/domain
- правилом определения tenant по `host`
- server-to-server созданием tenant

### Domain

Файлы:

- [src/modules/tenancy/domain/tenant/entity.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/tenant/entity.py)
- [src/modules/tenancy/domain/tenant_domain/entity.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/tenant_domain/entity.py)
- [src/modules/tenancy/domain/service/tenant_onboarding.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/service/tenant_onboarding.py)

Бизнес-правила:

- `TenantStatus`
  - `active`
  - `freeze`
- `TenantDomainStatus`
  - домен может быть удален через статус `deleted`
- tenant определяет прикладной режим работы:
  - `allows_login()` -> только `active`
  - `allows_read_business_data()` -> `active` и `freeze`
  - `allows_write_business_data()` -> только `active`

Это важно для будущих CRM/read-only сценариев:

- `freeze` означает, что tenant может остаться доступным для чтения бизнес-данных;
- но write-операции должны быть запрещены прикладным модулем.

### Application

Текущая раскладка application-слоя:

1. `tenant`
    - `command/create_tenant_command.py`
    - `dto/create_tenant_result_dto.py`
    - `use_case/create_tenant.py`
2. `tenant_domain`
    - `query/resolve_tenant_by_host_query.py`
    - `query/resolve_tenant_request_context_by_host_query.py`
    - `dto/resolve_tenant_by_host_result_dto.py`
    - `dto/tenant_request_context_dto.py`
    - `use_case/resolve_tenant_by_host.py`
    - `use_case/resolve_tenant_request_context_by_host.py`
3. `ports`
    - tenancy-owned интеграционные порты к `identity` и `schema_registry`

### Presentation

Роуты:

- `POST /api/admin/create-tenant`
- `GET /api/console/tenants/resolve`

Схемы request/response вынесены в отдельные файлы:

- `presentation/http/admin_tenant/requests/*`
- `presentation/http/admin_tenant/responses/*`
- `presentation/http/console_tenant/responses/*`

### Infrastructure

Содержит:

- SQLAlchemy persistence models
- SQLAlchemy repositories в `infrastructure/repository/`
- mapping domain <-> DB в `infrastructure/mapper/`
- adapter к identity provisioning в `infrastructure/adapter/`

### Текущий create-tenant flow

`POST /api/admin/create-tenant`:

1. route получает request schema
2. route проходит Bearer API key guard
3. payload маппится в `CreateTenantCommand`
4. `CreateTenantUseCase` вызывает:
    - `TenantOnboardingService`
   - `IdentityProvisioningServiceAdapter`
    - `TenantSchemaBootstrapPort`
5. use case не открывает собственный `UoW` и не делает `commit()`/`rollback()`
6. работа идет в request-scoped session через зависимости FastAPI

Endpoint принимает:

- `tenant.name`
- `tenant.external_id`
- `tenant_domain.host`
- `user.first_name`
- `user.last_name`
- `user_email.email`

### Текущий resolve flow

`GET /api/console/tenants/resolve`:

1. общий shared dependency извлекает `host`
2. `ResolveTenantByHostUseCase` ищет не удаленный `TenantDomain`
3. получает связанный `Tenant`
4. возвращает read-model:
   - `exists`
   - `available`
   - `status`
   - `tenant_id`
   - `api_host`

`available=true` только если tenant допускает login.

---

## Модуль `identity`

### Ответственность

`identity` владеет:

- `User`
- `UserEmail`
- tenant-scoped поиском user по primary email
- auth-flow по email OTP + session
- tenant-scoped валидацией session и чтением/обновлением current user profile
- provisioning tenant admin пользователя для onboarding в `tenancy`

### Domain

Файлы:

- [src/modules/identity/domain/user/entity.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/user/entity.py)
- [src/modules/identity/domain/user/error.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/user/error.py)
- [src/modules/identity/domain/user/repository.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/user/repository.py)
- [src/modules/identity/domain/auth/error.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/src/modules/identity/domain/auth/error.py)

Бизнес-правила:

- email нормализуется как `strip().lower()`
- login разрешен только для primary email
- `UserEmail.is_deleted = true` не участвует в login flow
- при успешном confirm email может быть помечен как verified

### Application

Application-слой разделен на:

1. `user`
    - `dto/created_tenant_admin.py`
    - `service/user_service.py`
2. `auth`
    - `command/*`
    - `dto/*`
    - `service/*`
    - `use_case/*`
   - use case instances вызываются через `__call__`, а не `execute`
3. `ports`
    - `email_sender.py`
    - `tenant_context_reader.py`
    - `token_store.py`

### Auth-flow

#### `POST /api/console/auth/request-otp`

1. route берет `host` через shared dependency
2. `RequestEmailOtpUseCase` запрашивает tenant-context у `tenancy`
3. user ищется по `tenant_id + primary email`
4. генерируется:
   - `token`
   - цифровой `code`
   - `code_hash`
5. challenge пишется в token store
6. code отправляется через email sender adapter
7. response возвращает:
   - `token`
   - `expires_in`
   - `code` только в development mode

#### `POST /api/console/auth/confirm-otp`

1. повторно определяется `host`
2. повторно загружается tenant-context
3. challenge читается из token store
4. валидируются:
   - tenant
   - tenant domain
   - host
   - email
   - token
   - code
5. user повторно загружается из БД
6. создается session record
7. session сохраняется в token store
8. OTP challenge инвалидируется
9. при необходимости `UserEmail.is_verified = true`
10. `UoW.commit()`
11. route выставляет session cookie

#### `POST /api/console/auth/logout`

1. определяется `host`
2. загружается tenant-context
3. session token читается из cookie
4. session проверяется на совпадение:
   - `tenant_id`
   - `tenant_domain_id`
   - `host`
5. session инвалидируется
6. route очищает cookie

#### `GET /api/console/auth/me`

1. определяется `host`
2. загружается tenant-context
3. session token читается из cookie
4. session проверяется на совпадение:
   - `tenant_id`
   - `tenant_domain_id`
   - `host`
5. user загружается по `session.user_id`
6. проверяется статус user (`active`)
7. response возвращает user profile и `emails` c фильтром `is_deleted = false`

#### `PATCH /api/console/auth/me`

1. определяется `host`
2. загружается tenant-context
3. session token читается из cookie
4. session проверяется на совпадение:
   - `tenant_id`
   - `tenant_domain_id`
   - `host`
5. user загружается по `session.user_id`
6. проверяется статус user (`active`)
7. обновляются поля:
   - `last_name`, `first_name`, `middle_name`
   - `interface_language` (`uk`/`en`)
   - `interface_theme` (`system`/`dark`/`light`, обязательно)
   - `timezone` (`Europe/Kyiv`/`Europe/Warsaw`)
   - дополнительные поля вне контракта PATCH payload отклоняются
8. `UoW.commit()`
9. response возвращает обновленный user profile и `emails` c фильтром `is_deleted = false`

### Presentation

HTTP-слой разложен по CRM-подобной структуре:

- `presentation/http/console_auth/controller/*`
- `presentation/http/console_auth/requests/*`
- `presentation/http/console_auth/responses/*`
- `presentation/depends/application.py`
- `presentation/depends/infrastructure.py`

Контроллеры сами мапят domain/tenancy ошибки в `HTTPException`.
Отдельный shared `error_mapper.py` для `identity` не используется.

### Infrastructure

Содержит:

- SQLAlchemy repository в `infrastructure/repository/user_repository.py`
- явный ORM -> domain mapping прямо в `repository/user_repository.py`
- adapters:
    - `tenant_context.py`
    - `otp_challenge_store.py`
    - `session_store.py`
    - `email_sender.py`
- persistence models в `infrastructure/persistence/`

### Token storage и email sender

`identity` работает не напрямую с Redis, а через:

- `OtpChallengeStorePort`
- `SessionStorePort`
- shared `TokenManager`

В production path default `TokenManager` пытается использовать Redis backend.
Если Redis backend недоступен, shared dependency логирует warning и откатывается на in-memory fallback.

Для MVP используется `InMemoryEmailSender` как stub adapter.
Это техническая заглушка, а не финальный интеграционный email provider.

### Правило tenant по host

В проекте уже централизовано правило:

- `host` всегда извлекается из `Request`
- `host` всегда нормализуется в shared слое
- auth-flow не доверяет frontend resolve-check и всегда повторно валидирует tenant context

Для login-сценариев внутренний источник истины — `ResolveTenantRequestContextByHostUseCase`.

Этот use case:

- возвращает `tenant_id`, `tenant_domain_id`, `host`, `tenant_status`, `domain_status`, `api_host`
- либо бросает предметную ошибку:
  - tenant по host не найден
  - tenant недоступен для login

## Текущее тестовое покрытие

Сейчас есть:

- [test/test_architecture_boundaries.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_architecture_boundaries.py)
    - архитектурные границы модулей
  - запрет legacy import-путей, включая старые `identity` import roots
  - запрет импортов удалённых `controller/error_mapper.py` и `infrastructure/mapper`
- [test/test_identity_use_cases.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_identity_use_cases.py)
    - request/confirm OTP
    - authenticate by session
    - current user
    - profile update
    - logout
    - tenant admin provisioning service
- [test/test_identity_repository.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_identity_repository.py)
    - явный ORM -> domain mapping в repository return
- [test/test_identity_http_router.py](/Users/denisnikoncuk/PycharmProjects/dnk-runtime-core/test/test_identity_http_router.py)
    - сохранение публичных identity routes
    - cookie set/delete semantics
  - tenant-aware HTTP error mapping прямо в controller-файлах

---

## Архитектурные договоренности

1. Один request = один `UoW` = одна SQLAlchemy session.
2. HTTP layer не содержит бизнес-логики.
3. Domain не знает про FastAPI, SQLAlchemy, Redis.
4. Cross-module взаимодействие должно идти через application ports/adapters, а не через ORM-модели чужого модуля.
5. `shared` хранит технические механизмы, но не бизнес-правила конкретного bounded context.
6. `tenancy` — источник истины для host -> tenant context.
7. `identity` — источник истины для user/email/auth.
