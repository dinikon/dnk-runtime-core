# Tenant migrations

## Ownership

Alembic owns both global and static tenant tables. Global revisions live in `migrations/global/`; run `dnk-manage database upgrade` before starting API and workers. Startup only checks their version. The fresh global baseline refuses an existing unversioned database rather than adopting or deleting its tables. No dynamic object subsystem is active.

Tenant models use `TenantBase` with logical schema `tenant`. `src/modules/tenant_persistence.py` registers model imports and historical table names. Retain historical names after removing a model so autogenerate can detect its removal. Unregistered legacy tables are excluded from reflection candidates; they are never adopted or deleted automatically.

## Schema identity

`TenantSchemaNaming` builds `SCHEMA_PREFIX + tenant_id.uuid.hex`. `SCHEMA_PREFIX` defaults to `dnk_` and must remain stable for an installation. Changing it requires an explicit schema relocation; there is no datasource metadata lookup or fallback schema discovery.

## New tenants

`CreateTenantUseCase` creates the tenant and primary domain, invokes the tenancy-owned bootstrap port, then provisions the administrator and email in the migrated schema. `AlembicTenantSchemaBootstrapAdapter` uses the same UoW session to acquire a schema lock, reject an existing schema, create it and upgrade to `head`.

The adapter and migrator never commit. PostgreSQL DDL, Alembic version writes, tenant, domain, owner identity and cloud connection writes commit together. Any failure rolls everything back. The Control Plane installer records accepted-command errors in its durable attempt state and reconciles actual resources before declaring absence.

## Revisions

Files live in `migrations/tenant/versions/`; each tenant schema has its own `alembic_version`. The first revision is `0001_warehouses`; `0002_identity_users` adds tenant-local `users` and `user_emails` with a same-schema foreign key. `0003_identity_cloud_access` adds roles, session epochs, cloud identities, invitations and live normalized-email uniqueness. Revisions contain no fixed tenant names and do not import current ORM models.

The migration environment uses transaction-local `search_path` (through PostgreSQL `set_config(..., true)`) and explicitly sets `version_table_schema`. Successful execution restores the previous path. Failed transactions are rolled back by the owner. Migration files must preserve transactional execution: no internal commit, autocommit block or nontransactional DDL in onboarding revisions.

An in-process lock protects Alembic's global context proxies; a schema-specific advisory transaction lock serializes separate workers/processes. The database lock is acquired before the process lock to avoid holding the latter while waiting for another transaction's commit.

## Transition from shared identity tables

The shared-users transition requires recreating development/test databases and repeating tenant onboarding. `0002_identity_users` creates empty tables; it does not migrate or delete records in `public.users` or `public.user_emails`. Startup no longer creates those shared tables, and runtime identity access has no legacy fallback. Running `upgrade --all` on an old installation creates the new tables but does not make its old users available.

## Existing tenants

```sh
dnk-manage tenant-migrations current <tenant_id>
dnk-manage tenant-migrations current --all
dnk-manage tenant-migrations upgrade <tenant_id>
dnk-manage tenant-migrations upgrade --all
```

Commands verify tenant existence and require its calculated schema to exist. They never create missing schemas. `current` reports `base` for an unversioned schema without creating `alembic_version`.

`--all` processes tenants sequentially, one transaction per tenant. It continues after failures, retains successful upgrades and exits 2 if any tenant failed. Re-running upgrades is safe. No mass upgrade runs at application startup.

## Authoring migrations

```sh
dnk-manage tenant-migrations revision --autogenerate --tenant-id <tenant_id> -m "Add a warehouse field"
```

Use a development tenant already at the current head. Change the ORM model, generate a candidate revision, review it and then apply it. Include newly managed table names in the registration history; do not delete names when retiring tables.

Autogenerate uses a separate engine and a schema-free metadata copy, rewriting tenant foreign keys to the same copy. The application's metadata and engine dialect are not modified. SQL types and server defaults are compared; shared `StringUUID` renders as `sa.UUID()` to keep revisions independent of application decorators.

Review renames, destructive changes and CHECK expressions manually. Longer warehouse cycles remain outside this version's guarantees. Downgrade is available through the internal migrator/Alembic environment for reviewed operations and tests; no bulk downgrade command is exposed.

## Verification and deployment

CI starts PostgreSQL 16 and sets `TEST_POSTGRES_URL` to a disposable database. Tests cover full onboarding, rollback, two tenants, constraints, upgrades/downgrades, generated revision execution and concurrency across processes. Local integration tests skip only when this variable is absent; they do not fall back to the application's database URL.

Control Plane v1 targets a fresh database. Migration or adoption of existing installations is outside this release; no command automatically deletes an old database. For subsequent releases on a versioned v1 database, deploy the migration files, upgrade global tables and use `upgrade --all` for tenant revisions before starting the matching workers. New tenants use the deployed head automatically.

## Related

- [Inventory](../modules/inventory.md)
- [Tenancy](../modules/tenancy.md)
- [Persistence and UoW](../architecture/persistence-and-uow.md)
- [Historical dynamic schema](../history/data/runtime-schema.md)
