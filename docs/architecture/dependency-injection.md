# Dependency Injection

HTTP composition lives in module `presentation/depends` functions using FastAPI `Depends` and `Annotated` aliases. Repositories and adapters receive the same request-scoped UoW session. Tenant identifiers are passed explicitly through commands/repository methods; client-data wiring does not bind a repository instance to a tenant.

## Tenant onboarding

`get_tenant_schema_bootstrap_port` assembles `AlembicTenantSchemaBootstrapAdapter` using `uow.session` and the shared `TenantMigrator`. The use case sees only `TenantSchemaBootstrapPort`. Its context contains tenant id and schema name, with no seed path or runtime metadata.

## Management

`tenancy/presentation/depends/management.py` builds migration command dependencies. `TenantMigrationManagement.run_one` owns one UoW per tenant. Revision generation opens a separate engine exclusively for reflection, avoiding mutation of the application's shared dialect.

Events and jobs retain their shared presentation builders. Inventory has no use-case or HTTP DI graph yet.

## Related

- [Persistence and UoW](persistence-and-uow.md)
- [Management CLI](../interfaces/management-cli.md)
- [Tenancy](../modules/tenancy.md)
