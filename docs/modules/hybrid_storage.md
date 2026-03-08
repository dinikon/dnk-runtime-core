# Hybrid Storage, CRM, Universal Access, Access Control

## Цель

Зафиксировать архитектуру для следующего этапа проекта:

- control-plane данные остаются в `public` schema PostgreSQL;
- client/business данные tenant живут в отдельной schema;
- при создании `Tenant` создается tenant schema и запись в `public.data_sourses`;
- следующими прикладными модулями становятся `crm`, `universal_access`, `access_control`.

Ниже я использую доменное имя `DataSource`, но имя таблицы оставляю как `public.data_sourses`, потому что оно задано в текущем требовании. Если `data_sourses` было опечаткой, исправить это лучше до первой production-миграции.

## Граница хранения

### `public` schema

В `public` лежат control-plane данные:

- `tenants`
- `tenant_domains`
- `data_sourses`
- `users`
- `user_emails`
- пользовательские UI preferences
- tenant-level UI config, если это настройки tenant, а не конкретного user
- роли, политики и назначения доступа для `access_control`

### tenant schema

В tenant schema лежат бизнес-данные tenant:

- `crm.deals` и связанные CRM-таблицы
- будущие tenant-scoped таблицы `catalog`
- будущие tenant-scoped таблицы `org`

## Bounded Contexts

### `shared`

`shared` не владеет бизнес-сущностями. Здесь остаются только технические механизмы:

- `PublicBase` и `TenantBase`
- engine/session factory
- schema-aware SQLAlchemy helpers
- `UoW`
- host extraction
- token storage

Важно: полноценную авторизацию нельзя развивать в `shared.access`. Текущий `AllowAllAuthorizationService` должен остаться временной заглушкой или быть удален после ввода `access_control`.

### `tenancy`

`tenancy` владеет:

- `Tenant`
- `TenantDomain`
- `TenantDataSource`
- lifecycle создания tenant
- mapping tenant -> schema/DSN
- resolve tenant по `host`
- выдачей tenant data access context для бизнес-модулей

Почему `DataSource` должен жить именно в `tenancy`:

- он создается вместе с tenant;
- он описывает физическое размещение tenant data;
- он нужен всем tenant-bound модулям как source of truth для маршрутизации к данным;
- это control-plane метаданные, а не CRM-доменные данные.

### `identity`

`identity` остается владельцем:

- `User`
- `UserEmail`
- login/session flow
- user-level UI preferences

`identity` не должен знать, как устроены `Deal` и права на строки/колонки. Его ответственность заканчивается на идентификации пользователя и выдаче actor context.

### `crm`

`crm` владеет:

- `Deal`
- бизнес-инвариантами сделок
- CRM read/write use cases

`crm` не должен владеть:

- tenant routing;
- generic CRUD API для всех сущностей;
- ролями и политиками доступа.

### `universal_access`

`universal_access` не владеет бизнес-правилами `Deal`.

Его роль:

- единая generic facade для работы с сущностями;
- registry entity handlers;
- типовые операции `list/get/create/update/delete`;
- единый контракт для UI/grid/form слоев.

`universal_access` должен делегировать доменную логику в модуль-владелец сущности, например в `crm`.

### `access_control`

`access_control` владеет:

- ролями;
- permission grants;
- CRUD-решениями;
- row-level filters;
- column-level allow/deny правилами;
- policy evaluation.

`access_control` хранит control-plane метаданные в `public`, но применяет их к запросам в tenant schema.

## Ключевые архитектурные решения

### 1. Разделить metadata для public и tenant таблиц

Текущий проект использует один `Base.metadata`. Для гибридного хранения лучше разделить ORM bases:

```python
TENANT_SCHEMA_ALIAS = "tenant"


class PublicBase(DeclarativeBase):
    metadata = MetaData()


class TenantBase(DeclarativeBase):
    metadata = MetaData(schema=TENANT_SCHEMA_ALIAS)
```

Тогда:

- `PublicBase.metadata.create_all()` создает public-таблицы;
- `TenantBase.metadata.create_all()` можно вызывать для новой schema через `schema_translate_map`.

### 2. MVP должен опираться на local schema в одном PostgreSQL

Первый этап стоит ограничить так:

- `type = "postgresql"`
- `is_remote = false`
- `dsn` указывает на тот же PostgreSQL instance, где живет `public`
- tenant data хранятся в отдельной schema

Причина: это сохраняет один connection boundary и не ломает текущую идею "`один request = один UoW`".

`is_remote = true` имеет смысл заложить в модель и интерфейсы, но не реализовывать как полноценный cross-database transaction flow в первой итерации.

### 3. Schema name должен быть стабильным и не зависеть от display-name

Рекомендуемый формат:

```python
def build_tenant_schema_name(tenant_id: UUID) -> str:
    return f"tenant_{tenant_id.hex}"
```

Не стоит делать schema name из `tenant.name` или `external_id`:

- там будут коллизии;
- там возможны спецсимволы и rename-сценарии;
- это ухудшит миграции и сопровождение.

### 4. `universal_access` не заменяет предметные use cases

Generic CRUD нужен для типовых UI-сценариев. Но если у `Deal` появятся:

- переходы по stage;
- сложные правила суммы;
- автоматические пересчеты;
- внешние интеграции;

то это должны оставаться отдельные use cases внутри `crm`.

## Целевой flow создания tenant

```text
POST /api/admin/create-tenant
  -> tenancy.CreateTenantUseCase
  -> TenantService.create_tenant(...)
  -> TenantDomainService.create_primary_domain(...)
  -> TenantSchemaProvisioner.create_schema(schema)
  -> TenantDataSourceService.register_primary_data_source(...)
  -> identity provisioning.create_tenant_admin(...)
  -> UoW.commit()
```

Для MVP порядок операций должен быть таким:

1. создать `Tenant`;
2. создать primary `TenantDomain`;
3. вычислить schema name;
4. создать schema в PostgreSQL;
5. записать `public.data_sourses`;
6. создать первого admin user;
7. закоммитить транзакцию.

Если шаги 4-6 падают, onboarding должен завершаться ошибкой без частично зарегистрированного tenant.

## Backlog задач

### Этап 1. Фундамент hybrid storage

1. Разделить ORM base на `PublicBase` и `TenantBase`.
2. Обновить `src/modules/persistence.py`, чтобы отдельно регистрировать public-модели и tenant-модели.
3. Добавить технический helper для `schema_translate_map`.
4. Добавить в `tenancy` сущность `TenantDataSource`.
5. Добавить ORM-модель `public.data_sourses`.
6. Добавить repository и service для регистрации data source.
7. Добавить port/adaptor для создания tenant schema.
8. Расширить `CreateTenantUseCase`, чтобы он создавал schema и `data_sourses`.
9. Расширить admin response, если нужно вернуть `data_source_id` и `schema`.

### Этап 2. Tenant data access context

1. Добавить в `tenancy` отдельный use case для получения business data context по `host`.
2. В result DTO вернуть:
   - `tenant_id`
   - `host`
   - `data_source_id`
   - `dsn`
   - `schema`
   - `is_remote`
   - `type`
3. Добавить технический resolver, который строит tenant-aware session.
4. Для MVP разрешить только `is_remote = false`.

### Этап 3. CRM / Deal

1. Описать domain `Deal`.
2. Добавить tenant-scoped ORM-модель `DealModel` на `TenantBase`.
3. Реализовать repository и базовые use cases CRUD.
4. Поднять first-class HTTP API для `Deal`.
5. Подготовить adapter в `crm`, который сможет быть вызван из `universal_access`.

### Этап 4. Universal Access

1. Сделать entity registry.
2. Добавить generic DTO для list/get/create/update/delete.
3. Добавить entity handler protocol.
4. Подключить `Deal` как первую сущность в registry.
5. Добавить generic endpoints для UI.

### Этап 5. Access Control

1. Спроектировать роли и grants в `public`.
2. Реализовать CRUD decision engine.
3. Реализовать row-level filters.
4. Реализовать column-level access rules.
5. Подключить `access_control` к `crm` и `universal_access`.

### Этап 6. Тесты и эксплуатация

1. Покрыть onboarding tenant со schema creation.
2. Покрыть tenant routing в CRM.
3. Покрыть generic CRUD через `universal_access`.
4. Покрыть deny/read-only сценарии для `access_control`.
5. Добавить PostgreSQL integration tests, потому что SQLite не проверяет поведение schema-level multi-tenancy.

## Каркас по модулям

### `src/modules/shared`

```text
shared/
  db/
    base.py
    helper.py
    tenant_schema.py
  depends/
    uow.py
```

Каркас:

```python
TENANT_SCHEMA_ALIAS = "tenant"


def build_schema_translate_map(schema: str) -> dict[str, str]: ...


class DatabaseHelper:
    async def create_public_all(self) -> None: ...
    async def create_tenant_all(self, schema: str) -> None: ...
    async def create_schema(self, schema: str) -> None: ...
```

Замечание: DDL для tenant schema можно оставить за port/adaptor внутри `tenancy`, а в `shared.db` держать только технические примитивы.

### `src/modules/tenancy`

```text
tenancy/
  application/
    admin_onboarding/
      dto.py
      ports/
        identity.py
        repositories.py
        storage.py
      services/
        tenant_service.py
        tenant_domain_service.py
        tenant_data_source_service.py
        tenant_schema_name_service.py
      use_cases/
        create_tenant.py
    data_access_context_by_host/
      dto.py
      use_case.py
  domain/
    entities.py
    errors.py
    value_objects/
      tenant_status.py
      tenant_service_type.py
      data_source_type.py
  infrastructure/
    persistence/
      tenant.py
      tenant_domain.py
      data_source.py
    repositories.py
    schema_provisioner.py
  presentation/
    depends/
      repositories.py
      services.py
      use_cases.py
    api/
      admin_tenants.py
      requests/
      responses/
```

Каркас domain:

```python
@dataclass(slots=True)
class TenantDataSource:
    id: UUID
    tenant_id: UUID
    type: str
    is_remote: bool
    dsn: str
    schema: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create_primary(
        cls,
        *,
        tenant_id: UUID,
        dsn: str,
        schema: str,
        is_remote: bool = False,
        source_type: str = "postgresql",
    ) -> "TenantDataSource": ...
```

Каркас application ports:

```python
class TenantDataSourceRepositoryProtocol(Protocol):
    async def add(self, data_source: TenantDataSource) -> None: ...
    async def get_by_tenant_id(self, tenant_id: UUID) -> TenantDataSource | None: ...
    async def exists_by_schema(self, schema: str) -> bool: ...


class TenantSchemaProvisionerProtocol(Protocol):
    async def create_schema(self, schema: str) -> None: ...
    async def schema_exists(self, schema: str) -> bool: ...
```

Каркас services/use cases:

```python
class TenantSchemaNameService:
    def build(self, tenant_id: UUID) -> str: ...


class TenantDataSourceService:
    async def register_primary_data_source(
        self,
        *,
        tenant_id: UUID,
        dsn: str,
        schema: str,
        is_remote: bool = False,
        source_type: str = "postgresql",
    ) -> TenantDataSource: ...


class CreateTenantUseCase:
    async def execute(self, dto: CreateTenantCommandDTO) -> CreateTenantResultDTO: ...


class GetTenantDataAccessContextByHostUseCase:
    async def execute(
        self,
        dto: GetTenantDataAccessContextByHostQueryDTO,
    ) -> TenantDataAccessContextDTO: ...
```

### `src/modules/identity`

Структуру модуля сильно менять не нужно.

Изменения минимальные:

- оставить `User` и `UserEmail` в `public`;
- сохранить UI preferences в `identity`, если они принадлежат user;
- при необходимости расширить actor context, который потом потребляет `access_control`.

Каркас actor context:

```python
@dataclass(frozen=True, slots=True)
class ActorContextDTO:
    user_id: UUID
    tenant_id: UUID
    email: str
```

### `src/modules/crm`

```text
crm/
  application/
    deals/
      dto.py
      ports/
        repositories.py
        tenant_data_context.py
        access_control.py
      use_cases/
        create_deal.py
        get_deal.py
        list_deals.py
        update_deal.py
        delete_deal.py
  domain/
    entities.py
    errors.py
    value_objects/
      deal_status.py
  infrastructure/
    persistence/
      deal.py
    repositories.py
    universal_access.py
  presentation/
    depends/
      repositories.py
      use_cases.py
    api/
      deals.py
      requests/
      responses/
```

Каркас domain:

```python
@dataclass(slots=True)
class Deal:
    id: UUID
    tenant_id: UUID
    title: str
    status: str
    amount: Decimal | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        title: str,
        amount: Decimal | None,
    ) -> "Deal": ...

    def rename(self, title: str) -> None: ...
    def change_status(self, status: str) -> None: ...
    def change_amount(self, amount: Decimal | None) -> None: ...
```

Каркас repository/use cases:

```python
class DealRepositoryProtocol(Protocol):
    async def add(self, deal: Deal) -> None: ...
    async def get_by_id(self, deal_id: UUID) -> Deal | None: ...
    async def list(self, query: ListDealsQueryDTO) -> list[Deal]: ...
    async def save(self, deal: Deal) -> None: ...
    async def delete(self, deal_id: UUID) -> None: ...


class CreateDealUseCase:
    async def execute(self, dto: CreateDealCommandDTO) -> DealDTO: ...


class ListDealsUseCase:
    async def execute(self, dto: ListDealsQueryDTO) -> ListDealsResultDTO: ...
```

### `src/modules/universal_access`

```text
universal_access/
  application/
    entities/
      dto.py
      ports/
        entity_handler.py
        access_control.py
      use_cases/
        describe_entity.py
        list_records.py
        get_record.py
        create_record.py
        update_record.py
        delete_record.py
  domain/
    entity/
      entity_definition.py
      entity_field.py
    value_object/
      entity_code.py
  infrastructure/
    registry.py
  presentation/
    depends/
      registry.py
      use_cases.py
    api/
      entities.py
      requests/
      responses/
```

Каркас протоколов:

```python
class EntityHandlerProtocol(Protocol):
    entity_code: str

    async def describe(self) -> EntityDefinition: ...
    async def list(self, dto: ListEntityRecordsQueryDTO) -> ListEntityRecordsResultDTO: ...
    async def get(self, dto: GetEntityRecordQueryDTO) -> EntityRecordDTO: ...
    async def create(self, dto: CreateEntityRecordCommandDTO) -> EntityRecordDTO: ...
    async def update(self, dto: UpdateEntityRecordCommandDTO) -> EntityRecordDTO: ...
    async def delete(self, dto: DeleteEntityRecordCommandDTO) -> None: ...


class EntityHandlerRegistry:
    def register(self, handler: EntityHandlerProtocol) -> None: ...
    def get(self, entity_code: str) -> EntityHandlerProtocol: ...
```

Рекомендация:

- `universal_access` работает через registry;
- `crm` регистрирует `DealEntityHandler`;
- сложные предметные операции в generic layer не дублируются.

### `src/modules/access_control`

```text
access_control/
  application/
    policies/
      dto.py
      ports/
        repositories.py
      use_cases/
        authorize_crud.py
        build_row_filter.py
        get_allowed_columns.py
  domain/
    entities.py
    errors.py
    value_objects/
      access_action.py
      access_effect.py
      access_scope.py
  infrastructure/
    persistence/
      role.py
      policy.py
      subject_role.py
    repositories.py
  presentation/
    depends/
      repositories.py
      use_cases.py
```

Каркас решений:

```python
@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class RowAccessFilter:
    sql_predicate: str | None
    params: dict[str, object]


@dataclass(frozen=True, slots=True)
class ColumnAccessDecision:
    readable: set[str]
    writable: set[str]
```

Каркас use cases:

```python
class AuthorizeCrudUseCase:
    async def execute(self, dto: AuthorizeCrudCommandDTO) -> AccessDecision: ...


class BuildRowFilterUseCase:
    async def execute(self, dto: BuildRowFilterQueryDTO) -> RowAccessFilter: ...


class GetAllowedColumnsUseCase:
    async def execute(
        self,
        dto: GetAllowedColumnsQueryDTO,
    ) -> ColumnAccessDecision: ...
```

## Связи между модулями

Рекомендуемая зависимость по направлению:

```text
presentation -> application -> domain
                          -> ports
infrastructure -> adapters/repositories -> application ports
```

Межмодульно:

- `crm` использует `tenancy` только через tenant data context port;
- `crm` использует `access_control` только через application port;
- `universal_access` использует registry handlers, а не ORM `crm` напрямую;
- `identity` не читает tenant ORM-модели напрямую;
- `access_control` не должен владеть CRUD логикой `Deal`.

## Риски и ограничения

### 1. SQLite не является репрезентативным для schema-based multi-tenancy

Текущие тесты проекта завязаны на SQLite. Для hybrid storage этого недостаточно.

Нужно разделить тесты:

- unit tests: можно оставлять на SQLite;
- integration tests для schema provisioning и tenant routing: только PostgreSQL.

### 2. Remote data sources не стоит полноценно делать в первой поставке

Как только `is_remote = true` начинает реально использоваться, появляются:

- отдельные engines/session factories;
- отдельные transaction boundaries;
- невозможность простого atomic commit между public и remote tenant DB;
- необходимость compensation/saga механики.

Поэтому первая поставка должна закрыть только:

- `public` + tenant schema в одном PostgreSQL;
- `is_remote = false`.

### 3. Generic CRUD легко начинает размывать доменную модель

Если `universal_access` начнет сам принимать решения по `Deal`, это быстро разрушит bounded context `crm`.

Правильное правило:

- generic layer описывает формат работы;
- модуль-владелец сущности описывает смысл и инварианты.

## Рекомендуемый порядок реализации

1. `shared.db`: разделение public/tenant metadata.
2. `tenancy`: `TenantDataSource` + schema provisioning + onboarding update.
3. `tenancy`: `GetTenantDataAccessContextByHostUseCase`.
4. `crm`: `Deal` + tenant ORM + CRUD use cases.
5. `access_control`: CRUD decision engine.
6. `universal_access`: registry + generic CRUD.
7. Интеграция `crm` <-> `access_control` <-> `universal_access`.
