# Tenancy Module

## Ответственность

`src/modules/tenancy` — bounded context, который владеет:

- `Tenant`
- `TenantDomain`
- статусами tenant/domain
- определением tenant по `host`
- server-to-server созданием tenant

`tenancy` — источник истины для tenant-context, который потом используют другие модули.

## Структура

```text
tenancy/
  application/
    admin_onboarding/
    request_context_by_host/
    resolve_tenant_by_host/
  domain/
  infrastructure/
  presentation/
```

## Domain

Ключевые файлы:

- [`src/modules/tenancy/domain/entities.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/entities.py)
- [`src/modules/tenancy/domain/errors.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/errors.py)
- [`src/modules/tenancy/domain/value_objects/tenant_status.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/value_objects/tenant_status.py)
- [`src/modules/tenancy/domain/value_objects/tenant_domian_status.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/domain/value_objects/tenant_domian_status.py)

### Domain rules

`Tenant` поддерживает:

```python
def allows_login(self) -> bool
def allows_read_business_data(self) -> bool
def allows_write_business_data(self) -> bool
```

Смысл статусов:

- `active`
  - login разрешен
  - чтение разрешено
  - запись разрешена
- `freeze`
  - login запрещен текущим auth-flow
  - чтение бизнес-данных допустимо
  - запись должна быть запрещена прикладными модулями

`TenantDomainStatus` также содержит `deleted`, и такие домены не участвуют в resolve/search по host.

## Application

### `admin_onboarding`

Назначение:

- создание tenant и его стартового набора сущностей

DTO:

```python
class CreateTenantCommandDTO:
    tenant_name: str
    external_id: str
    tenant_domain_host: str
    user_last_name: str
    user_first_name: str
    user_email: str

class CreateTenantResultDTO:
    tenant_id: UUID
    user_id: UUID
    user_email_id: UUID
    tenant_domain_id: UUID
    tenant_status: str
    user_status: str
    tenant_domain_host: str
```

Порты:

```python
class TenantRepositoryProtocol(Protocol):
    async def add(self, tenant: Tenant) -> None: ...
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None: ...
    async def get_by_name(self, name: str) -> Tenant | None: ...
    async def exists_by_external_id(self, external_id: str) -> bool: ...
    async def exists_by_name(self, name: str) -> bool: ...

class TenantDomainRepositoryProtocol(Protocol):
    async def add(self, domain: TenantDomain) -> None: ...
    async def get_by_id(self, domain_id: UUID) -> TenantDomain | None: ...
    async def get_by_host(self, host: str) -> TenantDomain | None: ...
    async def get_api_host_by_tenant_id(self, tenant_id: UUID) -> str | None: ...
    async def exists_by_host(self, host: str) -> bool: ...
```

Сервисы:

- [`TenantService.create_tenant(name, external_id)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/application/admin_onboarding/services/tenant_service.py)
- [`TenantDomainService.create_primary_domain(tenant_id, host)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/application/admin_onboarding/services/tenant_domain_service.py)

Use case:

- [`CreateTenantUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/application/admin_onboarding/use_cases/create_tenant.py)

### `request_context_by_host`

Назначение:

- внутренний use case для прикладных модулей
- возвращает уже валидный login-context

DTO:

```python
class GetTenantRequestContextByHostQueryDTO:
    host: str

class TenantRequestContextDTO:
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    tenant_status: str
    domain_status: str
    api_host: str | None
```

Use case:

- [`GetTenantRequestContextByHostUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/application/request_context_by_host/use_case.py)

Контракт поведения:

- если host пустой или tenant/domain не найден -> `TenantHostNotFoundError`
- если tenant/domain не допускают login -> `TenantLoginUnavailableError`
- если всё валидно -> `TenantRequestContextDTO`

### `resolve_tenant_by_host`

Назначение:

- внешний read-model для UI
- не бросает ошибки для обычного `not_found`, а возвращает read-model

DTO:

```python
class ResolveTenantByHostQueryDTO:
    host: str

class ResolveTenantByHostResultDTO:
    exists: bool
    available: bool
    status: str
    tenant_id: UUID | None
    api_host: str | None
```

Use case:

- [`ResolveTenantByHostUseCase.execute(dto)`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/application/resolve_tenant_by_host/use_case.py)

## Infrastructure

Файлы:

- [`src/modules/tenancy/infrastructure/persistence/tenant.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/infrastructure/persistence/tenant.py)
- [`src/modules/tenancy/infrastructure/persistence/tenant_domain.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/infrastructure/persistence/tenant_domain.py)
- [`src/modules/tenancy/infrastructure/repositories.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/infrastructure/repositories.py)

Репозитории:

- `SqlAlchemyTenantRepository`
- `SqlAlchemyTenantDomainRepository`

## Presentation

Роуты:

- [`POST /api/admin/create-tenant`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/presentation/api/admin_tenants.py)
- [`GET /api/console/tenants/resolve`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/tenancy/presentation/api/console_tenants.py)

Схемы request/response вынесены в:

- `presentation/api/requests/*`
- `presentation/api/responses/*`

DI:

- repositories -> `presentation/depends/repositories.py`
- services -> `presentation/depends/services.py`
- use cases -> `presentation/depends/use_cases.py`
- control-plane auth -> `presentation/depends/control_plane_auth.py`

## Что может использовать внешний модуль

Если другому bounded context нужен tenant-context по host, он должен использовать application use case / port-adapter, а не напрямую читать tenancy ORM.
