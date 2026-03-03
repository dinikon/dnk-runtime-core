# Shared Module

## Ответственность

`src/modules/shared` содержит только технические, переиспользуемые компоненты. Здесь не должно быть предметной логики tenancy, identity, crm и других bounded contexts.

## Подмодули

### `shared.db`

Файлы:

- [`src/modules/shared/db/base.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/db/base.py)
- [`src/modules/shared/db/helper.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/db/helper.py)

Отвечает за:

- `DeclarativeBase`
- `PortableJSON`
- создание engine
- `session_factory`
- `create_all()`
- `dispose()`

### `shared.uow`

Файлы:

- [`src/modules/shared/uow.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/uow.py)
- [`src/modules/shared/depends/uow.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/depends/uow.py)

Контракт:

```python
class UnitOfWorkProtocol(Protocol):
    session: AsyncSession
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

Роль:

- request-scoped SQLAlchemy session boundary
- один request = один `UnitOfWork`

### `shared.http`

Файл:

- [`src/modules/shared/http/host.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/http/host.py)

Методы:

```python
def normalize_host(host: str) -> str
def extract_request_host(request: Request) -> str
```

Роль:

- единая нормализация host
- единый способ извлечения host из `Request`

Dependency:

- [`src/modules/shared/depends/request_host.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/depends/request_host.py)

```python
def get_request_host(request: Request) -> str
RequestHostDep = Annotated[str, Depends(get_request_host)]
```

### `shared.tokens`

Файлы:

- [`src/modules/shared/tokens/manager.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens/manager.py)
- [`src/modules/shared/tokens/protocols.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens/protocols.py)
- [`src/modules/shared/tokens/in_memory_adapter.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens/in_memory_adapter.py)
- [`src/modules/shared/tokens/redis_repository.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens/redis_repository.py)
- [`src/modules/shared/tokens/redis_adapter.py`](/Users/inikon/PycharmProjects/dnk-runtime-core/src/modules/shared/tokens/redis_adapter.py)

Контракт backend:

```python
class TokenBackendProtocol(Protocol):
    async def set(self, key: str, value: StoredToken) -> None: ...
    async def get(self, key: str) -> StoredToken | None: ...
    async def delete(self, key: str) -> None: ...
```

Контракт manager:

```python
class TokenManager:
    async def set_token(...)
    async def exists(...)
    async def get_token(...)
    async def invalidate(...)
    async def consume_token(...)
```

Роль:

- техническое token/session storage API
- не содержит бизнес-правил auth
- используется `identity` через порты `OtpChallengeStorePort` и `SessionStorePort`

## Что нельзя класть в `shared`

- правила tenant lifecycle
- правила user login
- бизнес-ограничения CRM / Catalog / Org
- доменные сущности bounded context'ов
