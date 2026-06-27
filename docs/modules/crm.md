# CRM Module

## Purpose

`crm` - backend-модуль для tenant-scoped CRM-данных: контактов (`contact`) и компаний (`company`).
Модуль не владеет статическими ORM-таблицами CRM. Фактическое хранение идет через `runtime_data`, а описание
runtime-объектов и полей берется из `schema_registry`.

HTTP routes CRM подключаются через `src/modules/router.py`: общий router имеет prefix `/api`, а CRM router добавляет
предметные префиксы `/crm/contacts` и `/crm/companies`.

## Current Scope

Текущая реализация покрывает два близких subdomain внутри одного bounded context:

- `contact`: создание, получение по id, список, поиск по runtime filter/sort DSL, обновление имени/статуса/тегов,
  удаление, описание runtime-полей.
- `company`: создание, получение по id, список, обновление юридического названия, удаление, описание runtime-полей.
- Runtime seed для CRM находится в `src/modules/schema_registry/seed/contexts/crm.py`: объекты `contact` и `company`,
  а также many-to-many relation `contact_companies`.

В текущей реализации не найдено:

- отдельные domain services внутри `src/modules/crm/domain`;
- background jobs, event handlers, consumers, queues, outbox/inbox;
- HTTP endpoints для управления связью `contact_companies`.

## Public Functionality

- создать контакт текущего tenant;
- получить контакт по id;
- получить страницу контактов по `limit`/`offset`;
- выполнить поиск контактов через runtime-owned `filter`/`sort` DSL;
- обновить контакт: `first_name`, `last_name`, `middle_name`, `status`, `tags`;
- удалить контакт;
- получить описание CRM-модели `contact` и ее полей;
- создать компанию текущего tenant;
- получить компанию по id;
- получить страницу компаний по `limit`/`offset`;
- обновить `legal_name` компании;
- удалить компанию;
- получить описание CRM-модели `company` и ее полей.

## Main Flows / Use Cases

| Use Case                       | Input                  | Output                        | Description                                                                                                          |
|--------------------------------|------------------------|-------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `CreateContactUseCase`         | `CreateContactCommand` | `ContactDTO`                  | Создает `ContactEntity` через factory, сохраняет через `ContactCommandRepositoryProtocol`, мапит entity в DTO.       |
| `GetContactUseCase`            | `GetContactQuery`      | `ContactDTO`                  | Читает контакт через `ContactQueryRepositoryProtocol`; при отсутствии поднимает `ContactNotFoundError`.              |
| `ListContactsUseCase`          | `ListContactsQuery`    | `ContactListResultDTO`        | Делегирует поиск в `RuntimeObjectQueryService` для объекта `contact`, мапит runtime rows в DTO и возвращает `total`. |
| `UpdateContactUseCase`         | `RenameContactCommand` | `ContactDTO`                  | Загружает entity, вызывает `ContactEntity.rename`, сохраняет через command repository.                               |
| `DeleteContactUseCase`         | `DeleteContactCommand` | `None`                        | Проверяет существование контакта через `load`, затем удаляет через command repository.                               |
| `DescribeContactFieldsUseCase` | `EntityIdVO`           | `ContactFieldsDescriptionDTO` | Возвращает описание объекта `contact` через `ContactFieldsDescriptionRepositoryProtocol`.                            |
| `CreateCompanyUseCase`         | `CreateCompanyCommand` | `CompanyDTO`                  | Создает `CompanyEntity` через factory, сохраняет через `CompanyCommandRepositoryProtocol`, мапит entity в DTO.       |
| `GetCompanyUseCase`            | `GetCompanyQuery`      | `CompanyDTO`                  | Читает компанию через `CompanyQueryRepositoryProtocol`; при отсутствии поднимает `CompanyNotFoundError`.             |
| `ListCompaniesUseCase`         | `ListCompaniesQuery`   | `list[CompanyDTO]`            | Возвращает страницу компаний через `CompanyQueryRepositoryProtocol`.                                                 |
| `UpdateCompanyUseCase`         | `UpdateCompanyCommand` | `CompanyDTO`                  | Загружает entity, вызывает `CompanyEntity.update`, сохраняет через command repository.                               |
| `DeleteCompanyUseCase`         | `DeleteCompanyCommand` | `None`                        | Проверяет существование компании через `load`, затем удаляет через command repository.                               |
| `DescribeCompanyFieldsUseCase` | `EntityIdVO`           | `CompanyFieldsDescriptionDTO` | Возвращает описание объекта `company` через `CompanyFieldsDescriptionRepositoryProtocol`.                            |

## Domain Model

### `ContactEntity`

- ID: `ContactIdVO`, concrete VO поверх `src.modules.shared.EntityIdVO`.
- Tenant scope: поля `tenant_id` в entity нет; tenant передается снаружи через command/query/repository методы как
  `EntityIdVO`.
- Fields: `id`, `created_at`, `updated_at`, `contact_name`, `status`, `tags`.
- Value Objects:
  - `ContactNameVO(last_name, first_name, middle_name)`;
  - `ContactIdVO`.
- Factory methods: `ContactEntity.create(...)` выставляет одинаковые `created_at` и `updated_at`, валидирует имя через
  `ContactNameVO`, преобразует tuple tags в list.
- Update methods:
  - `rename(...)` обновляет ФИО, статус и теги; если данные не изменились, `updated_at` не меняется;
  - `touch(...)` обновляет только `updated_at`.
- Domain errors:
  - `ContactNotFoundError`;
  - `InvalidContactNameError`.
- Invariants:
  - `ContactNameVO` запрещает `first_name is None`;
  - пустая строка `first_name` сейчас допустима и покрыта тестом `test/test_crm_contact_name_vo.py`;
  - `tags=None` в `rename` означает "оставить текущие теги", пустой tuple очищает теги.

### `CompanyEntity`

- ID: `CompanyIdVO`, concrete VO поверх `src.modules.shared.EntityIdVO`.
- Tenant scope: поля `tenant_id` в entity нет; tenant передается снаружи через command/query/repository методы как
  `EntityIdVO`.
- Fields: `id`, `created_at`, `updated_at`, `legal_name`.
- Value Objects:
  - `CompanyLegalNameVO(value)`;
  - `CompanyIdVO`.
- Factory methods: `CompanyEntity.create(...)` выставляет одинаковые `created_at` и `updated_at`, нормализует
  `legal_name` через `CompanyLegalNameVO`.
- Update methods: `update(...)` меняет `legal_name` и `updated_at` только при фактическом изменении значения.
- Domain errors:
  - `CompanyNotFoundError`;
  - `InvalidCompanyLegalNameError`.
- Invariants:
  - `CompanyLegalNameVO` принимает только string;
  - значение trim-ится;
  - пустая строка после trim запрещена.

## Application Layer

### Commands

Все command classes оформлены как `@dataclass(slots=True, frozen=True)`:

- `CreateContactCommand`: `tenant_id`, `contact_id`, `first_name`, optional `last_name`, `middle_name`, `status`,
  `tags`.
- `RenameContactCommand`: `tenant_id`, `contact_id`, `first_name`, optional `last_name`, `middle_name`, `status`,
  optional `tags`.
- `DeleteContactCommand`: `tenant_id`, `contact_id`.
- `CreateCompanyCommand`: `tenant_id`, `company_id`, `legal_name`.
- `UpdateCompanyCommand`: `tenant_id`, `company_id`, `legal_name`.
- `DeleteCompanyCommand`: `tenant_id`, `company_id`.

### Queries

Все query classes оформлены как `@dataclass(slots=True, frozen=True)`:

- `GetContactQuery`: `tenant_id`, `contact_id`.
- `ListContactsQuery`: `tenant_id`, `limit`, `offset`, optional `filter_dsl`, `sort_dsl`.
- `GetCompanyQuery`: `tenant_id`, `company_id`.
- `ListCompaniesQuery`: `tenant_id`, `limit=50`, `offset=0`.

### DTOs

- `ContactDTO`: `id`, timestamps, name fields, `status`, `tags`.
- `ContactListResultDTO`: `items`, `total`, `limit`, `offset`.
- `ContactFieldsDescriptionDTO`: object description plus field descriptions with options, filter capability and sort
  capability.
- `CompanyDTO`: `id`, timestamps, `legal_name`.
- `CompanyFieldsDescriptionDTO`: object description plus field descriptions with options.

DTO classes находятся в application layer и оформлены dataclass. HTTP Pydantic schemas остаются в presentation layer.

### Use Cases

- Contact write use cases (`CreateContactUseCase`, `UpdateContactUseCase`, `DeleteContactUseCase`) используют
  `ContactCommandRepositoryProtocol`; create/update дополнительно используют `ClockPort`.
- Contact read-by-id use case (`GetContactUseCase`) использует `ContactQueryRepositoryProtocol`.
- Contact list/search use case (`ListContactsUseCase`) использует `RuntimeObjectQueryService` напрямую.
- Contact metadata use case (`DescribeContactFieldsUseCase`) использует `ContactFieldsDescriptionRepositoryProtocol`.
- Company write use cases (`CreateCompanyUseCase`, `UpdateCompanyUseCase`, `DeleteCompanyUseCase`) используют
  `CompanyCommandRepositoryProtocol`; create/update дополнительно используют `ClockPort`.
- Company read use cases (`GetCompanyUseCase`, `ListCompaniesUseCase`) используют `CompanyQueryRepositoryProtocol`.
- Company metadata use case (`DescribeCompanyFieldsUseCase`) использует `CompanyFieldsDescriptionRepositoryProtocol`.

### Repository Protocols

- `ContactCommandRepositoryProtocol`: `load`, `save`, `delete` для `ContactEntity`.
- `ContactQueryRepositoryProtocol`: `get_by_id`, `list` для `ContactDTO`.
- `ContactFieldsDescriptionRepositoryProtocol`: `describe_fields`.
- `CompanyCommandRepositoryProtocol`: `load`, `save`, `delete` для `CompanyEntity`.
- `CompanyQueryRepositoryProtocol`: `get_by_id`, `list` для `CompanyDTO`.
- `CompanyFieldsDescriptionRepositoryProtocol`: `describe_fields`.

## Infrastructure / Persistence

### `ContactRuntimeRepository`

- File: `src/modules/crm/infrastructure/contact_runtime_repository.py`.
- Implements: `ContactCommandRepositoryProtocol`, `ContactQueryRepositoryProtocol`.
- Storage: `runtime_data` через `RuntimeCommandGateway` и `RuntimeQueryGateway`.
- Runtime object: `_OBJECT_NAME = "contact"`.
- Tenant handling: repository не хранит tenant в instance; каждый public method принимает `tenant_id: EntityIdVO` и
  резолвит descriptor через `RuntimeObjectResolverProtocol`.
- Mapping:
  - `_row_to_entity` мапит runtime row в `ContactEntity`;
  - `_row_to_dto` мапит runtime row в `ContactDTO`;
  - UUID, datetime, optional string и `list[str]` проверяются явно.
- Write behavior:
  - `save` сначала вызывает gateway `get_by_id`;
  - если строки нет, делает `insert`;
  - если строка есть, делает `update`;
  - `list` сортирует по `created_at asc`, затем `id asc`.
- Errors:
  - `ContactNotFoundError`, если update/delete не нашел строку;
  - `TypeError`, если runtime row имеет неожиданные типы;
  - runtime/schema errors не перехватываются в repository и мапятся выше на HTTP layer.

### `CompanyRuntimeRepository`

- File: `src/modules/crm/infrastructure/company_runtime_repository.py`.
- Implements: `CompanyCommandRepositoryProtocol`, `CompanyQueryRepositoryProtocol`.
- Storage: `runtime_data` через `RuntimeCommandGateway` и `RuntimeQueryGateway`.
- Runtime object: `_OBJECT_NAME = "company"`.
- Tenant handling: repository не хранит tenant в instance; каждый public method принимает `tenant_id: EntityIdVO` и
  резолвит descriptor через `RuntimeObjectResolverProtocol`.
- Mapping:
  - `_row_to_entity` мапит runtime row в `CompanyEntity`;
  - `_row_to_dto` мапит runtime row в `CompanyDTO`;
  - UUID, datetime и string проверяются явно.
- Write behavior:
  - `save` сначала вызывает gateway `get_by_id`;
  - если строки нет, делает `insert` с `id` и `legal_name`;
  - если строка есть, делает `update` с `legal_name`;
  - `list` сортирует по `created_at asc`, затем `id asc`.
- Errors:
  - `CompanyNotFoundError`, если update/delete не нашел строку;
  - `TypeError`, если runtime row имеет неожиданные типы;
  - runtime/schema errors не перехватываются в repository и мапятся выше на HTTP layer.

### `ContactModelDescriptionRepository`

- File: `src/modules/crm/infrastructure/contact_model_description_repository.py`.
- Implements: `ContactFieldsDescriptionRepositoryProtocol`.
- Storage: не читает runtime rows; вызывает `DescribeRuntimeObjectUseCaseProtocol` из `schema_registry`.
- Runtime object: `_OBJECT_NAME = "contact"`.
- Tenant handling: `describe_fields` принимает `tenant_id` и передает его в `schema_registry` use case; если передан
  `RuntimeObjectResolverProtocol`, дополнительно резолвит descriptor для query capabilities.
- Mapping: schema_registry object/field DTO мапятся в `ContactObjectDescriptionDTO`,
  `ContactFieldDescriptionDTO`, `ContactFieldOptionDTO`.
- Query capabilities: добавляет `filter` и `sort` capability через `QueryCapabilityResolver`; если resolver не передан,
  использует disabled capabilities.
- Errors: schema_registry errors не перехватываются в repository.

### `CompanyModelDescriptionRepository`

- File: `src/modules/crm/infrastructure/company_model_description_repository.py`.
- Implements: `CompanyFieldsDescriptionRepositoryProtocol`.
- Storage: не читает runtime rows; вызывает `DescribeRuntimeObjectUseCaseProtocol` из `schema_registry`.
- Runtime object: `_OBJECT_NAME = "company"`.
- Tenant handling: `describe_fields` принимает `tenant_id` и передает его в `schema_registry` use case.
- Mapping: schema_registry object/field DTO мапятся в `CompanyObjectDescriptionDTO`,
  `CompanyFieldDescriptionDTO`, `CompanyFieldOptionDTO`.
- Query capabilities: в текущей реализации не добавляются в company field DTO/response.
- Errors: schema_registry errors не перехватываются в repository.

## Presentation / HTTP API

Base prefix:

```text
/api
```

`src/modules/crm/presentation/http/router.py` подключает action routers без собственного prefix. Префиксы задаются в
controller modules: `/crm/contacts` и `/crm/companies`.

| Method   | Path                              | Controller                | Use Case                       | Request                      | Response                                           |
|----------|-----------------------------------|---------------------------|--------------------------------|------------------------------|----------------------------------------------------|
| `POST`   | `/api/crm/contacts`               | `create_contact`          | `CreateContactUseCase`         | `CreateContactRequestSchema` | `ContactResponseSchema`, `201`                     |
| `GET`    | `/api/crm/contacts`               | `list_contacts`           | `ListContactsUseCase`          | query `limit`, `offset`      | `ListContactsResponseSchema`                       |
| `POST`   | `/api/crm/contacts/search`        | `search_contacts`         | `ListContactsUseCase`          | `ContactSearchRequestSchema` | `ContactSearchResponseSchema`                      |
| `GET`    | `/api/crm/contacts/fields`        | `describe_contact_fields` | `DescribeContactFieldsUseCase` | none                         | `ContactFieldsResponseSchema`                      |
| `POST`   | `/api/crm/contacts/fields`        | `describe_contact_fields` | `DescribeContactFieldsUseCase` | none                         | `ContactFieldsResponseSchema`; hidden from OpenAPI |
| `GET`    | `/api/crm/contacts/{contact_id}`  | `get_contact`             | `GetContactUseCase`            | path `contact_id`            | `ContactResponseSchema`                            |
| `PUT`    | `/api/crm/contacts/{contact_id}`  | `update_contact`          | `UpdateContactUseCase`         | `UpdateContactRequestSchema` | `ContactResponseSchema`                            |
| `DELETE` | `/api/crm/contacts/{contact_id}`  | `delete_contact`          | `DeleteContactUseCase`         | path `contact_id`            | empty `204`                                        |
| `POST`   | `/api/crm/companies`              | `create_company`          | `CreateCompanyUseCase`         | `CreateCompanyRequestSchema` | `CompanyResponseSchema`, `201`                     |
| `GET`    | `/api/crm/companies`              | `list_companies`          | `ListCompaniesUseCase`         | query `limit`, `offset`      | `ListCompaniesResponseSchema`                      |
| `POST`   | `/api/crm/companies/fields`       | `describe_company_fields` | `DescribeCompanyFieldsUseCase` | none                         | `CompanyFieldsResponseSchema`                      |
| `GET`    | `/api/crm/companies/{company_id}` | `get_company`             | `GetCompanyUseCase`            | path `company_id`            | `CompanyResponseSchema`                            |
| `PUT`    | `/api/crm/companies/{company_id}` | `update_company`          | `UpdateCompanyUseCase`         | `UpdateCompanyRequestSchema` | `CompanyResponseSchema`                            |
| `DELETE` | `/api/crm/companies/{company_id}` | `delete_company`          | `DeleteCompanyUseCase`         | path `company_id`            | empty `204`                                        |

All routes require `AuthenticatedRequestContextDep`. Controllers read `principal.tenant_id`, convert it to
`EntityIdVO`, and do not accept `tenant_id` from HTTP payloads.

HTTP error mapping:

- missing principal or tenant id -> `401 Unauthorized`;
- `ContactNotFoundError` / `CompanyNotFoundError` -> `404 Not Found`;
- runtime persistence/policy errors and runtime object descriptor/not-found/schema metadata consistency errors -> `409`;
- runtime validation/filter errors and generic `DomainError` -> `422`;
- metadata controllers map `DataSourceNotFoundError`, `RuntimeObjectNotFoundError`,
  `SchemaRegistryMetadataInconsistentError` -> `409`, `DomainError` -> `422`.

## Dependency Injection

- Infrastructure dependencies:
  - `get_runtime_field_type_policy` creates `RuntimeFieldTypePolicy`;
  - `get_runtime_query_gateway` creates `PostgresRuntimeQueryGateway` from `UoWDep.session`;
  - `get_runtime_command_gateway` creates `PostgresRuntimeCommandGateway` from `UoWDep.session`;
  - `get_runtime_object_query_service` creates `RuntimeObjectQueryService`;
  - `get_query_capability_resolver` creates `QueryCapabilityResolver`;
  - `get_contact_query_repository` and `get_contact_command_repository` create separate `ContactRuntimeRepository`
    instances;
  - `get_company_query_repository` and `get_company_command_repository` create separate `CompanyRuntimeRepository`
    instances;
  - `get_contact_fields_description_repository` creates `ContactModelDescriptionRepository`;
  - `get_company_fields_description_repository` creates `CompanyModelDescriptionRepository`.
- Application dependencies:
  - `get_create_contact_use_case`, `get_update_contact_use_case` and company analogs inject command repositories and
    `ClockDep`;
  - get/list use cases inject query repositories, except `get_list_contacts_use_case`, which injects
    `RuntimeObjectQueryServiceDep`;
  - describe-fields use cases inject fields description repositories.
- Shared dependencies:
    - `UoWDep` from `shared.presentation.persistence`;
    - `ClockDep` from `shared.presentation.time`;
  - `AuthenticatedRequestContextDep` in controllers.
- Schema registry dependencies:
  - `RuntimeObjectResolverDep`;
  - `DescribeRuntimeObjectUseCaseDep`.

## Dependencies On Other Modules

| Module            | Layer                                   | Used For                                                                                                                          |
|-------------------|-----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `shared`          | domain/application/presentation         | `EntityIdVO`, `DomainError`, `ClockPort`/`ClockDep`, `UoWDep`, authenticated request context.                                     |
| `runtime_data`    | application/infrastructure/presentation | Runtime gateways, query service, search query, page/sort specs, type policy, query capabilities, runtime errors.                  |
| `schema_registry` | infrastructure/presentation             | Runtime object descriptor resolution, metadata description use case, schema metadata errors, CRM seed source for runtime objects. |

## Events / Background Processing

В текущей реализации не найдено.

Не найдены event handlers, message consumers, scheduled jobs, management commands, outbox/inbox или queue consumers
внутри `src/modules/crm`.

## Tests Covering This Module

- Domain:
  - `test/test_crm_contact_entity.py`;
  - `test/test_crm_company_entity.py`;
  - `test/test_crm_contact_name_vo.py`;
  - `test/test_crm_company_legal_name_vo.py`.
- Application:
  - `test/test_crm_contact_use_cases.py`;
  - `test/test_crm_company_use_cases.py`.
- Infrastructure:
  - `test/test_crm_contact_runtime_repository.py`;
  - `test/test_crm_company_runtime_repository.py`;
  - `test/test_crm_contact_model_description_repository.py`.
- Presentation:
  - `test/test_crm_contact_controller_errors.py`;
  - `test/test_crm_company_controller_errors.py`;
  - `test/test_crm_contact_fields_controller.py`;
  - `test/test_crm_company_fields_controller.py`.
- Integration / architecture / schema-related:
  - `test/test_architecture_boundaries.py`;
  - `test/test_inventory_schema_seed.py` проверяет наличие CRM seed objects/relations и отсутствие удалённых runtime
    models.

Important uncovered or partially covered areas found during audit:

- direct repository test for `CompanyModelDescriptionRepository` was not found;
- direct HTTP router smoke test for the whole CRM router was not found;
- tests for HTTP management of `contact_companies` are not applicable because endpoints for this relation were not
  found.

## Known Gaps / Technical Debt

- `ListContactsUseCase` напрямую зависит от `RuntimeObjectQueryService`, тогда как `ListCompaniesUseCase` использует
  `CompanyQueryRepositoryProtocol`. Это отклоняется от более единообразного query repository pattern внутри CRM.
- Contact search response возвращает `pagination.total`, но обычный `GET /api/crm/contacts` возвращает только `count`
  текущей страницы. Company list также возвращает только `count`, без `total`.
- `ContactNameVO` запрещает только `None` для `first_name`; пустая строка сейчас допустима и закреплена тестом.
- Contact fields metadata включает filter/sort capabilities; company fields metadata такой capability surface не имеет.
- `CompanyModelDescriptionRepository` не найден среди прямых repository tests.
- Runtime seed содержит relation `contact_companies`, но CRM module не содержит application или HTTP сценариев для
  управления этой связью.

## Related Documentation

- [Develop Style](../develop-style.md)
- [HTTP API](../interfaces/http-api.md)
- [Runtime schema](../data/runtime-schema.md)
- [Domain models](../data/domain-models.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `docs/prompts/document-module-from-source.md`
- `docs/develop-style.md`
- `src/modules/router.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/crm/domain/contact/value_object/contact_name.py`
- `src/modules/crm/domain/contact/repository.py`
- `src/modules/crm/domain/company/entity.py`
- `src/modules/crm/domain/company/value_object/company_legal_name.py`
- `src/modules/crm/domain/company/repository.py`
- `src/modules/crm/application/contact/`
- `src/modules/crm/application/company/`
- `src/modules/crm/infrastructure/contact_runtime_repository.py`
- `src/modules/crm/infrastructure/company_runtime_repository.py`
- `src/modules/crm/infrastructure/contact_model_description_repository.py`
- `src/modules/crm/infrastructure/company_model_description_repository.py`
- `src/modules/crm/presentation/depends/`
- `src/modules/crm/presentation/http/`
- `src/modules/schema_registry/seed/contexts/crm.py`
- `test/test_crm_contact_entity.py`
- `test/test_crm_company_entity.py`
- `test/test_crm_contact_name_vo.py`
- `test/test_crm_company_legal_name_vo.py`
- `test/test_crm_contact_use_cases.py`
- `test/test_crm_company_use_cases.py`
- `test/test_crm_contact_runtime_repository.py`
- `test/test_crm_company_runtime_repository.py`
- `test/test_crm_contact_model_description_repository.py`
- `test/test_crm_contact_controller_errors.py`
- `test/test_crm_company_controller_errors.py`
- `test/test_crm_contact_fields_controller.py`
- `test/test_crm_company_fields_controller.py`
- `test/test_architecture_boundaries.py`
- `test/test_inventory_schema_seed.py`
