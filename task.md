## 1. Цель

Нужно добавить в проект полноценный auth-flow для пользователей системы, где авторизация всегда привязана к **конкретному Tenant и его домену**.

Реализация должна лечь в текущую модульную структуру `src/modules`, не ломать правило **1 request = 1 UoW = 1 SQLAlchemy session**, и соблюдать границы bounded contexts: `tenancy` владеет Tenant/Domain, `identity` владеет User/UserEmail, а `shared` хранит только технические cross-module компоненты.   

---

## 2. Бизнес-идея

Каждый Tenant работает на своем домене, поэтому **каждый auth-запрос должен проверять, с какого host он пришел**.

Базовый пользовательский путь:

1. Пользователь открывает сайт Tenant.
2. Фронтенд вызывает `GET /api/console/tenants/resolve`.
3. Если Tenant активен — показывается форма логина.
4. Пользователь вводит email.
5. Бэкенд генерирует `token` + `code`, отправляет `code` на email, а `token` возвращает фронтенду.
6. Пользователь вводит code.
7. Фронтенд отправляет `token + code + email` в `confirm_otp`.
8. Если все валидно — бэкенд создает session в Redis и выставляет **session cookie на тот же host**, с которого пришел запрос.
9. Для выхода из системы отдельный endpoint инвалидирует session и очищает cookie.

---

## 3. Ключевые бизнес-правила

### 3.1. Tenant всегда определяется по host

Для `request_otp`, `confirm_otp` и `logout` backend **на каждом запросе заново**:

* берет `host` из request;
* нормализует `host` (`strip().lower()`);
* проверяет, что этот host принадлежит не удаленному `TenantDomain`;
* проверяет, что Tenant в допустимом статусе для логина.

Нельзя доверять только фронтенду. Даже если фронт уже вызвал `resolve`, backend должен повторно валидировать tenant-context.

---

### 3.2. Email должен проверяться в контексте Tenant

Сейчас в проекте email уникален **только внутри конкретного tenant**, а одинаковый email в разных tenant разрешен. Нормализация email уже заложена как `.strip().lower()`. 

Значит логин по email должен искать пользователя **внутри текущего tenant**, а не глобально.

---

### 3.3. Логин только через primary email

Рекомендуемое правило для этого сценария:

* авторизация разрешена только по `UserEmail`, где `is_primary = true`;
* `UserEmail` с `is_deleted = true` не участвует;
* после успешного `confirm_otp` можно пометить email как подтвержденный (`is_verified = true`), если он еще не подтвержден.

---

### 3.4. OTP challenge должен быть привязан к tenant + host + email

Чтобы нельзя было использовать token между разными tenant/доменами, OTP challenge в Redis должен быть связан с:

* `tenant_id`
* `tenant_domain_id`
* `host`
* `email`

То есть `confirm_otp` валидирует не только `token` и `code`, но и совпадение tenant-context.

---

## 4. API endpoints

Рекомендуемый console API:

```text
POST /api/console/auth/request-otp
POST /api/console/auth/confirm-otp
POST /api/console/auth/logout
```

`GET /api/console/tenants/resolve` уже используется как pre-check до показа формы.

---

## 5. Контракт endpoint'ов

## 5.1. `POST /api/console/auth/request-otp`

### Request

Пользователь отправляет:

```json
{
  "email": "john@example.com"
}
```

### Backend flow

1. Получить `host` из request.
2. Через `tenancy` проверить, что на host есть активный Tenant.
3. Нормализовать email.
4. Найти `UserEmail` внутри текущего tenant:

   * `is_primary = true`
   * `is_deleted = false`
5. Сгенерировать:

   * `token` — случайная строка
   * `code` — цифровой код длиной из config
6. Сохранить challenge в Redis через `TokenManager`.
7. Отправить `code` на email.
8. Вернуть `token` и TTL.

### Response

```json
{
  "token": "otp_xxx",
  "expires_in": 300
}
```

**Важно:**
`code` в response не возвращать. Только отправка на email.

---

## 5.2. `POST /api/console/auth/confirm-otp`

### Request

```json
{
  "email": "john@example.com",
  "token": "otp_xxx",
  "code": "123456"
}
```

### Backend flow

1. Получить `host` из request.
2. Повторно resolve Tenant по host.
3. Нормализовать email.
4. Загрузить OTP challenge из Redis по `token`.
5. Проверить:

   * challenge существует;
   * не истек TTL;
   * `email` совпадает;
   * `host` совпадает;
   * `tenant_id` / `tenant_domain_id` совпадают;
   * `code` валиден.
6. Повторно найти `UserEmail` в БД в рамках tenant:

   * на случай, если пользователь был удален/деактивирован между шагами.
7. Создать session token.
8. Сохранить session в Redis.
9. Инвалидировать OTP challenge.
10. Выставить session cookie в response.
11. При необходимости обновить `UserEmail.is_verified = true`.
12. Сделать `commit()` в конце use case.

### Response

```json
{
  "ok": true,
  "user_id": "019c....",
  "tenant_id": "019c...."
}
```

Плюс `Set-Cookie` с session token.

---

## 5.3. `POST /api/console/auth/logout`

### Request

Тело не обязательно. Session читается из cookie.

### Backend flow

1. Получить `host` из request.
2. Resolve Tenant по host.
3. Прочитать session token из cookie.
4. Найти session в Redis.
5. Проверить, что session принадлежит:

   * этому `tenant_id`
   * этому `tenant_domain_id`
   * этому `host`
6. Инвалидировать session token в Redis.
7. Вернуть response с очисткой cookie (`max-age=0` / expired).

### Response

```json
{
  "ok": true
}
```

---

## 6. Архитектура по модулям

## 6.1. `modules/tenancy`

`tenancy` уже владеет `Tenant` и `TenantDomain`, поэтому именно он остается источником истины для проверки host. 

### Что использовать

* существующий `GET /api/console/tenants/resolve` как внешний pre-check для UI;
* внутри auth-flow — отдельный application port / use case для получения `TenantRequestContext` по host.

### Что нужно добавить/использовать

В `tenancy` желательно иметь read-scenario уровня:

* `ResolveActiveTenantByHostUseCase`
  или
* `GetTenantRequestContextByHostUseCase`

Он должен вернуть минимальный контекст:

* `tenant_id`
* `tenant_domain_id`
* `host`
* `tenant_status`
* `domain_status`
* `api_host` / `service_type` (если нужно)

Этот сценарий не должен импортироваться через ORM из `identity`; взаимодействие только через port/adapter.

---

## 6.2. `modules/identity`

`identity` уже владеет `User` и `UserEmail`, поэтому auth-flow должен жить именно здесь, как новый bounded-context сценарий поверх существующего provisioning-направления. 

### Новый application slice

Рекомендуется добавить новый раздел:

```text
src/modules/identity/application/auth/
```

Внутри:

* `dto.py`
* `ports/`
* `services/`
* `use_cases/`

### Нужные use cases

1. `RequestEmailOtpUseCase`
2. `ConfirmEmailOtpUseCase`
3. `LogoutCurrentSessionUseCase`

---

## 6.3. `modules/shared`

`shared` по вашему контексту хранит только действительно общие технические компоненты, а не бизнес-логику конкретного модуля. Поэтому `TokenManager` — хороший кандидат именно для `shared`, так как это инфраструктурный reusable-компонент для Redis token storage. 

---

## 7. Shared `TokenManager`

## 7.1. Назначение

Нужен общий `TokenManager`, который умеет работать с Redis-ключами для:

* OTP challenge
* session token
* в будущем — reset password, invite links, magic links и т.д.

Это не domain-service `identity`, а **технический storage-manager**.

---

## 7.2. Где разместить

Рекомендуемо:

```text
src/modules/shared/tokens/
  manager.py
  protocols.py
  models.py
```

или проще:

```text
src/modules/shared/token_manager.py
```

Но лучше отдельной папкой.

---

## 7.3. Модель ключа

У токена должны быть:

* `prefix`
* `suffix`
* `token`
* `body`
* `ttl`

### Рекомендуемый формат Redis key

```text
<prefix>:<suffix>:<token>
```

### Примеры

* OTP:

```text
otp_login:<tenant_id>:<token>
```

* Session:

```text
session:<tenant_id>:<token>
```

Если хотите сильнее привязать к host, можно suffix делать составным:

```text
otp_login:<tenant_id>:<tenant_domain_id>:<token>
session:<tenant_id>:<host_hash>:<token>
```

---

## 7.4. Что хранить в `body`

### Для OTP

* `email`
* `tenant_id`
* `tenant_domain_id`
* `host`
* `code_hash`
* `created_at`

**Важно:**
в Redis лучше хранить не raw `code`, а `code_hash`.

### Для session

* `session_id` (логический id, если нужен)
* `user_id`
* `tenant_id`
* `tenant_domain_id`
* `host`
* `issued_at`
* `expires_at`

---

## 7.5. Методы `TokenManager`

Обязательные методы:

* `set_token(prefix, suffix, token, body, ttl) -> None`
* `exists(prefix, suffix, token) -> bool`
* `get_token(prefix, suffix, token) -> dict | None`
* `invalidate(prefix, suffix, token) -> None`

Дополнительно очень полезно добавить:

* `consume_token(...) -> body | None`
  (атомарно прочитать и удалить; идеально для OTP)

Для `logout` достаточно:

* прочитать session token из cookie;
* `invalidate(...)`.

---

## 8. Конфиг

Нужен отдельный config-файл и отдельный config-класс, который подключается к `DnkConfig`.

## 8.1. Где разместить

Рекомендуемо:

```text
src/config/auth_config.py
```

---

## 8.2. Класс настроек

Рекомендуемое имя:

* `IdentityAuthConfig`

И подключение в:

* `DnkConfig`

---

## 8.3. Обязательные настройки

1. `otp_code_length`
2. `otp_token_ttl_seconds`
3. `session_ttl_seconds`
4. `session_cookie_name`

Пример логики:

* `otp_code_length = 6`
* `otp_token_ttl_seconds = 300`
* `session_ttl_seconds = 432000` (5 дней)
* `session_cookie_name = "dnk_session"`

---

## 8.4. Как читать из env

Лучше использовать nested-конфиг через `pydantic-settings`, чтобы значения приходили из env и собирались в `DnkConfig`.

Пример подхода:

* `AUTH__OTP_CODE_LENGTH`
* `AUTH__OTP_TOKEN_TTL_SECONDS`
* `AUTH__SESSION_TTL_SECONDS`
* `AUTH__SESSION_COOKIE_NAME`

---

## 9. Application ports

Чтобы не ломать модульные границы, в `identity.application.auth.ports` нужны отдельные контракты.

## 9.1. `TenantContextReaderPort`

Порт для получения tenant-context по `host`.

Метод:

* `get_active_by_host(host: str) -> TenantRequestContext | None`

Реализация адаптера будет использовать `tenancy`, но без прямого импорта ORM другого модуля.

---

## 9.2. `UserEmailReaderPort`

Для поиска primary email в рамках tenant.

Методы:

* `get_primary_active_email(tenant_id, email) -> UserEmail | None`

---

## 9.3. `OtpChallengeStorePort`

Для хранения OTP challenge.

Можно реализовать поверх shared `TokenManager`.

Методы:

* `create_challenge(...)`
* `get_challenge(...)`
* `invalidate_challenge(...)`

---

## 9.4. `SessionStorePort`

Для хранения сессий в Redis.

Тоже поверх shared `TokenManager`.

Методы:

* `create_session(...)`
* `get_session(...)`
* `invalidate_session(...)`

---

## 9.5. `EmailSenderPort`

Технический порт для отправки кода на email.

Метод:

* `send_login_code(email, code)`

Для MVP можно сделать stub/adapter.

---

## 10. Domain и application логика

## 10.1. Что остается в domain

В `identity.domain` должны оставаться бизнес-правила про:

* допустимость логина пользователя;
* работу с primary email;
* подтверждение email (если это часть доменной логики).

Но Redis token/session storage — это не domain, а infrastructure/application boundary.

---

## 10.2. Session как MVP

Так как вы явно хотите хранить session в Redis, для MVP **не нужен SQL ORM для сессий**.

Лучше сделать так:

* session — это auth-state;
* живет в `SessionStorePort` (Redis);
* в БД его не дублируем;
* при необходимости позже можно добавить отдельную persistence-модель.

Это позволит не усложнять схему сейчас.

---

## 11. Cookie policy

Session cookie должна выставляться **на тот же host**, с которого пришел запрос к Tenant.

### Требования

* `HttpOnly = true`
* `Secure = true` (в prod)
* `SameSite = "Lax"`
* `Path = "/"`
* `Max-Age = session_ttl_seconds`

### Важно

Не указывать общий `Domain=.example.com`, если хотите жестко изолировать tenant по host.
Для multi-tenant по отдельным host безопаснее **host-only cookie**.

---

## 12. Последующая авторизация на защищенных endpoints

Сразу стоит заложить shared/dependency flow для последующих запросов в console API:

1. взять `host`;
2. resolve tenant;
3. прочитать session cookie;
4. найти session в Redis;
5. убедиться, что `tenant_id` и `host` совпадают;
6. построить `AuthContext`.

То есть login/logout — это только начало. После этого должен появиться reusable dependency вида:

* `get_current_identity_session()`
* `get_current_auth_context()`

который потом будет использоваться в `crm`, `org`, `catalog` endpoints.

---

## 13. Структура файлов

### Добавить в `identity`

```text
src/modules/identity/
  application/
    auth/
      dto.py
      ports/
        tenant_context.py
        repositories.py
        token_store.py
        email_sender.py
      services/
        otp_service.py
        session_service.py
      use_cases/
        request_email_otp.py
        confirm_email_otp.py
        logout_current_session.py
  presentation/
    api/
      console_auth.py
    depends/
      auth_repositories.py
      auth_services.py
      auth_use_cases.py
```

### Добавить в `shared`

```text
src/modules/shared/
  tokens/
    protocols.py
    manager.py
    models.py
    redis_adapter.py
```

### Добавить в `config`

```text
src/config/
  auth_config.py
```

### Изменить

* `src/config/app_config.py`
* `src/modules/router.py`
  (сейчас у вас подключен только router `tenancy`, нужно добавить router `identity`) 
* `src/modules/persistence.py`
  (если появятся новые persistence-модули; для Redis-only session это может не понадобиться)
* `src/modules/identity/presentation/api/router.py`

---

## 14. Acceptance Criteria

1. `POST /api/console/auth/request-otp` принимает email и определяет Tenant по `host`.
2. Запрос не проходит, если host не принадлежит активному Tenant.
3. Email ищется только внутри текущего tenant.
4. Логин разрешен только по primary email.
5. Backend генерирует случайный `token` и цифровой `code`.
6. OTP challenge сохраняется в Redis через shared `TokenManager`.
7. Код отправляется на email, а в response возвращается только `token` и TTL.
8. `POST /api/console/auth/confirm-otp` повторно валидирует `host`, `tenant`, `email`, `token`, `code`.
9. При успешном confirm создается session в Redis.
10. В response выставляется host-only session cookie.
11. OTP token после успешного confirm инвалидируется.
12. `POST /api/console/auth/logout` инвалидирует текущую session в Redis.
13. Logout очищает cookie в response.
14. Реализация не нарушает границы модулей и не тянет ORM одного модуля в другой.

---

## 15. Тесты

### `request_otp`

* успешный запрос для активного tenant + valid email;
* `404/403`, если tenant по host не найден или неактивен;
* отказ, если email не найден в текущем tenant;
* отказ, если email не primary;
* проверка, что OTP challenge записан в Redis;
* проверка, что token возвращен, а code — нет.

### `confirm_otp`

* успешное подтверждение;
* неверный `code`;
* неверный `token`;
* истекший OTP;
* `email` не совпадает с challenge;
* `host` не совпадает с challenge;
* попытка использовать OTP повторно после успешного confirm;
* проверка, что session создана в Redis;
* проверка, что cookie выставлена.

### `logout`

* успешный logout по валидной session;
* повторный logout по уже удаленной session;
* очистка cookie;
* session другого tenant/host не может быть инвалидирована чужим host.