# Test Map

This page maps current tests to the behaviors they protect.

## Architecture Boundaries

- `test/test_architecture_boundaries.py`
    - protects `tenancy.application -> schema_registry.application` boundary
    - protects `schema_registry.domain` from PostgreSQL/migration implementation leakage
    - checks that removed legacy paths are no longer used

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
    - session authentication
    - current user profile read/update
    - logout
    - tenant admin provisioning service
- `test/test_identity_http_router.py`
    - public identity route registration
    - session cookie set/delete behavior
    - tenant-aware HTTP error mapping

## CRM

- `test_crm_*`
    - CRM endpoints and domain/use case behavior around contacts

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
