# Persistence and Unit of Work

`DatabaseHelper` owns the async SQLAlchemy engine, session factory, startup retry and disposal. Startup `create_all` targets only global `Base.metadata`.

Static tenant tables (`warehouses`, `users`, `user_emails`) inherit `TenantBase`. They are created and evolved exclusively by tenant Alembic revisions, not startup `create_all`.

## Transaction boundaries

`UnitOfWork` creates a session on entry, commits on success and rolls back on failure. Session close runs in `finally`, including when commit/rollback fails.

HTTP dependencies share the same UoW session across repositories, identity provisioning and schema bootstrap. The bootstrap adapter creates the schema and runs Alembic using that connection. Administrator and email insertion follows successful bootstrap on the same session. The migrator and identity repository have no internal commit, so PostgreSQL DDL and all onboarding records are atomic, including a failure after administrator insertion.

Management `upgrade --all` uses a separate UoW for each tenant. Failed tenants are rolled back; successful tenants remain upgraded. Migration generation uses a separate engine for reflection.

## Identity schema selection

Identity repositories receive an explicit `EntityIdVO` tenant scope for every operation. `TenantSchemaNaming` determines the physical schema. SQLAlchemy Core statements built from tenant model tables apply their own `schema_translate_map`; they do not change the shared engine, connection options or `search_path`, or keep tenant users in the ORM identity map. Multiple tenant operations on one session therefore remain isolated even with equal record IDs. The domain `User.tenant_id` is reconstructed from that scope rather than persisted as a column.

## Related

- [Tenant migrations](../data/tenant-migrations.md)
- [Dependency injection](dependency-injection.md)
- [Shared](../modules/shared.md)
