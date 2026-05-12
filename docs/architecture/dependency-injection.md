# Dependency Injection

## Current Pattern

The project uses explicit composition functions instead of a large global container.

- HTTP composition lives in `presentation/depends/` inside each module.
- Management composition uses dedicated builders, for example `schema_registry/presentation/depends/management.py`.
- Shared request-scoped objects such as `UnitOfWork` are exposed through `src/modules/shared/depends/`.

## HTTP Composition

- FastAPI controllers depend on typed aliases like `CreateTenantUseCaseDep` or `AuthenticatedRequestContextDep`.
- These aliases are built from `Depends(...)` functions inside module-specific `presentation/depends/*`.
- Repositories and adapters are assembled from the same request-scoped `uow.session`.
- Client-data module wiring stays tenant-agnostic: it assembles repositories/gateways only. Controllers read tenant from
  the authenticated request context and pass `tenant_id` through command/query DTOs and use cases.
- In `tenancy`, DI now wires use cases from `application/tenant/use_case/` and
  `application/tenant_domain/use_case/` while keeping the public dependency
  aliases stable for the rest of the codebase.
- In `identity`, `presentation/depends/infrastructure.py` builds repository,
  token-store, tenant-context and settings dependencies, while
  `presentation/depends/application.py` composes auth use cases and
  `UserService`. Controllers call identity use cases through `await use_case(...)`.

## Management Composition

- `dnk-manage` does not use FastAPI `Depends`.
- Command handlers explicitly open `UnitOfWork` and call a builder.
- Example: schema diff command builds `DiffSchemaUseCase` from the active `uow.session`.

## Important Boundary

- `tenancy` does not directly depend on `CreateSchemaUseCase`.
- It uses tenancy-owned port `TenantSchemaBootstrapPort` and `TenantSchemaBootstrapContextFactory`.
- `schema_registry` provides the adapter that translates the context into `CreateSchemaCommand`.

## Session-Bound Wiring

- One active `UnitOfWork` owns one `AsyncSession`.
- Repositories, PostgreSQL inspectors/executors and schema bootstrap use that same session.
- This is especially important for nested `CreateTenant -> CreateSchema` flow and for `schema_registry` diff execution.

## Related

- [Request lifecycle](request-lifecycle.md)
- [Persistence and Unit of Work](persistence-and-uow.md)
- [Tenancy module](../modules/tenancy.md)
- [Schema Registry module](../modules/schema-registry.md)

## Source Of Truth

- `src/modules/shared/depends/uow.py`
- `src/modules/tenancy/presentation/depends/application.py`
- `src/modules/tenancy/application/tenant/use_case/`
- `src/modules/tenancy/application/tenant_domain/use_case/`
- `src/modules/identity/presentation/depends/application.py`
- `src/modules/identity/presentation/depends/infrastructure.py`
- `src/modules/communication/presentation/depends/application.py`
- `src/modules/communication/presentation/depends/infrastructure.py`
- `src/modules/communication/presentation/depends/management.py`
- `src/modules/schema_registry/presentation/depends/application.py`
- `src/modules/schema_registry/presentation/depends/management.py`
