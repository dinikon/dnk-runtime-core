# Модуль Segmentation

## Статус

`segmentation` реализован в `src/modules/segmentation` как Contact-only bounded context поверх `runtime_data`.
Документ описывает фактическое состояние кода, а не roadmap.

Модуль подключен в корневой API router через `src/modules/router.py`; публичные HTTP routes доступны под
`/api/segments`.

## Назначение

`segmentation` управляет tenant-scoped Contact-аудиториями:

- определениями сегментов;
- версиями dynamic DSL-конфигураций;
- static Contact members;
- read-only preview аудитории;
- синхронными frozen snapshots и snapshot members.

Модуль возвращает только Contact audience: `contact_id` и опциональные Contact summary read models. Он не выбирает
`contact_point`, канал, provider, template, workflow step или campaign action.

По типу реализации это runtime-data module: persistence идет через tenant-scoped runtime objects, описанные seed-ом
`schema_registry`, без ORM-моделей сегментации.

## Public Functionality

Фактически поддерживаются:

- create/list/get/update/archive segment definitions;
- create/list/get/activate segment versions;
- add/list/remove static Contact members;
- preview raw dynamic config, existing segment definition или exact segment version;
- create/get/list segment snapshots;
- list snapshot members with optional Contact summaries.

Не найдено:

- delete endpoint для segment definitions или versions;
- endpoint активации самого `segment_definition.status`;
- describe-fields endpoints;
- background jobs, management commands, event handlers или queue subscribers;
- persistence для preview результатов.

## Runtime Objects

Seed segmentation находится в `src/modules/schema_registry/seed/schema_seed.py` как `SEGMENTATION_OBJECTS`.

| Runtime object            | Назначение                       | Ключевые поля                                                                                                   | Индексы/relations                                                                               |
|---------------------------|----------------------------------|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `segment_definition`      | Contact segment metadata         | `name`, `description`, `segment_kind`, `status`, `archived_at`                                                  | unique `id`, index `status`, index `segment_kind,status`                                        |
| `segment_version`         | Versioned dynamic DSL config     | `segment_definition_id`, `version_number`, `status`, `config`, `config_checksum`, `activated_at`, `archived_at` | unique `segment_definition_id,version_number`, relation to `segment_definition`                 |
| `segment_static_member`   | Static Contact audience member   | `segment_definition_id`, `contact_id`, `source_type`, `metadata`                                                | unique `segment_definition_id,contact_id`, relation to `segment_definition`; no FK to `contact` |
| `segment_snapshot`        | Frozen Contact audience snapshot | `segment_definition_id`, `segment_version_id`, `status`, `member_count`, timestamps, error fields               | relations to `segment_definition` and `segment_version`                                         |
| `segment_snapshot_member` | Frozen snapshot member           | `segment_snapshot_id`, `contact_id`, `position`                                                                 | unique `segment_snapshot_id,contact_id`, relation to `segment_snapshot`; no FK to `contact`     |

Select values:

- `segment_kind`: `static`, `dynamic`;
- definition/version `status`: `draft`, `active`, `archived`;
- static member `source_type`: `manual`, `import`, `api`;
- snapshot `status`: `pending`, `running`, `completed`, `failed`.

Runtime objects are tenant-scoped by `runtime_data`; seed does not add `tenant_id` fields.

## Domain Model

Domain layer is split by aggregate package under `src/modules/segmentation/domain`.

### SegmentDefinition

File: `domain/segment_definition/entity.py`

- Entity: `SegmentDefinition`.
- Id VO: `SegmentIdVO`.
- Fields: `segment_id`, `name`, `segment_kind`, `status`, `description`, `archived_at`.
- Value objects: `SegmentIdVO`, `SegmentKindVO`, `SegmentStatusVO`.
- Methods:
    - `update(...)` changes name/description and rejects archived segments;
    - `archive(now=...)` is idempotent.
- Invariants:
    - name must be a non-empty trimmed string;
    - `segment_kind` is immutable after creation;
    - archived segment cannot be updated.
- Errors: `SegmentDefinitionNotFoundError`, `InvalidSegmentDefinitionNameError`,
  `SegmentDefinitionArchivedError`, `SegmentDefinitionKindChangeError`.

### SegmentVersion

File: `domain/segment_version/entity.py`

- Entity: `SegmentVersion`.
- Id VO: `SegmentVersionIdVO`; owner id is `SegmentIdVO`.
- Fields: `segment_version_id`, `segment_id`, `version_number`, `status`, `config`, `config_checksum`,
  `activated_at`, `archived_at`.
- Value objects: `SegmentVersionIdVO`, `SegmentVersionStatusVO`.
- Methods:
    - `activate(now=...)` only from `draft`;
    - `archive(now=...)` is idempotent.
- Invariants:
    - `version_number >= 1`;
    - `config` must be a mapping and is copied;
    - `config_checksum` must be non-empty;
    - non-draft versions cannot be activated.
- Errors: `SegmentVersionNotFoundError`, `InvalidSegmentVersionError`, `SegmentVersionTransitionError`.

### SegmentStaticMember

File: `domain/segment_static_member/entity.py`

- Entity: `SegmentStaticMember`.
- Id VO: `SegmentStaticMemberIdVO`; owner id is `SegmentIdVO`; Contact id uses generic `EntityIdVO`.
- Fields: `segment_static_member_id`, `segment_id`, `contact_id`, `source_type`, `metadata`.
- Value objects: `SegmentStaticMemberIdVO`, `SegmentStaticMemberSourceTypeVO`.
- Creation: `SegmentStaticMember.create(...)`.
- Invariants:
    - metadata, when present, must be a mapping and is deep-copied;
    - source type is one of `manual`, `import`, `api`.
- Errors: `SegmentStaticMemberContactNotFoundError`, `SegmentStaticMemberArchivedSegmentError`,
  `SegmentStaticMemberNonStaticSegmentError`, base `SegmentStaticMemberError`.

### SegmentSnapshot

File: `domain/segment_snapshot/entity.py`

- Entity: `SegmentSnapshot`.
- Id VO: `SegmentSnapshotIdVO`; owner ids are `SegmentIdVO` and `SegmentVersionIdVO`.
- Fields: `segment_snapshot_id`, `segment_id`, `segment_version_id`, `status`, `member_count`, `started_at`,
  `completed_at`, `error_code`, `error_message`.
- Value objects: `SegmentSnapshotIdVO`, `SegmentSnapshotStatusVO`.
- Creation: `SegmentSnapshot.create(...)`.
- Lifecycle methods:
    - `start(now=...)`: `pending -> running`;
    - `complete(now=..., member_count=...)`: `running -> completed`;
    - `fail(now=..., error_code=..., error_message=...)`: `pending/running -> failed`.
- Invariants:
    - `member_count >= 0`;
    - failed snapshot requires non-empty error code and message;
    - completed snapshot is immutable.
- Errors: `InvalidSegmentSnapshotError`, `SegmentSnapshotNotFoundError`, `SegmentSnapshotTransitionError`,
  `SegmentSnapshotImmutableError`.

### SegmentSnapshotMember

File: `domain/segment_snapshot_member/entity.py`

- Entity: `SegmentSnapshotMember`.
- Id VO: `SegmentSnapshotMemberIdVO`; owner id is `SegmentSnapshotIdVO`; Contact id uses generic `EntityIdVO`.
- Fields: `segment_snapshot_member_id`, `segment_snapshot_id`, `contact_id`, `position`.
- Creation: `SegmentSnapshotMember.create(...)`.
- Invariant: `position` must be `None` or `>= 0`.
- Errors: `InvalidSegmentSnapshotMemberError`.

## Application Contracts

Commands, queries and DTOs are dataclasses. HTTP Pydantic schemas do not cross into application layer.

Command/query DTOs use `EntityIdVO` for tenant scope and concrete aggregate id VOs for segment-owned ids.

### Main Use Cases

| Use case                            | Input                             | Output                           | Main dependencies                                                                            |
|-------------------------------------|-----------------------------------|----------------------------------|----------------------------------------------------------------------------------------------|
| `CreateSegmentDefinitionUseCase`    | `CreateSegmentDefinitionCommand`  | `SegmentDefinitionDTO`           | definition command/query repositories, `UuidPort`                                            |
| `UpdateSegmentDefinitionUseCase`    | `UpdateSegmentDefinitionCommand`  | `SegmentDefinitionDTO`           | definition command/query repositories                                                        |
| `ArchiveSegmentDefinitionUseCase`   | `ArchiveSegmentDefinitionCommand` | `SegmentDefinitionDTO`           | definition command/query repositories, `ClockPort`                                           |
| `GetSegmentDefinitionUseCase`       | `GetSegmentDefinitionQuery`       | `SegmentDefinitionDTO`           | definition query repository                                                                  |
| `ListSegmentDefinitionsUseCase`     | `ListSegmentDefinitionsQuery`     | `list[SegmentDefinitionDTO]`     | definition query repository                                                                  |
| `PreviewSegmentDefinitionUseCase`   | `PreviewSegmentDefinitionQuery`   | `SegmentPreviewDTO`              | definition repository, evaluation service, Contact lookup                                    |
| `CreateSegmentVersionUseCase`       | `CreateSegmentVersionCommand`     | `SegmentVersionDTO`              | definition repository, version command/query repositories, DSL validator, `UuidPort`         |
| `ActivateSegmentVersionUseCase`     | `ActivateSegmentVersionCommand`   | `SegmentVersionDTO`              | definition repository, version command/query repositories, DSL validator, `ClockPort`        |
| `GetSegmentVersionUseCase`          | `GetSegmentVersionQuery`          | `SegmentVersionDTO`              | version query repository                                                                     |
| `ListSegmentVersionsUseCase`        | `ListSegmentVersionsQuery`        | `list[SegmentVersionDTO]`        | version query repository                                                                     |
| `PreviewSegmentConfigUseCase`       | `PreviewSegmentConfigCommand`     | `SegmentPreviewDTO`              | DSL validator, evaluation service, Contact lookup                                            |
| `PreviewSegmentVersionUseCase`      | `PreviewSegmentVersionQuery`      | `SegmentPreviewDTO`              | evaluation service, Contact lookup                                                           |
| `AddStaticMemberUseCase`            | `AddStaticMemberCommand`          | `StaticMemberDTO`                | definition repository, static member repositories, Contact lookup, `UuidPort`                |
| `RemoveStaticMemberUseCase`         | `RemoveStaticMemberCommand`       | `bool`                           | definition repository, static member command repository                                      |
| `ListStaticMembersUseCase`          | `ListStaticMembersQuery`          | `list[StaticMemberDTO]`          | static member query repository, Contact lookup                                               |
| `CreateSegmentSnapshotUseCase`      | `CreateSegmentSnapshotCommand`    | `SegmentSnapshotDTO`             | definition/version/snapshot/member repositories, evaluation service, `ClockPort`, `UuidPort` |
| `GetSegmentSnapshotUseCase`         | `GetSegmentSnapshotQuery`         | `SegmentSnapshotDTO`             | snapshot query repository                                                                    |
| `ListSegmentSnapshotsUseCase`       | `ListSegmentSnapshotsQuery`       | `list[SegmentSnapshotDTO]`       | definition repository, snapshot query repository                                             |
| `ListSegmentSnapshotMembersUseCase` | `ListSegmentSnapshotMembersQuery` | `list[SegmentSnapshotMemberDTO]` | snapshot query repository, snapshot member query repository, Contact lookup                  |

### Query And Repository Protocols

Domain command repository protocols:

- `SegmentDefinitionCommandRepositoryProtocol`;
- `SegmentVersionCommandRepositoryProtocol`;
- `SegmentStaticMemberCommandRepositoryProtocol`;
- `SegmentSnapshotCommandRepositoryProtocol`;
- `SegmentSnapshotMemberCommandRepositoryProtocol`.

Application query ports:

- `SegmentDefinitionQueryRepositoryProtocol`;
- `SegmentVersionQueryRepositoryProtocol`;
- `SegmentStaticMemberQueryRepositoryProtocol`;
- `SegmentSnapshotQueryRepositoryProtocol`;
- `SegmentSnapshotMemberQueryRepositoryProtocol`;
- `ContactLookupProtocol`;
- `StaticContactAudienceQueryProtocol`;
- `ContactAudienceQueryProtocol`;
- `RuntimeObjectMetadataProtocol`;
- `RuntimeFilterValidatorProtocol`.

## Segment Version DSL

DSL lives under `application/segment_version/dsl`.

Raw config is parsed into:

- `SegmentVersionDslConfig`;
- `SegmentVersionDslRule`;
- `SegmentVersionContactMapping`.

Canonical config shape:

```json
{
  "root_object": "contact",
  "include": [],
  "exclude": [],
  "inherit_include_segment_ids": [],
  "inherit_exclude_segment_ids": []
}
```

Rules must contain exactly:

- `rule_id`;
- `object`;
- `relation_path`;
- `contact_mapping`;
- `filter`.

Validator behavior:

- `root_object` must be `contact`;
- unknown top-level keys are rejected;
- `rule_id` is required and unique across include/exclude;
- include/exclude rule counts are capped at 10 each;
- inherited include/exclude segment counts are capped at 10 each;
- inherited segments must exist, must not be archived, must not duplicate each other, and must not reference the current
  segment;
- relation path items use `<source_object>.<relation_name>`;
- relation path depth is limited to 2 during validation;
- Contact self rules require empty `relation_path` and `{"type":"self","field":"id"}`;
- non-contact rules require `{"type":"field", ...}` where the field matches the relation FK back to Contact and is
  `uuid` or `reference`;
- filters are validated through current `runtime_data` `FilterDslParser` + `FilterSemanticValidator`.

`CreateSegmentVersionUseCase` and `ActivateSegmentVersionUseCase` validate config, dump canonical JSON-like config and
compute
`config_checksum` via deterministic SHA-256 over sorted compact JSON.

## Evaluation And Preview

Evaluation code lives under `application/segment_version/evaluation`.

Main classes:

- `SegmentVersionRuleExecutor`;
- `SegmentVersionInheritanceEvaluator`;
- `SegmentVersionEvaluationService`;
- `SegmentVersionEvaluationOptions`;
- `SegmentVersionEvaluationResult`.

Evaluation behavior:

- accepts raw or typed DSL config through the same validator;
- executes include rules in declaration order;
- evaluates inherited include segments;
- executes exclude rules and inherited exclude segments;
- removes excluded Contact ids;
- dedupes while preserving first include order;
- applies final `offset`/`limit` after dedupe/exclude;
- returns `count == len(returned contact_ids)`.

Static inherited segments are read through `StaticContactAudienceQueryProtocol`.
Dynamic inherited segments use active segment versions. Missing active dynamic version raises
`SegmentVersionActiveVersionNotFoundError`.

Inheritance detection:

- cycle detection uses visited `SegmentIdVO`;
- max nested inheritance depth is 3.

Runtime evaluator support is intentionally limited:

- Contact self rules are supported;
- direct related-object rules with a Contact mapping field are supported;
- deeper relation traversal is rejected by `SegmentVersionEvaluationUnsupportedRelationPathError`.

Preview use cases return `SegmentPreviewDTO`. `total` is always `None`; `has_more` is computed as `count == limit`.
If `include_contact_summary=false`, Contact summaries are not loaded.

## Snapshot Flow

`CreateSegmentSnapshotUseCase` creates snapshots synchronously.

Flow:

1. Load segment definition.
2. Reject missing or archived segment.
3. Resolve explicit `segment_version_id` or active version.
4. Save pending snapshot.
5. Mark snapshot running.
6. Evaluate Contact audience:
    - static segment uses static members;
    - dynamic segment evaluates the resolved version.
7. Deduplicate Contact ids preserving order.
8. Insert frozen `segment_snapshot_member` rows with deterministic `position`.
9. Complete snapshot with `member_count`.

If a controlled `DomainError` happens after the snapshot is created, members for that snapshot are deleted, snapshot is
saved
as `failed` with `error_code/error_message`, and the original error is re-raised to the caller.

## Infrastructure / Persistence

All repositories/adapters live under `src/modules/segmentation/infrastructure`.

| Adapter                                  | Protocols                            | Runtime object(s)         | Notes                                                                                                                  |
|------------------------------------------|--------------------------------------|---------------------------|------------------------------------------------------------------------------------------------------------------------|
| `SegmentDefinitionRuntimeRepository`     | definition command/query             | `segment_definition`      | insert/update by id, list sorted `created_at asc, id asc`                                                              |
| `SegmentVersionRuntimeRepository`        | version command/query                | `segment_version`         | advisory lock for next version number, active version lookup, archive active versions                                  |
| `SegmentStaticMemberRuntimeRepository`   | static member command/query          | `segment_static_member`   | advisory lock per tenant+segment+contact, duplicate add is idempotent, remove deletes found row id                     |
| `SegmentSnapshotRuntimeRepository`       | snapshot command/query               | `segment_snapshot`        | insert/update snapshot, list sorted `created_at desc, id desc`                                                         |
| `SegmentSnapshotMemberRuntimeRepository` | snapshot member command/query        | `segment_snapshot_member` | bulk member inserts, duplicate persistence race is reread-tolerant, list sorted `position asc, created_at asc, id asc` |
| `RuntimeContactLookupAdapter`            | `ContactLookupProtocol`              | `contact`                 | uses runtime object `contact`; no CRM domain import                                                                    |
| `RuntimeContactAudienceQuery`            | `ContactAudienceQueryProtocol`       | dynamic rule object       | maps runtime rows to Contact ids                                                                                       |
| `StaticContactAudienceRuntimeQuery`      | `StaticContactAudienceQueryProtocol` | `segment_static_member`   | returns static Contact ids sorted by member creation order                                                             |
| `RuntimeObjectMetadataAdapter`           | `RuntimeObjectMetadataProtocol`      | schema metadata           | resolves objects/fields/relations with public singular object names                                                    |
| `RuntimeFilterValidatorAdapter`          | `RuntimeFilterValidatorProtocol`     | runtime descriptor        | wraps runtime filter parser/semantic validator errors into DSL errors                                                  |

Tenant scope is always passed as `EntityIdVO` method parameter; repositories do not store tenant id in instance state.

Runtime gateways:

- read paths use `RuntimeQueryGateway`;
- write paths use `RuntimeCommandGateway`;
- query filters use `RuntimeTypedFilterBuilder`;
- pagination uses `PageSpec`;
- sorting uses `SortSpec`.

PostgreSQL advisory transaction locks are used for:

- `segmentation_segment_version:{tenant_id}:{segment_id}` while calculating next version number;
- `segmentation_static_member:{tenant_id}:{segment_id}:{contact_id}` while adding/removing static members.

## HTTP API

All routes require authenticated request context. Controllers explicitly read:

```python
principal = context.principal
if principal is None or principal.tenant_id is None:
    raise HTTPException(status_code=401, detail="Unauthorized.")
```

Controllers build application command/query objects, call one use case, and explicitly construct Pydantic response
schemas.

| Method   | Path                                                               | Controller                      | Use Case                            | Request                                                      | Response                                   |
|----------|--------------------------------------------------------------------|---------------------------------|-------------------------------------|--------------------------------------------------------------|--------------------------------------------|
| `POST`   | `/api/segments`                                                    | `create_segment_definition`     | `CreateSegmentDefinitionUseCase`    | `CreateSegmentDefinitionRequestSchema`                       | `SegmentDefinitionResponseSchema`          |
| `GET`    | `/api/segments`                                                    | `list_segment_definitions`      | `ListSegmentDefinitionsUseCase`     | query `limit=50`, `offset=0`                                 | `ListSegmentDefinitionsResponseSchema`     |
| `GET`    | `/api/segments/{segment_id}`                                       | `get_segment_definition`        | `GetSegmentDefinitionUseCase`       | path UUID                                                    | `SegmentDefinitionResponseSchema`          |
| `PATCH`  | `/api/segments/{segment_id}`                                       | `update_segment_definition`     | `UpdateSegmentDefinitionUseCase`    | `UpdateSegmentDefinitionRequestSchema`                       | `SegmentDefinitionResponseSchema`          |
| `POST`   | `/api/segments/{segment_id}/archive`                               | `archive_segment_definition`    | `ArchiveSegmentDefinitionUseCase`   | path UUID                                                    | `SegmentDefinitionResponseSchema`          |
| `POST`   | `/api/segments/preview`                                            | `preview_segment_config`        | `PreviewSegmentConfigUseCase`       | `PreviewSegmentConfigRequestSchema`                          | `SegmentPreviewResponseSchema`             |
| `POST`   | `/api/segments/{segment_id}/preview`                               | `preview_segment_definition`    | `PreviewSegmentDefinitionUseCase`   | `PreviewSegmentDefinitionRequestSchema`                      | `SegmentPreviewResponseSchema`             |
| `POST`   | `/api/segments/{segment_id}/versions`                              | `create_segment_version`        | `CreateSegmentVersionUseCase`       | `CreateSegmentVersionRequestSchema`                          | `SegmentVersionResponseSchema`             |
| `GET`    | `/api/segments/{segment_id}/versions`                              | `list_segment_versions`         | `ListSegmentVersionsUseCase`        | query `limit=50`, `offset=0`                                 | `ListSegmentVersionsResponseSchema`        |
| `GET`    | `/api/segments/{segment_id}/versions/{version_id}`                 | `get_segment_version`           | `GetSegmentVersionUseCase`          | path UUIDs                                                   | `SegmentVersionResponseSchema`             |
| `POST`   | `/api/segments/{segment_id}/versions/{version_id}/activate`        | `activate_segment_version`      | `ActivateSegmentVersionUseCase`     | path UUIDs                                                   | `SegmentVersionResponseSchema`             |
| `POST`   | `/api/segments/{segment_id}/versions/{segment_version_id}/preview` | `preview_segment_version`       | `PreviewSegmentVersionUseCase`      | `PreviewSegmentVersionRequestSchema`                         | `SegmentPreviewResponseSchema`             |
| `POST`   | `/api/segments/{segment_id}/static-members`                        | `add_static_member`             | `AddStaticMemberUseCase`            | `AddStaticMemberRequestSchema`                               | `StaticMemberResponseSchema`               |
| `GET`    | `/api/segments/{segment_id}/static-members`                        | `list_static_members`           | `ListStaticMembersUseCase`          | query `limit=50`, `offset=0`, `include_contact_summary=true` | `ListStaticMembersResponseSchema`          |
| `DELETE` | `/api/segments/{segment_id}/static-members/{contact_id}`           | `remove_static_member`          | `RemoveStaticMemberUseCase`         | path UUIDs                                                   | `204 No Content`                           |
| `POST`   | `/api/segments/{segment_id}/snapshots`                             | `create_segment_snapshot`       | `CreateSegmentSnapshotUseCase`      | `CreateSegmentSnapshotRequestSchema`                         | `SegmentSnapshotResponseSchema`            |
| `GET`    | `/api/segments/{segment_id}/snapshots`                             | `list_segment_snapshots`        | `ListSegmentSnapshotsUseCase`       | query `limit=50`, `offset=0`                                 | `ListSegmentSnapshotsResponseSchema`       |
| `GET`    | `/api/segments/snapshots/{segment_snapshot_id}`                    | `get_segment_snapshot`          | `GetSegmentSnapshotUseCase`         | path UUID                                                    | `SegmentSnapshotResponseSchema`            |
| `GET`    | `/api/segments/snapshots/{segment_snapshot_id}/members`            | `list_segment_snapshot_members` | `ListSegmentSnapshotMembersUseCase` | query `limit=50`, `offset=0`, `include_contact_summary=true` | `ListSegmentSnapshotMembersResponseSchema` |

List responses use `{items, count}` where `count == len(items)`.

Common HTTP error mapping:

- missing principal/tenant -> `401`;
- missing segment/version/snapshot/contact -> `404`;
- archived segment, non-static member mutation, missing active version, unsupported relation path, runtime/schema
  conflict -> `409`;
- DSL validation, domain validation, runtime filter/validation errors -> `422`.

## Dependency Injection

DI lives in `src/modules/segmentation/presentation/depends`.

`infrastructure.py` builds:

- `PostgresRuntimeQueryGateway` and `PostgresRuntimeCommandGateway` from shared `UoWDep`;
- `RuntimeFieldTypePolicy`;
- repositories for definitions, versions, static members, snapshots and snapshot members;
- Contact lookup and audience query adapters;
- runtime metadata and runtime filter validator adapters.

Shared external DI:

- `UoWDep`;
- `RuntimeObjectResolverDep`;
- `ObjectServiceDep`;
- `ClockDep`;
- `UuidDep`.

`application.py` builds:

- all command/query use cases;
- `SegmentVersionDslConfigValidator`;
- `SegmentVersionRuleExecutor`;
- `SegmentVersionInheritanceEvaluator`;
- `SegmentVersionEvaluationService`.

## Dependencies On Other Modules

Real outgoing dependencies:

- `shared`: `EntityIdVO`, `DomainError`, `ClockPort`, `UuidPort`, request context, UoW dependencies;
- `schema_registry`: runtime object resolver, runtime descriptors, object service and schema errors;
- `runtime_data`: runtime command/query gateways, typed filter builder, filter DSL parser/semantic validator, page/sort
  specs.

The module queries the runtime object named `contact` through `RuntimeContactLookupAdapter`, but does not import CRM
domain,
CRM repositories or Contact entity classes.

Architecture tests assert no imports from:

- `broadcast`;
- `campaigns`;
- `communication`;
- `contact_point`.

## Tests Covering This Module

Segmentation-specific tests:

- `test/test_segmentation_module.py`;
- `test/test_segmentation_lifecycle_domain.py`;
- `test/test_segmentation_segment_definition_use_cases.py`;
- `test/test_segmentation_segment_version_use_cases.py`;
- `test/test_segmentation_segment_version_dsl.py`;
- `test/test_segmentation_segment_version_evaluation.py`;
- `test/test_segmentation_static_member_use_cases.py`;
- `test/test_segmentation_preview_use_case.py`;
- `test/test_segmentation_preview_api.py`;
- `test/test_segmentation_runtime_repository.py`;
- `test/test_segmentation_http_router.py`;
- `test/test_segmentation_snapshot_use_case.py`;
- `test/test_segmentation_snapshot_runtime_repository.py`;
- `test/test_segmentation_snapshot_api.py`.

Cross-module coverage:

- `test/test_inventory_schema_seed.py` verifies segmentation runtime seed objects, fields, indexes and relations;
- `test/test_architecture_boundaries.py` verifies forbidden imports, absence of generic `segment/*` packages, controller
  shape
  and request schema file shape.

## Known Gaps / Technical Debt

- `SegmentDefinition` and `SegmentVersion` still do primitive normalization/coercion in entity `__post_init__`.
  Static member and snapshot entities use the newer `create(...)` style with already prepared value objects.
- `SegmentStatusVO` and seed include `active`, but code does not expose a segment-definition activation use case or HTTP
  route.
  Version activation exists separately.
- Some package `__init__.py` files contain an initial empty `__all__` assignment before the final exported `__all__`.
  This is import-safe but noisy.
- DSL validation allows relation path depth up to 2, while the current evaluator executes only Contact self rules and
  direct
  related-object rules. Deeper relation traversal is rejected at evaluation time.
- Snapshot creation is synchronous. There is no background worker, retry, progress polling model or async job
  integration in
  this module.

## Source Of Truth

Primary source:

- `src/modules/segmentation/`.

Important files:

- `src/modules/segmentation/domain/*/entity.py`;
- `src/modules/segmentation/application/*/use_case/*.py`;
- `src/modules/segmentation/application/segment_version/dsl/*.py`;
- `src/modules/segmentation/application/segment_version/evaluation/*.py`;
- `src/modules/segmentation/infrastructure/*.py`;
- `src/modules/segmentation/presentation/http/router.py`;
- `src/modules/segmentation/presentation/http/*/controllers/*.py`;
- `src/modules/segmentation/presentation/depends/*.py`;
- `src/modules/schema_registry/seed/schema_seed.py`;
- tests listed in this document.

Related docs:

- [Inventory Module](./inventory.md)
- [CRM Module](./crm.md)
- [Runtime Data Module](./runtime-data.md)
- [Schema Registry Module](./schema-registry.md)
