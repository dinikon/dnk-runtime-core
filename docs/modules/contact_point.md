# Contact Point Module

## Purpose

`contact_point` хранит tenant-scoped реестр контактных точек и их привязок к runtime-записям владельцев. Модуль
нормализует `EMAIL` и украинские `PHONE` значения, хеширует нормализованное значение и переиспользует уже существующий
`ContactPointEntity` внутри tenant schema по паре `contact_point_type` + `normalized_hash`.

Модуль является runtime-data module: собственных статических ORM-таблиц не найдено. Хранение идет через runtime objects
`contact_point` и `contact_point_binding`, описанные seed metadata в
`src/modules/schema_registry/seed/contexts/contact_point.py`.

## Current Scope

Текущая реализация покрывает два связанных subdomain:

- `contact_point`: нормализованное значение канала связи (`EMAIL` или `PHONE`) с исходным значением и SHA-256 hash.
- `binding`: soft-active связь контактной точки с произвольной runtime owner record через `owner_object_id` и
  `owner_record_id`.

Что модуль делает сейчас:

- проверяет существование owner record через runtime descriptor и runtime query gateway;
- проверяет, что для owner object включена object feature `CONTACT_POINT`;
- создает или переиспользует контактную точку;
- создает, реактивирует или идемпотентно возвращает binding;
- поддерживает один primary binding на owner + contact point type;
- soft-detach-ит binding и при необходимости назначает следующий active binding primary.
- читает одну contact point по id;
- листит contact points с фильтром по type и pagination;
- листит active contact points владельца с metadata binding;
- листит bindings с диагностическими фильтрами по type/contact point/owner/active state.
- выбирает active contact point владельца для delivery channel через application-level selection service.

В текущей реализации не найдено:

- describe fields / metadata endpoints;
- hard delete или cleanup orphan contact points;
- отдельные background jobs, event handlers, consumers, management commands, CLI commands, outbox/inbox или queues.

## Public Functionality

- привязать `EMAIL` или `PHONE` contact point к runtime owner record;
- нормализовать email к lowercase trimmed виду;
- нормализовать украинский телефон к формату `+380XXXXXXXXX`;
- переиспользовать существующий contact point по normalized hash;
- повторно активировать ранее detached binding;
- сделать binding primary явно или автоматически, если у owner/type нет active primary;
- soft-detach binding по `binding_id`;
- вернуть признак orphan contact point после detach без удаления самого contact point.
- получить contact point без internal `normalized_hash`;
- получить active contact points владельца вместе с `binding_id`, `is_primary`, `is_active`, `detached_at`;
- получить список bindings, включая inactive bindings при `is_active` filter.
- выбрать recipient address для канала `SMS`, `VIBER` или `EMAIL` по strategy `primary`, `last_active`,
  `all_active`, `explicit_contact_point`.

## Main Flows / Use Cases

| Use Case                       | Input                          | Output                                                      | Description                                                                                                                                     |
|--------------------------------|--------------------------------|-------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `AttachContactPointUseCase`    | `AttachContactPointCommand`    | `AttachContactPointResultDTO`                               | Проверяет owner и feature gate, нормализует и хеширует значение, создает/переиспользует `ContactPointEntity`, создает/реактивирует binding.     |
| `DetachContactPointUseCase`    | `DetachContactPointCommand`    | `DetachContactPointResultDTO`                               | Загружает binding, soft-deactivate через `detach`, назначает следующий active binding primary при отсутствии primary, contact point не удаляет. |
| `ContactPointSelectionService` | `ContactPointSelectionCommand` | `ContactPointSelectionDTO` / `ContactPointSelectionListDTO` | Мапит delivery channel в contact point type и выбирает active binding по strategy.                                                              |

## Domain Model

### `ContactPointEntity`

- ID: `ContactPointIdVO`, наследник `EntityIdVO`.
- Tenant scope: tenant не хранится в entity; `tenant_id` передается снаружи в repository/use case как `EntityIdVO`.
- Fields: `id`, `created_at`, `updated_at`, `contact_point_type`, `raw_value`, `normalized_value`, `hash_value`.
- Value Objects:
    - `ContactPointIdVO`;
    - `ContactPointTypeVO` со значениями `PHONE`, `EMAIL`.
- Factory methods: `ContactPointEntity.create(...)` выставляет одинаковые `created_at` и `updated_at`.
- Update methods: в текущей реализации не найдено.
- Domain errors:
    - `ContactPointNotFoundError`;
    - `ContactPointValidationError`;
    - `InvalidContactPointValueError`;
    - `UnsupportedContactPointTypeError`.
- Invariants:
    - уникальность contact point фактически обеспечивается runtime seed index `uniq_contact_point_type_hash` на
      `contact_point_type` + `normalized_hash`;
    - entity сама не валидирует `raw_value`, `normalized_value` и `hash_value`; нормализация и hash вынесены в
      infrastructure services.

### `ContactPointBindingEntity`

- ID: `ContactPointBindingIdVO`, наследник `EntityIdVO`.
- Tenant scope: tenant не хранится в entity; `tenant_id` передается снаружи в repository/use case как `EntityIdVO`.
- Fields: `id`, `created_at`, `updated_at`, `contact_point_id`, `contact_point_type`, `owner`, `is_primary`,
  `detached_at`, `is_active`.
- Value Objects:
    - `ContactPointBindingIdVO`;
    - `OwnerContactPointBinding(owner_object_id, owner_record_id)`;
    - `ContactPointIdVO`;
    - `ContactPointTypeVO`.
- Factory methods: `ContactPointBindingEntity.create(...)` создает active binding с `detached_at=None`.
- Update methods:
    - `reactivate(...)` возвращает binding в active state, очищает `detached_at`, обновляет `is_primary`;
    - `detach(...)` делает binding inactive, снимает primary, выставляет `detached_at`;
    - `mark_primary(...)`;
    - `unmark_primary(...)`.
- Domain errors:
    - `ContactPointBindingNotFoundError`;
    - `ContactPointOwnerNotFoundError`.
- Invariants:
    - один binding на `contact_point_id` + `owner_object_id` + `owner_record_id` закреплен seed index
      `uniq_cpb_point_owner`;
    - правило "один primary на owner + type" поддерживается use case/repository методом
      `unset_primary_for_owner_and_type`, а не отдельным unique index в seed.

## Application Layer

### Commands

Все command classes оформлены как `@dataclass(frozen=True, slots=True)`:

- `AttachContactPointCommand`: `tenant_id`, `owner_object_id`, `owner_record_id`, `contact_point_type`, `raw_value`,
  `is_primary=False`.
- `DetachContactPointCommand`: `tenant_id`, `binding_id`.

### Queries

Все query classes оформлены как `@dataclass(frozen=True, slots=True)`:

- `GetContactPointQuery`: `tenant_id`, `contact_point_id`.
- `ListContactPointsQuery`: `tenant_id`, optional `contact_point_type`, `limit`, `offset`.
- `ListOwnerContactPointsQuery`: `tenant_id`, `owner_object_id`, `owner_record_id`, optional
  `contact_point_type`, `limit`, `offset`.
- `ListContactPointBindingsQuery`: `tenant_id`, optional `contact_point_type`, `contact_point_id`,
  `owner_object_id`, `owner_record_id`, `is_active`, `limit`, `offset`.
- `ContactPointSelectionCommand`: `tenant_id`, `owner_object_id`, `owner_record_id`, `channel_code`,
  `strategy`, optional `explicit_contact_point_id`.

### DTOs

Все DTO classes оформлены как `@dataclass(frozen=True, slots=True)`:

- `AttachContactPointResultDTO`: `contact_point_id`, `binding_id`, `contact_point_created`, `binding_created`,
  `already_attached`.
- `DetachContactPointResultDTO`: `contact_point_id`, `binding_id`, `binding_deleted`, `contact_point_deleted`,
  `contact_point_left_orphan`.
- `ContactPointDTO`: `id`, `created_at`, `updated_at`, `contact_point_type`, `raw_value`, `normalized_value`.
- `ContactPointListDTO`: `items`, `count`, `limit`, `offset`.
- `OwnerContactPointDTO`: contact point fields plus `binding_id`, `is_primary`, `is_active`, `detached_at`.
- `OwnerContactPointListDTO`: `items`, `count`, optional `limit`, `offset`.
- `ContactPointBindingDTO`: binding fields plus `contact_point_type`.
- `ContactPointBindingListDTO`: `items`, `count`, `limit`, `offset`.
- `ContactPointSelectionDTO`: selected `contact_point_id`, `recipient_address`, `recipient_snapshot`,
  `binding_id`, `contact_point_type`, `is_primary`.
- `ContactPointSelectionListDTO`: `items`, `count`.

DTO возвращают UUID на application boundary. HTTP Pydantic schemas остаются в presentation layer.

### Ports

- `OwnerResolverPort`: проверяет существование owner runtime record.
- `ContactPointObjectFeatureGatePort`: проверяет включенность object feature `CONTACT_POINT`.
- `ContactPointNormalizerPort`: нормализует raw contact point value.
- `ContactPointHashPort`: считает hash нормализованного значения.
- `ContactPointSelectionPort`: application-level порт выбора recipient address для будущих bulk-send orchestration modules.
- `ContactPointSelectionRepositoryProtocol`: selection reads для active primary, last active, all active и explicit
  active owner binding.

### Use Cases

- `AttachContactPointUseCase` использует `ContactPointRepositoryProtocol`, `ContactPointBindingRepositoryProtocol`,
  `OwnerResolverPort`, `ContactPointObjectFeatureGatePort`, `ContactPointNormalizerPort`, `ContactPointHashPort`,
  `UuidPort` и `ClockPort`.
- `DetachContactPointUseCase` использует `ContactPointBindingRepositoryProtocol` и `ClockPort`.
- `GetContactPointUseCase` читает одну contact point и мапит отсутствующую запись в `ContactPointNotFoundError`.
- `ListContactPointsUseCase` делегирует query repository.
- `ListOwnerContactPointsUseCase` проверяет owner existence и feature gate, затем возвращает active bindings.
- `ListContactPointBindingsUseCase` делегирует query repository и может вернуть active/inactive bindings.
- `ContactPointSelectionService` поддерживает mapping `SMS`/`VIBER` -> `PHONE`, `EMAIL` -> `EMAIL`; `PUSH`,
  `CUSTOM` и unknown channels возвращают typed unsupported-channel error.

`AttachContactPointUseCase` сначала проверяет owner existence, затем feature gate, затем нормализует значение и ищет
contact point по type/hash. Если contact point не найден, он создается с новым UUID. Binding ищется по owner +
contact_point_id. Active binding возвращается идемпотентно; inactive binding реактивируется; новый binding создается
при отсутствии существующего. Если `is_primary=True` или у owner/type нет active primary, остальные primary bindings
для owner/type снимаются.

`DetachContactPointUseCase` загружает binding по `binding_id`. Если binding уже inactive, use case не меняет состояние
и возвращает `binding_deleted=False`. Active binding переводится в inactive state. Если после detach у owner/type нет
active primary, первый active binding по сортировке `created_at asc`, `id asc` становится primary. Contact point не
удаляется: `contact_point_deleted=False`.

### Repository Protocols

- `ContactPointRepositoryProtocol`:
    - `load_contact_point`;
    - `get_by_type_and_hash`;
    - `save_contact_point`.
- `ContactPointBindingRepositoryProtocol`:
    - `load_binding`;
    - `find_by_owner_and_contact_point`;
    - `find_first_active_by_owner_and_type`;
    - `find_active_primary_by_owner_and_type`;
    - `unset_primary_for_owner_and_type`;
    - `has_active_bindings_for_contact_point`;
    - `save_binding`.
- `OwnerContactPointQueryRepositoryProtocol`:
    - `get_contact_point`;
    - `list_contact_points`;
    - `list_owner_contact_points`;
    - `list_contact_point_bindings`.

## Infrastructure / Persistence

### `ContactPointRuntimeRepository`

- File: `src/modules/contact_point/infrastructure/runtime_repository.py`.
- Implements: `ContactPointRepositoryProtocol`, `ContactPointBindingRepositoryProtocol`.
- Storage: `runtime_data` через `RuntimeCommandGateway` и `RuntimeQueryGateway`.
- Runtime objects:
    - `_CONTACT_POINT = "contact_point"`;
    - `_CONTACT_POINT_BINDING = "contact_point_binding"`.
- Tenant handling: repository не хранит tenant в instance; каждый public method принимает `tenant_id: EntityIdVO` и
  резолвит descriptor через `RuntimeObjectResolverProtocol`.
- Mapping:
    - `contact_point_entity(row)` мапит runtime row в `ContactPointEntity`;
    - `contact_point_binding_entity(row)` мапит runtime row в `ContactPointBindingEntity`;
    - runtime field `normalized_hash` мапится в entity field `hash_value`;
    - UUID, datetime, optional datetime, string и bool проверяются явно.
- Write behavior:
    - `save_contact_point` делает insert/update по наличию строки в runtime gateway;
    - `save_binding` делает insert/update по наличию строки в runtime gateway;
    - `unset_primary_for_owner_and_type` вызывает `update_where` с filters по owner/type/active/primary;
    - list lookups используют `RuntimeTypedFilterBuilder`, `PageSpec(limit=1, offset=0)` и иногда `SortSpec`.
- Errors:
    - `ContactPointNotFoundError`, если update contact point вернул `None`;
    - `ContactPointBindingNotFoundError`, если update binding вернул `None`;
    - `TypeError`, если runtime row содержит неожиданный тип;
    - runtime/schema errors не перехватываются в repository и мапятся выше в HTTP layer.

### `ContactPointNormalizeService`

- File: `src/modules/contact_point/infrastructure/services.py`.
- Implements: `ContactPointNormalizerPort`.
- `EMAIL`: trim + lowercase, затем regex `^[^@\s]+@[^@\s]+\.[^@\s]+$`.
- `PHONE`: оставляет только цифры и нормализует украинские номера:
    - `380XXXXXXXXX` -> `+380XXXXXXXXX`;
    - `0XXXXXXXXX` -> `+380XXXXXXXXX`;
    - `XXXXXXXXX` -> `+380XXXXXXXXX`.
- Errors:
    - `InvalidContactPointValueError` для невалидного email/phone;
    - `UnsupportedContactPointTypeError` для неподдержанного типа.

### `ContactPointHashService`

- File: `src/modules/contact_point/infrastructure/services.py`.
- Implements: `ContactPointHashPort`.
- Hash: `sha256(normalized_value.encode("utf-8")).hexdigest()`.

### `RuntimeOwnerResolver`

- File: `src/modules/contact_point/infrastructure/services.py`.
- Implements: `OwnerResolverPort`.
- Uses:
    - `RuntimeObjectResolverProtocol.resolve_by_id(...)` по `owner.owner_object_id`;
    - `RuntimeQueryGateway.get_by_id(...)` по `owner.owner_record_id`.
- Returns: `True`, если owner runtime row найден, иначе `False`.

### `SchemaRegistryContactPointObjectFeatureGate`

- File: `src/modules/contact_point/infrastructure/services.py`.
- Implements: `ContactPointObjectFeatureGatePort`.
- Uses: `AssertObjectFeatureEnabledUseCaseProtocol`.
- Feature code: `ObjectFeatureCode.CONTACT_POINT.value`.
- Проверяет feature для `owner_object_id`, преобразованного в `RuntimeObjectIdVO`.

### Runtime Seed

Source: `src/modules/schema_registry/seed/contexts/contact_point.py`.

- `contact_point` fields: `id`, `created_at`, `updated_at`, `contact_point_type`, `raw_value`, `normalized_value`,
  `normalized_hash`.
- `contact_point` indexes:
    - `uniq_contact_point_type_hash` on `contact_point_type`, `normalized_hash`, unique;
    - `idx_contact_point_hash` on `normalized_hash`.
- `contact_point_binding` fields: `id`, `created_at`, `updated_at`, `contact_point_id`, `contact_point_type`,
  `owner_object_id`, `owner_record_id`, `is_primary`, `is_active`, `detached_at`.
- `contact_point_binding` indexes:
    - `idx_cpb_owner`;
    - `idx_cpb_contact_point_id`;
    - `idx_cpb_owner_type`;
    - `uniq_cpb_point_owner`.
- Relation: `contact_point_bindings_contact_point`, `many_to_one`,
  `contact_point_binding.contact_point_id -> contact_point.id`, `on_delete="restrict"`.

## Presentation / HTTP API

Base prefix:

```text
/api
```

`src/modules/router.py` подключает `contact_point_router` под общим prefix `/api`. Controllers задают prefix
`/contact-points`.

| Method | Path                                                             | Controller                          | Use Case                          | Request                                                        | Response                                 |
|--------|------------------------------------------------------------------|-------------------------------------|-----------------------------------|----------------------------------------------------------------|------------------------------------------|
| `POST` | `/api/contact-points/attach`                                     | `attach_contact_point`              | `AttachContactPointUseCase`       | `AttachContactPointRequestSchema`                              | `AttachContactPointResponseSchema`       |
| `POST` | `/api/contact-points/detach`                                     | `detach_contact_point`              | `DetachContactPointUseCase`       | `DetachContactPointRequestSchema`                              | `DetachContactPointResponseSchema`       |
| `POST` | `/api/contact-points/list-by-record`                             | `list_owner_contact_points`         | `ListOwnerContactPointsUseCase`   | `ListOwnerContactPointsRequestSchema`                          | `ListOwnerContactPointsResponseSchema`   |
| `GET`  | `/api/contact-points/{id}`                                       | `get_contact_point`                 | `GetContactPointUseCase`          | path `id`                                                      | `ContactPointResponseSchema`             |
| `GET`  | `/api/contact-points`                                            | `list_contact_points`               | `ListContactPointsUseCase`        | query `contact_point_type`, `limit`, `offset`                  | `ListContactPointsResponseSchema`        |
| `GET`  | `/api/contact-points/owners/{owner_object_id}/{owner_record_id}` | `list_owner_contact_points_by_path` | `ListOwnerContactPointsUseCase`   | path owner ids + query `contact_point_type`, `limit`, `offset` | `ListOwnerContactPointsResponseSchema`   |
| `GET`  | `/api/contact-points/bindings`                                   | `list_contact_point_bindings`       | `ListContactPointBindingsUseCase` | query filters + `limit`, `offset`                              | `ListContactPointBindingsResponseSchema` |

All routes require `AuthenticatedRequestContextDep`. Controllers read `principal.tenant_id`, convert it to
`EntityIdVO`, and do not accept `tenant_id` from HTTP payloads.

`GET /api/contact-points` and owner/binding list endpoints use `limit` validation `1..100` and `offset >= 0`.
`GET /api/contact-points/{id}` intentionally does not expose `normalized_hash`.

HTTP error mapping:

- missing principal or tenant id -> `401 Unauthorized`;
- `ContactPointOwnerNotFoundError`, `ContactPointBindingNotFoundError`, `RuntimeObjectNotFoundError` -> `404`;
- `RuntimeDataPersistenceError`, `RuntimeDataPolicyError`, `RuntimeObjectDescriptorError`,
  `SchemaRegistryMetadataInconsistentError` -> `409`;
- `ContactPointValidationError`, `ObjectFeatureConfigNotFoundError`, `ObjectFeatureNotEnabledError`,
  `RuntimeDataValidationError`, `RuntimeDataFilterError`, generic `DomainError` -> `422`.

## Dependency Injection

- Infrastructure dependencies:
    - `get_runtime_field_type_policy` creates `RuntimeFieldTypePolicy`;
    - `get_runtime_query_gateway` creates `PostgresRuntimeQueryGateway` from `UoWDep.session`;
    - `get_runtime_command_gateway` creates `PostgresRuntimeCommandGateway` from `UoWDep.session` and query gateway;
    - `get_contact_point_repository` creates `ContactPointRuntimeRepository`;
    - `get_owner_resolver` creates `RuntimeOwnerResolver`;
    - `get_contact_point_object_feature_gate` creates `SchemaRegistryContactPointObjectFeatureGate`;
    - `get_contact_point_normalizer` creates `ContactPointNormalizeService`;
    - `get_contact_point_hash_service` creates `ContactPointHashService`.
- Application dependencies:
    - `get_attach_contact_point_use_case` injects the same runtime repository as contact point and binding repository,
      plus owner resolver, feature gate, normalizer, hash service, `UuidDep` and `ClockDep`;
  - `get_detach_contact_point_use_case` injects runtime repository as binding repository and `ClockDep`;
  - query use case dependencies inject the same runtime repository as `OwnerContactPointQueryRepositoryProtocol`.
- Shared dependencies:
    - `UoWDep`;
    - `ClockDep`;
    - `UuidDep`;
    - `AuthenticatedRequestContextDep`.
- Schema registry dependencies:
    - `RuntimeObjectResolverDep`;
    - `AssertObjectFeatureEnabledUseCaseDep`.

## Dependencies On Other Modules

| Module            | Layer                              | Used For                                                                                              |
|-------------------|------------------------------------|-------------------------------------------------------------------------------------------------------|
| `shared`          | domain/application/presentation    | `EntityIdVO`, `DomainError`, `ClockPort`/`ClockDep`, `UuidPort`/`UuidDep`, `UoWDep`, request context. |
| `runtime_data`    | infrastructure/presentation        | Runtime command/query gateways, typed filters, sorting, paging, type policy, runtime errors.          |
| `schema_registry` | infrastructure/presentation/tests  | Runtime object descriptor resolution, object feature gate `CONTACT_POINT`, seed metadata.             |
| owner modules     | infrastructure via runtime records | Owner records are addressed generically by runtime `owner_object_id` and `owner_record_id`.           |

## Events / Background Processing

В текущей реализации не найдено.

Не найдены event handlers, message consumers, scheduled jobs, management commands, CLI commands, outbox/inbox или queue
consumers внутри `src/modules/contact_point`.

## Tests Covering This Module

- Domain:
    - direct entity-only test file in current source tree was not found;
    - entity behavior is partially covered through `test/test_contact_point_application.py`.
- Application:
    - `test/test_contact_point_application.py` covers normalization/hash service behavior, attach idempotency,
      primary selection, reactivation, owner/feature failures, soft detach and primary promotion.
- Infrastructure:
    - `test/test_contact_point_runtime_repository.py` covers runtime repository filters, sorting and payload mapping;
    - direct tests for `RuntimeOwnerResolver` and `SchemaRegistryContactPointObjectFeatureGate` were not found.
- Presentation:
    - `test/test_contact_point_http_router.py` covers router endpoint registration, controller command/query mapping,
      tenant context handling, route ordering and HTTP error mapping.
- Integration / architecture / schema-related:
    - `test/test_contact_point_schema_seed.py` covers runtime seed objects, fields, indexes and relation;
    - `test/test_schema_registry_object_feature_*` covers object feature behavior for `CONTACT_POINT`;
    - `test/test_architecture_boundaries.py` checks schema_registry does not use legacy `CONTACT_POINTS` feature code.

Verification command used for the contact_point-specific source tests:

```bash
uv run python -m unittest test.test_contact_point_application test.test_contact_point_runtime_repository test.test_contact_point_http_router test.test_contact_point_schema_seed -v
```

## Known Gaps / Technical Debt

- `application` layer is flatter than the aggregate-oriented structure recommended by `docs/develop-style.md`.
- describe-fields HTTP API for contact points or bindings is not implemented.
- `DetachContactPointUseCase` returns orphan status but does not hard-delete or cleanup orphan contact points;
  `contact_point_deleted` is always `False` in current code.
- Direct tests for `RuntimeOwnerResolver` and `SchemaRegistryContactPointObjectFeatureGate` were not found.
- Domain entities do not contain value-level validation for raw/normalized/hash values; validation currently lives in
  infrastructure normalizer service.
- `ContactPointBindingEntity.unmark_primary(...)` is implemented but not used by current use cases.
- Runtime seed has no unique index that directly enforces one active primary binding per owner/type; this is handled by
  application/repository logic.

## Related Documentation

- [Develop Style](../develop-style.md)
- [HTTP API](../interfaces/http-api.md)

## Source Of Truth

- `docs/prompts/document-module-from-source.md`
- `docs/develop-style.md`
- `src/modules/router.py`
- `src/modules/contact_point/domain/contact_point/entity.py`
- `src/modules/contact_point/domain/contact_point/error.py`
- `src/modules/contact_point/domain/contact_point/repository.py`
- `src/modules/contact_point/domain/contact_point/value_object/`
- `src/modules/contact_point/domain/binding/entity.py`
- `src/modules/contact_point/domain/binding/error.py`
- `src/modules/contact_point/domain/binding/repository.py`
- `src/modules/contact_point/domain/binding/value_object/`
- `src/modules/contact_point/application/command/`
- `src/modules/contact_point/application/dto/`
- `src/modules/contact_point/application/ports.py`
- `src/modules/contact_point/application/use_case/`
- `src/modules/contact_point/infrastructure/row_mapper.py`
- `src/modules/contact_point/infrastructure/runtime_object_names.py`
- `src/modules/contact_point/infrastructure/runtime_repository.py`
- `src/modules/contact_point/infrastructure/services.py`
- `src/modules/contact_point/presentation/depends/`
- `src/modules/contact_point/presentation/http/`
- `src/modules/schema_registry/seed/contexts/contact_point.py`
- `test/test_contact_point_application.py`
- `test/test_contact_point_runtime_repository.py`
- `test/test_contact_point_http_router.py`
- `test/test_contact_point_schema_seed.py`
- `test/test_schema_registry_object_feature_*.py`
- `test/test_architecture_boundaries.py`
