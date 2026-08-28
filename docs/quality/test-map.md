# Test Map

This page maps current tests to the behaviors they protect.

## Architecture Boundaries

- `test/test_architecture_boundaries.py`
    - protects `tenancy.application -> schema_registry.application` boundary
    - protects `schema_registry.domain` from PostgreSQL/migration implementation leakage
    - checks that removed legacy paths are no longer used
  - checks that removed `identity` `error_mapper` and `infrastructure.mapper` paths are no longer used
  - protects the single `EntityIdVO` identifier style and concrete id inheritance

## Tenancy And Bootstrap Boundary

- `test/test_tenancy_create_tenant_use_case.py`
    - tenant creation orchestration
- `test/test_tenant_schema_bootstrap_boundary.py`
    - tenancy-owned bootstrap context and adapter contract
- `test/test_tenancy_http_router.py`
    - guards public tenancy route registration

## Schema Registry

- `test/test_schema_registry_seed_service.py`
    - seed loading and validation
- `test/test_schema_registry_metadata_read_service.py`
    - metadata snapshot consistency
- `test/test_schema_registry_metadata_write_service.py`
    - metadata reconcile identity preservation
- `test/test_schema_registry_diff_use_case.py`
    - diff orchestration rules
- `test/test_schema_registry_planning.py`
    - create/diff plan building, relation uniqueness, unsafe required-column rejection
- `test/test_schema_registry_postgres_executor.py`
    - SQL rendering/execution behavior for migration operations
- `test/test_schema_registry_repositories.py`
    - repository mapping and flush ordering
- `test/test_schema_registry_depends.py`
    - session-bound dependency composition
- `test/test_management_schema_registry_command.py`
    - management CLI behavior for schema diff

## Identity

- `test/test_identity_use_cases.py`
    - request/confirm OTP flow
  - OTP email delivery failure fallback
    - session authentication
    - current user profile read/update
    - logout
    - tenant admin provisioning service
- `test/test_identity_http_router.py`
    - public identity route registration
    - session cookie set/delete behavior
  - tenant-aware per-controller HTTP error mapping

## Shared

- `test/test_shared_typed_entity_id.py`
    - `EntityIdVO` conversion from UUID/string/base id
    - concrete id classes inherit base behavior and are not equal for the same UUID
- `test/test_shared_email_service.py`
  - typed email service rendering for system email kinds
  - provider factory selection
  - SMTP transport message building
  - SMTP vs SMTP SSL transport choice
  - `resend` placeholder behavior
- `test/test_shared_events.py`
    - integration event serialization
    - outbox publish success, retry and max-attempt failure behavior
    - inbox idempotency for duplicate delivery
    - shared RabbitMQ event publisher topology and message metadata
- `test/test_event_bus_management_command.py`
    - shared event management command parsing and handler behavior
- `test/test_scheduled_jobs.py`
    - scheduled job serialization and scheduling behavior
    - due processing success, retry, exhausted attempts and missing handler retry path
    - SQLAlchemy repository claim, token-guarded completion/failure, cancel and stuck recovery behavior
    - optional PostgreSQL concurrent claim behavior when `DNK_TEST_DATABASE_URL` is set
- `test/test_jobs_management_command.py`
    - scheduled jobs management command parsing and handler behavior

## Schema Seed Cleanup

- `test/test_default_schema_seed.py`
  - empty runtime default seed normalization
  - schema-only tenant bootstrap plan without predefined system tables
  - tenant bootstrap forwards the empty runtime seed to metadata creation
- `test/test_removed_module_boundaries.py`
  - removed module directories and HTTP surfaces remain absent
  - removed CLI/configuration surfaces remain unavailable

## Runtime Data

- `test/test_runtime_data_postgres_gateway.py`
    - nested AND/OR runtime filter SQL generation

## Schema Config

- `test/test_schema_config_object_controller.py`
    - object describe HTTP error mapping
- `test/test_schema_config_repository.py`
    - object metadata creation and targeted DDL planning
    - object kind policy for system/view/standard/custom
    - field kind policy and unsafe required field addition rejection
- `test/test_schema_config_http_router.py`
    - public `/api/config/objects/...` route registration

## Legacy / Historical Naming

- some old test names still use `runtime_schema_*`
- these reflect earlier naming/history of the schema subsystem
- when using the test suite as project map, prefer the newer `schema_registry_*` cluster as the current terminology

## How To Use This Map

- start from module page
- jump to related tests from here
- use the tests as executable examples of current behavior and architecture boundaries

## Related

- [Constraints and conventions](constraints-and-conventions.md)
- [Schema Registry module](../modules/schema-registry.md)
- [Tenancy module](../modules/tenancy.md)

## Source Of Truth

- `test/`
