# Persistence and Unit of Work

`DatabaseHelper` owns the async SQLAlchemy engine, session factory, startup retry and disposal. Startup `create_all` targets only global `Base.metadata`.

Static tenant tables inherit `TenantBase`. They are created and evolved exclusively by tenant Alembic revisions, not startup `create_all`.

## Transaction boundaries

`UnitOfWork` creates a session on entry, commits on success and rolls back on failure. Session close runs in `finally`, including when commit/rollback fails.

HTTP dependencies share the same UoW session across repositories, identity provisioning and schema bootstrap. The bootstrap adapter creates the schema and runs Alembic using that connection. The migrator has no internal commit, so PostgreSQL DDL and all onboarding records are atomic.

Management `upgrade --all` uses a separate UoW for each tenant. Failed tenants are rolled back; successful tenants remain upgraded. Migration generation uses a separate engine for reflection.

## Related

- [Tenant migrations](../data/tenant-migrations.md)
- [Dependency injection](dependency-injection.md)
- [Shared](../modules/shared.md)
