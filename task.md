## 1. Цель

Нужно доработать модуль `tenancy` в текущей архитектуре проекта (**DDD + Clean Architecture**) для двух сценариев:

1. Расширить существующий endpoint `POST /api/admin/create-tenant`, чтобы его мог вызывать `ControlPlane` с server-to-server авторизацией по `API_KEY`, а также передавать `external_id`.
2. Добавить endpoint `GET /api/console/tenants/resolve`, который по `host` клиента определяет, существует ли Tenant на данном домене, и возвращает его состояние.

Дополнительно нужно расширить модель Tenant новым статусом: `freeze`.

---

## 2. Изменения в существующем create endpoint

## 2.1. Используем существующий endpoint

Новый endpoint создавать не нужно.

Дорабатываем **существующий**:

```text
POST /api/admin/create-tenant
```

---

## 2.2. Авторизация для вызова от `ControlPlane`

Запрос на создание Tenant должен быть доступен для server-to-server вызова от `ControlPlane`.

**Требования:**

* endpoint должен быть защищен по `API_KEY`;
* ключ хранится в `config/` проекта;
* значение читается из переменной окружения через **Pydantic Settings**;
* ключ передается в заголовке:

```http
Authorization: Bearer <API_KEY>
```

* при отсутствии заголовка или неверном ключе возвращать `401 Unauthorized`.

**Важно:**
Так как endpoint остается `POST /api/admin/create-tenant`, нужно встроить эту проверку в текущий flow данного route, не создавая отдельного internal route.

---

## 2.3. Добавить `external_id` в create flow

В существующий сценарий создания Tenant нужно добавить новое поле:

* `external_id` — идентификатор Tenant в системе `ControlPlane`.

**Требования:**

* `external_id` должен приходить в request DTO;
* `external_id` должен передаваться в use case;
* `external_id` должен сохраняться в сущности Tenant;
* `external_id` должен сохраняться в БД.

**Рекомендуемо:**

* сделать `external_id` уникальным.

---

## 3. Новый endpoint resolve Tenant

Нужно добавить endpoint:

```text
GET /api/console/tenants/resolve
```

---

## 3.1. Назначение

Endpoint должен:

1. принимать входящий запрос;
2. брать `host` клиента из request;
3. искать Tenant по этому host;
4. учитывать только не удаленные домены;
5. возвращать состояние Tenant.

---

## 3.2. Источник host

`host` не передается в body.

Нужно брать его из HTTP request:

* из `Host` header / request host.

Перед поиском `host` нужно нормализовать:

* `strip()`
* `lower()`

---

## 3.3. Логика поиска

Ищем Tenant через `TenantDomain`:

* по `TenantDomain.host`
* только среди записей, где домен **не удален**
* `is_deleted = false`

Если домен найден — получаем связанный Tenant и анализируем его статус.

---

## 4. Новый статус Tenant

Для Tenant нужно добавить новый статус:

* `freeze`

Итого поддерживаем:

* `active`
* `freeze`

---

## 5. Поведение `GET /api/console/tenants/resolve`

## 5.1. Если Tenant найден и статус `active`

Возвращаем, что Tenant существует и доступен.

**Ответ:**

* `exists = true`
* `available = true`
* `status = active`
* `tenant_id`
* домен, который используется для API (`api_host`)

**Пример:**

```json
{
  "exists": true,
  "available": true,
  "status": "active",
  "tenant_id": "019c....",
  "api_host": "api.acme.example.com"
}
```

---

## 5.2. Если Tenant найден и статус `freeze`

Возвращаем, что Tenant существует, но недоступен для нормальной работы.

**Ответ:**

* `exists = true`
* `available = false`
* `status = freeze`
* `tenant_id`
* `api_host`

**Пример:**

```json
{
  "exists": true,
  "available": false,
  "status": "freeze",
  "tenant_id": "019c....",
  "api_host": "api.acme.example.com"
}
```

---

## 5.3. Если Tenant не найден

Если по host нет ни одного не удаленного домена — возвращаем:

```json
{
  "exists": false,
  "available": false,
  "status": "not_found",
  "tenant_id": null,
  "api_host": null
}
```

**HTTP статус:**

* `200 OK`

---

## 6. Архитектурная реализация по слоям

## 6.1. Domain

Нужно доработать сущность `Tenant`:

* добавить поле `external_id`;
* добавить поддержку статуса `freeze`.

**Что обновить:**

* фабрику / конструктор Tenant;
* валидацию статуса;
* enum / VO статуса Tenant.

---

## 6.2. Application

### A. Доработка существующего use case создания Tenant

Нужно расширить текущий use case, который стоит за `POST /api/admin/create-tenant`:

* принять `external_id`;
* проверить бизнес-ограничения;
* создать Tenant с новым полем.

### B. Новый read use case: `ResolveTenantByHost`

Новый use case должен:

* принять `host`;
* найти `TenantDomain` по host;
* игнорировать удаленные домены;
* загрузить Tenant;
* вернуть response DTO.

---

## 6.3. Infrastructure

Нужно доработать persistence-слой:

* добавить колонку `external_id` в таблицу Tenant;
* расширить допустимые значения статуса (`freeze`);
* обновить ORM mapping;
* доработать repository метод для поиска по host.

**Нужны методы уровня репозитория:**

* `exists_by_external_id(...)`
* `get_by_host(...)` или query-метод для resolve

---

## 6.4. Presentation

### Для `POST /api/admin/create-tenant`

Нужно доработать текущий route:

* добавить dependency / guard, который валидирует Bearer API key;
* расширить request schema полем `external_id`.

### Для `GET /api/console/tenants/resolve`

Нужно добавить новый route:

* читает `host` из request;
* вызывает `ResolveTenantByHost`;
* возвращает read-model response.

---

## 6.5. Config

Нужно добавить в settings:

* `CONTROL_PLANE_API_KEY`

Источник:

* env variable
* Pydantic Settings

---

## 7. Что меняется по файлам

### Добавить

* `src/modules/tenancy/application/resolve_tenant_by_host/dto.py`
* `src/modules/tenancy/application/resolve_tenant_by_host/use_case.py`
* `src/modules/tenancy/presentation/api/console_tenants.py`
* `src/modules/tenancy/presentation/depends/control_plane_auth.py`

### Изменить

* `src/modules/tenancy/domain/entities.py`
* `src/modules/tenancy/domain/value_objects/*` (если статус как VO)
* `src/modules/tenancy/application/.../create_tenant*.py`
* `src/modules/tenancy/infrastructure/persistence/tenant.py`
* `src/modules/tenancy/infrastructure/repositories.py`
* `src/modules/tenancy/presentation/api/admin*.py`
* `src/modules/tenancy/presentation/api/router.py`
* `src/modules/router.py`
* `src/config/app_config.py` (или соответствующий settings module)

---

## 8. Acceptance Criteria

1. `POST /api/admin/create-tenant` принимает Bearer API key.
2. При отсутствии или неверном API key возвращается `401 Unauthorized`.
3. `POST /api/admin/create-tenant` принимает `external_id`.
4. При создании Tenant поле `external_id` сохраняется в доменной модели и БД.
5. Tenant поддерживает статус `freeze`.
6. `GET /api/console/tenants/resolve` читает `host` из request.
7. Поиск идет только по `TenantDomain`, где `is_deleted = false`.
8. Для `active` возвращается `exists=true`, `available=true`, `tenant_id`, `api_host`.
9. Для `freeze` возвращается `exists=true`, `available=false`, `status=freeze`.
10. Для отсутствующего host возвращается `exists=false`, `status=not_found`.
11. Реализация не нарушает границы модуля `tenancy` и текущий `UoW` flow.

---

## 9. Тесты

### Для `POST /api/admin/create-tenant`

* успешное создание Tenant по валидному API key;
* `401`, если нет `Authorization`;
* `401`, если Bearer token неверный;
* сохранение `external_id`;
* конфликт при дублировании `external_id` (если делаем unique);
* конфликт при дублировании host.

### Для `GET /api/console/tenants/resolve`

* найден Tenant со статусом `active`;
* найден Tenant со статусом `freeze`;
* домен удален (`is_deleted = true`) → результат `not_found`;
* host нормализуется в lower-case;
* по отсутствующему host возвращается `exists=false`.