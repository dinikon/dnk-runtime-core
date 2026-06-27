# Runtime Data Module

## Purpose

`runtime_data` предоставляет технический слой чтения, записи, поиска и загрузки связей для runtime objects, описанных
metadata из `schema_registry`.

Модуль не является классическим bounded context с aggregate model. Это технический runtime-data/persistence/query
модуль: он принимает `RuntimeObjectDescriptor`, валидирует payload и query DSL относительно descriptor, компилирует
запросы в PostgreSQL SQL и возвращает runtime rows или application DTO для поиска.

## Current Scope

Текущая реализация покрывает:

- descriptor-backed CRUD над runtime records;
- typed filter/sort DSL для публичного поиска;
- internal builder для типизированных фильтров в application repositories других модулей;
- pagination и total count для search;
- projection полей через `FetchPlan`;
- relation loading и relation commands по `RuntimeRelationDescriptor`;
- runtime type policy для приведения payload/filter values к Python/PostgreSQL-совместимым типам;
- query capabilities для frontend metadata endpoints.

Текущая реализация явно не содержит:

- `presentation/` layer;
- HTTP routes;
- module-local dependency injection в `presentation/depends`;
- domain entities, aggregates или value objects;
- management commands, jobs, event handlers, queues, outbox/inbox.

## Public Functionality

- `RuntimeCommandGateway` задает порт command-операций: `insert`, `update`, `delete`, `update_where`, `claim`.
- `RuntimeQueryGateway` задает порт read/search-операций: `get_by_id`, `list`, `search`.
- `RuntimeObjectQueryService.search_records` выполняет публичный поиск runtime records по `RuntimeSearchRecordsQuery`.
- `FilterDslParser`, `FilterSemanticValidator`, `FilterOperatorRegistry` и `FilterValueCoercer` разбирают и валидируют
  filter DSL.
- `SortDslParser` и `SortSemanticValidator` разбирают и валидируют sort DSL.
- `RuntimeTypedFilterBuilder` строит typed filters для trusted internal repositories.
- `QueryCapabilityResolver` строит capabilities фильтрации/сортировки для frontend metadata endpoints.
- `RuntimeRelationCommandGateway` и relation use cases поддерживают чтение related records, attach/detach M2M, set/unset
  FK relations.
- PostgreSQL infrastructure реализует runtime gateways через SQLAlchemy `AsyncSession` без commit/rollback внутри
  gateway.

## Main Flows / Use Cases

| Use Case                                   | Input                                                                          | Output                       | Description                                                                                                                                                 |
|--------------------------------------------|--------------------------------------------------------------------------------|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `RuntimeObjectQueryService.search_records` | `RuntimeSearchRecordsQuery`                                                    | `RuntimeSearchRecordsResult` | Резолвит `RuntimeObjectDescriptor`, парсит filter/sort DSL, валидирует их по descriptor, добавляет default sorting и вызывает `RuntimeQueryGateway.search`. |
| `GetRelatedRecordUseCase`                  | `tenant_id`, `object_name`, `relation_name`, `object_id`                       | `Mapping[str, Any] \| None`  | Резолвит descriptor через `RuntimeObjectResolverProtocol` и читает single related record через relation gateway.                                            |
| `ListRelatedRecordsUseCase`                | `tenant_id`, `object_name`, `relation_name`, `object_id`                       | `list[Mapping[str, Any]]`    | Резолвит descriptor и читает collection related records.                                                                                                    |
| `AttachRelatedRecordUseCase`               | `tenant_id`, `object_name`, `relation_name`, `object_id`, `related_id`         | `None`                       | Резолвит descriptor и создает M2M связь.                                                                                                                    |
| `DetachRelatedRecordUseCase`               | `tenant_id`, `object_name`, `relation_name`, `object_id`, `related_id`         | `None`                       | Резолвит descriptor и удаляет M2M связь.                                                                                                                    |
| `SetRelationUseCase`                       | `tenant_id`, `object_name`, `relation_name`, `object_id`, `related_id`         | `None`                       | Резолвит descriptor и устанавливает FK-based relation.                                                                                                      |
| `UnsetRelationUseCase`                     | `tenant_id`, `object_name`, `relation_name`, `object_id`, `related_id \| None` | `None`                       | Резолвит descriptor и сбрасывает nullable FK-based relation.                                                                                                |

`src/modules/runtime_data/application/**/use_case/` в текущей структуре отсутствует. Relation use cases находятся в
`src/modules/runtime_data/application/relation_use_cases.py`.

## Domain Model

### Aggregates / Entities

- ID: В текущей реализации не найдено.
- Tenant scope: В текущей реализации не найдено на уровне domain entities.
- Fields: В текущей реализации не найдено.
- Value Objects: В текущей реализации не найдено.
- Factory methods: В текущей реализации не найдено.
- Update methods: В текущей реализации не найдено.
- Domain errors: `RuntimeDataError`, `RuntimeDataValidationError`, `RuntimeDataObjectNotFoundError`,
  `RuntimeDataFilterError`, `RuntimeDataPolicyError`, `RuntimeDataPersistenceError`.
- Invariants: хранятся не в entities, а в application/infrastructure policies: descriptor-required fields, immutable
  patch fields, filter/sort compatibility, identifier validation, page limits.

Domain layer фактически состоит из `src/modules/runtime_data/domain/error.py`.

## Application Layer

### Commands

Отдельные immutable command dataclasses в текущей реализации не найдены.

Relation use cases принимают keyword-arguments напрямую: `tenant_id`, `object_name`, `relation_name`, `object_id`,
`related_id`.

### Queries

- `RuntimeSearchRecordsQuery` (`src/modules/runtime_data/application/query/query.py`) - immutable dataclass для public
  search: `tenant_id`, `object_name`, `filter_dsl`, `sort_dsl`, `limit`, `offset`.
- `RuntimeQueryPlan` (`src/modules/runtime_data/application/query/query_plan.py`) - descriptor-backed план запроса после
  semantic validation: `descriptor`, `filters`, `sorting`, `page`, `fetch_plan`.

### DTOs

- `RuntimeRecordDTO` (`src/modules/runtime_data/application/query/result.py`) - DTO одной runtime-записи: `id`,
  `values`.
- `RuntimeSearchRecordsResult` (`src/modules/runtime_data/application/query/result.py`) - DTO страницы поиска: `rows`,
  `total`, `limit`, `offset`.
- `RuntimeRowsPage` (`src/modules/runtime_data/application/models.py`) - результат gateway-level search: raw rows +
  total.
- `FieldFilterCapability`, `FieldSortCapability`, `FieldQueryCapability` (
  `src/modules/runtime_data/application/query/capabilities/field_query_capability.py`) - DTO capabilities для query UI.

### Use Cases / Services

- `RuntimeObjectQueryService` (`src/modules/runtime_data/application/query/runtime_object_query_service.py`) -
  application service публичного поиска.
- `GetRelatedRecordUseCase`, `ListRelatedRecordsUseCase`, `AttachRelatedRecordUseCase`, `DetachRelatedRecordUseCase`,
  `SetRelationUseCase`, `UnsetRelationUseCase` (`src/modules/runtime_data/application/relation_use_cases.py`) - thin use
  cases поверх resolver и `RuntimeRelationCommandGateway`.
- `RuntimeFieldTypePolicy` (`src/modules/runtime_data/application/type_policy.py`) - policy приведения
  insert/patch/filter values и normalize row.
- `FilterDslParser`, `FilterSemanticValidator`, `FilterOperatorRegistry`, `FilterValueCoercer` - filter DSL pipeline.
- `SortDslParser`, `SortSemanticValidator` - sort DSL pipeline.
- `RuntimeTypedFilterBuilder` - internal helper для построения typed filters без публичного JSON DSL.
- `QueryCapabilityResolver` - resolver capabilities фильтрации и сортировки по descriptor fields.

### Repository Protocols

В модуле нет repository protocols в стиле aggregate repositories. Вместо них определены gateway ports в
`src/modules/runtime_data/application/ports.py`:

- `RuntimeCommandGateway`;
- `RuntimeQueryGateway`;
- `RuntimeRelationLoader`;
- `RuntimeRelationCommandGateway`.

## Infrastructure / Persistence

### PostgresRuntimeCommandGateway

- File: `src/modules/runtime_data/infrastructure/persistence/postgres/gateway/command_gateway.py`
- Implements: `RuntimeCommandGateway`.
- Storage: PostgreSQL runtime tables через SQLAlchemy `AsyncSession`.
- Runtime object: использует `RuntimeObjectDescriptor.schema_name`, `table_name`, `pk`, `fields`.
- Tenant handling: tenant не хранится в gateway; tenant scope уже учтен на этапе resolver, который возвращает
  descriptor.
- Mapping: payload приводится через `RuntimeFieldTypePolicy`; результат `RETURNING` нормализуется через `normalize_row`.
- Errors: `RuntimeDataValidationError`, `RuntimeDataPolicyError`, `RuntimeDataPersistenceError`.
- Operations: `insert`, `update`, `delete`, `update_where`, `claim`.

`claim` использует CTE с `FOR UPDATE SKIP LOCKED`, `ORDER BY` и `LIMIT :claim_limit`.

### PostgresRuntimeQueryGateway

- File: `src/modules/runtime_data/infrastructure/persistence/postgres/gateway/query_gateway.py`
- Implements: `RuntimeQueryGateway`.
- Storage: PostgreSQL runtime tables через SQLAlchemy `AsyncSession`.
- Runtime object: использует `RuntimeObjectDescriptor`.
- Tenant handling: tenant не хранится в gateway; descriptor должен быть получен снаружи по tenant.
- Mapping: rows нормализуются через `RuntimeFieldTypePolicy.normalize_row`; relation data дозагружается через
  `RuntimeRelationLoader`, если `FetchPlan.relations` не пустой.
- Errors: `RuntimeDataValidationError`, `RuntimeDataPolicyError`, `RuntimeDataPersistenceError`.
- Operations: `get_by_id`, `list`, `search`.

`search` отдельно выполняет `COUNT(*)` и page query по одному `RuntimeQueryPlan`.

### PostgresRuntimeRelationCommandGateway

- File: `src/modules/runtime_data/infrastructure/persistence/postgres/gateway/relation_command_gateway.py`
- Implements: `RuntimeRelationCommandGateway`.
- Storage: PostgreSQL runtime object tables и relation tables.
- Runtime object: использует `RuntimeRelationDescriptor` из `descriptor.relations`.
- Tenant handling: tenant не хранится; работает с переданным descriptor.
- Mapping: читает base row, вызывает `PostgresRuntimeRelationLoader`, проверяет mapping shape.
- Errors: `RuntimeDataValidationError`, `RuntimeDataPersistenceError`.
- Operations: `get_related_record`, `list_related_records`, `attach_related_record`, `detach_related_record`,
  `set_relation`, `unset_relation`.

M2M операции используют relation table metadata: `relation_table_name`, `source_join_column_name`,
`target_join_column_name`. FK operations используют `owning_object`, `fk_field`, `referenced_object`,
`referenced_field`.

### PostgresRuntimeRelationLoader

- File: `src/modules/runtime_data/infrastructure/persistence/postgres/gateway/relation_loader.py`
- Implements: `RuntimeRelationLoader`.
- Storage: PostgreSQL runtime object tables и relation tables.
- Runtime object: загружает relations по именам из `FetchPlan.relations`.
- Tenant handling: tenant не хранится; schema берется из descriptor.
- Mapping: обогащает base rows ключами `source_relation_name` или `target_relation_name`.
- Errors: `RuntimeDataValidationError`, `RuntimeDataPersistenceError`.

Поддержанные relation types:

- `many_to_many`;
- `one_to_many`;
- `many_to_one`;
- `one_to_one`.

`NoopRuntimeRelationLoader` в том же файле реализует заглушку для тестов и альтернативных backend.

### SQL Compilers / Execution

- `PostgresRuntimeQueryCompiler` (`compiler/runtime_query_compiler.py`) компилирует `RuntimeQueryPlan` в SQL для
  count/search/list.
- `PostgresFilterSqlCompiler` (`compiler/filter_sql_compiler.py`) компилирует typed filters в `WHERE`.
- `PostgresSortSqlCompiler` (`compiler/sort_sql_compiler.py`) компилирует `SortSpec` в `ORDER BY`.
- `PostgresProjectionSqlCompiler` (`compiler/projection_sql_compiler.py`) компилирует projection list и всегда добавляет
  pk, если projection задан без него.
- `identifier.py` валидирует PostgreSQL identifiers regex-ом `^[a-z][a-z0-9_]*$` перед dynamic SQL composition.
- `PostgresSqlExecutor` (`execution/executor.py`) выполняет SQLAlchemy statements и мапит `SQLAlchemyError` в
  `RuntimeDataPersistenceError`.
- `PostgresStatementFactory` (`execution/statement_factory.py`) добавляет JSONB bind params для `json` и `multiselect`.

## Presentation / HTTP API

Base prefix:

```text
В текущей реализации не найдено.
```

| Method                           | Path                             | Controller                       | Use Case                         | Request                          | Response                         |
|----------------------------------|----------------------------------|----------------------------------|----------------------------------|----------------------------------|----------------------------------|
| В текущей реализации не найдено. | В текущей реализации не найдено. | В текущей реализации не найдено. | В текущей реализации не найдено. | В текущей реализации не найдено. | В текущей реализации не найдено. |

В модуле отсутствует `src/modules/runtime_data/presentation/`. HTTP endpoints, которые используют `runtime_data`,
находятся в потребляющих модулях (`crm`, `custom_object`, `communication`).

## Dependency Injection

- Infrastructure dependencies: module-local DI в `src/modules/runtime_data/presentation/depends/` отсутствует.
- Application dependencies: `RuntimeObjectQueryService` и relation use cases создаются потребляющими модулями или
  тестами.
- Shared dependencies: `AsyncSession` поступает через `UoWDep` в DI потребителей.

Фактическая wiring-точка находится вне `runtime_data`:

- `src/modules/crm/presentation/depends/infrastructure.py` создает `RuntimeFieldTypePolicy`,
  `PostgresRuntimeQueryGateway`, `PostgresRuntimeCommandGateway`, `RuntimeObjectQueryService`,
  `QueryCapabilityResolver`.
- `src/modules/custom_object/presentation/depends/infrastructure.py` создает `RuntimeFieldTypePolicy`,
  `PostgresRuntimeQueryGateway`, `PostgresRuntimeCommandGateway`.
- `src/modules/communication/presentation/depends/infrastructure.py` и
  `src/modules/communication/presentation/depends/management.py` создают runtime gateways для communication
  repositories/management flows.

## Dependencies On Other Modules

| Module                    | Layer                           | Used For                                                                                                                              |
|---------------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| `shared`                  | `domain`, `application`         | `DomainError` для runtime errors; `EntityIdVO` для tenant scope в queries/relation use cases.                                         |
| `schema_registry.runtime` | `application`, `infrastructure` | `RuntimeObjectDescriptor`, `RuntimeFieldDescriptor`, `RuntimeRelationDescriptor`, `RuntimeObjectResolverProtocol`.                    |
| `crm`                     | внешний потребитель             | Использует runtime gateways, `RuntimeObjectQueryService`, `QueryCapabilityResolver` и runtime errors в repositories/controllers.      |
| `custom_object`           | внешний потребитель             | Использует runtime gateways и DSL validators для dynamic custom record CRUD/search.                                                   |
| `communication`           | внешний потребитель             | Использует runtime gateways, `RuntimeTypedFilterBuilder`, runtime errors и type policy для runtime-backed communication repositories. |

Внутри `runtime_data` нет зависимости на `crm`, `custom_object` или `communication`; эти зависимости
направлены от потребителей к `runtime_data`.

## Events / Background Processing

В текущей реализации не найдено.

В модуле нет event handlers, message consumers, scheduled jobs, management commands, CLI commands, outbox/inbox или
queue adapters.

## Tests Covering This Module

- Domain: прямых domain entity tests нет, потому что domain entities отсутствуют. `test/test_runtime_data_search_dsl.py`
  и `test/test_runtime_data_type_policy.py` проверяют domain/application errors и validation behavior.
- Application:
    - `test/test_runtime_data_search_dsl.py` покрывает filter DSL parser/semantic validator, multiselect operators, sort
      DSL, `RuntimeObjectQueryService`, default sorting и pagination validation.
    - `test/modules/runtime_data/application/query/filter_dsl/test_parser.py` покрывает public parser contract: strict
      condition shape, groups, nesting depth, condition limit, обязательный `value`.
    - `test/test_runtime_data_type_policy.py` покрывает insert/patch coercion, immutable/system fields,
      decimal/datetime/reference/select/multiselect behavior.
    - `test/test_runtime_data_query_capabilities.py` покрывает `QueryCapabilityResolver` для select, multiselect,
      datetime и disabled json capabilities.
- Infrastructure:
    - `test/test_runtime_data_postgres_query_compiler.py` покрывает SQL compilation для filters, nested groups, sorting,
      escaping LIKE wildcards, `neq`, `between`, identifier validation и `PostgresRuntimeQueryGateway.search`.
    - `test/test_runtime_data_postgres_gateway.py` покрывает insert/update/update_where/claim/list/search SQL flow,
      JSONB bind params, no commit/rollback, nested filters, multiselect SQL и SQLAlchemy error mapping.
- Presentation: В текущей реализации не найдено.
- Integration:
    - `test/test_architecture_boundaries.py` проверяет отсутствие legacy runtime_data import surfaces, legacy filter
      spec names и удаление старых compatibility shims.
    - Потребляющие modules имеют собственные tests runtime repositories/controllers, где `runtime_data` используется как
      dependency.

## Known Gaps / Technical Debt

- Текущая структура намеренно отличается от aggregate-модулей вроде `crm`: нет `domain/<aggregate>/entity.py`,
  `repository.py`, `service.py` и нет `application/<aggregate>/use_case/`.
- Между application ports и infrastructure проходят raw runtime rows как `Mapping[str, Any]`; это осознанная форма
  runtime gateway, но она отличается от project style “DTO вместо raw dict” для бизнес-модулей.
- `RuntimeRelationCommandGateway` и `PostgresRuntimeRelationLoader` не имеют прямого dedicated test-файла; найденное
  покрытие по relation loading/commands отсутствует.
- Relation use cases находятся в одном файле `application/relation_use_cases.py`, а не в `application/**/use_case/`.
- Module-local HTTP/DI отсутствует; wiring runtime gateways дублируется в потребляющих модулях.
- `__init__.py` в root/application/domain/infrastructure пакетах не экспортируют публичные классы через `__all__`; по
  `test/test_architecture_boundaries.py` root compatibility import surface намеренно не используется.

## Related Documentation

- [Develop Style](../develop-style.md)
- [Schema Registry Module](./schema-registry.md)
- [Custom Object Module](./custom-object.md)
- [Communication Module](./communication.md)

## Source Of Truth

- `src/modules/runtime_data/domain/error.py`
- `src/modules/runtime_data/application/models.py`
- `src/modules/runtime_data/application/ports.py`
- `src/modules/runtime_data/application/type_policy.py`
- `src/modules/runtime_data/application/relation_use_cases.py`
- `src/modules/runtime_data/application/query/`
- `src/modules/runtime_data/infrastructure/persistence/postgres/`
- `test/test_runtime_data_search_dsl.py`
- `test/modules/runtime_data/application/query/filter_dsl/test_parser.py`
- `test/test_runtime_data_type_policy.py`
- `test/test_runtime_data_query_capabilities.py`
- `test/test_runtime_data_postgres_query_compiler.py`
- `test/test_runtime_data_postgres_gateway.py`
- `test/test_architecture_boundaries.py`
