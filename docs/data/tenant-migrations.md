# Tenant migrations

> The revision history below describes the current code. The
> [CatalogItem rewrite plan](../plan/catalog.md) replaces all Catalog revisions
> for a fresh database and rewires the remaining tenant chain. Those migration
> changes have not been implemented by the documentation update.

## Ownership

Alembic owns both global and static tenant tables. Global revisions live in `migrations/global/`; run `dnk-manage database upgrade` before starting API and workers. Startup only checks their version. The fresh global baseline refuses an existing unversioned database rather than adopting or deleting its tables. No dynamic object subsystem is active.

Global revision `0006_reference_data` adds the four public reference catalogs, country/time-zone links and synchronization state. It also permits `scheduled_jobs.tenant_id=NULL` for global jobs. After upgrading and before exposing the reference-data GET routes, run `dnk-manage reference-data sync --dataset all`; subsequent refreshes are registered by the shared jobs worker every seven days. The catalogs do not require tenant migrations.

Tenant models use `TenantBase` with logical schema `tenant`. `src/modules/tenant_persistence.py` registers model imports and historical table names. Retain historical names after removing a model so autogenerate can detect its removal. Unregistered legacy tables are excluded from reflection candidates; they are never adopted or deleted automatically.

## Schema identity

`TenantSchemaNaming` builds `SCHEMA_PREFIX + tenant_id.uuid.hex`. `SCHEMA_PREFIX` defaults to `dnk_` and must remain stable for an installation. Changing it requires an explicit schema relocation; there is no datasource metadata lookup or fallback schema discovery.

## New tenants

`CreateTenantHandler` validates the requested base currency against active Reference Data before creating resources, creates the tenant and primary domain, invokes the tenancy-owned bootstrap port, initializes `tenant_currency_settings` in that schema, then provisions the administrator and email. The currency-settings migration seeds existing schemas with UAH; new onboarding replaces that initial value with the validated selection in the same transaction. `AlembicTenantSchemaBootstrapAdapter` uses the same UoW session to acquire a schema lock, reject an existing schema, create it and upgrade to `head`.

The adapter and migrator never commit. PostgreSQL DDL, Alembic version writes, tenant, domain, owner identity and cloud connection writes commit together. Any failure rolls everything back. The Control Plane installer records accepted-command errors in its durable attempt state and reconciles actual resources before declaring absence.

## Revisions

Files live in `migrations/tenant/versions/`; each tenant schema has its own `alembic_version`. The first revision is
`0001_warehouses`; `0002_identity_users` adds tenant-local `users` and `user_emails` with a same-schema foreign key.
`0003_identity_cloud_access` adds roles, session epochs, cloud identities, invitations and live normalized-email
uniqueness. Revisions `0004` through `0006` add partner price-list ingestion and management. Revision
`0007_crm_contacts_companies` adds the static CRM `contacts` and `companies` tables, validation checks and stable-sort
indexes. Revision `0008_contact_points` creates the tenant-local directory, bindings and labels with same-schema
foreign keys. It seeds six labels with fixed identifiers and timestamps; seed actors are null. Upgrade existing
tenants before running code that reads the new CRM arrays. Existing CRM rows are preserved with empty arrays.
Revision `0011_inventory_skus`, after `0010_crm_company_legal_name`, adds the tenant-local
Inventory `skus` directory with unique codes and audit fields; this revision remains
in the migration history after removal of the module.
Catalog now uses a fresh `0023_catalog_item` baseline after
`0022_tenant_currency_settings`. It creates `catalog_item` for simple, variable
and variant nodes, normalized content/media/enum/classification links and the
fixed Default schema. The 2026-10-15 rebuild removes scalar override modes,
uses boolean stock management and stores each measurement as a nullable value/unit
pair (g/kg for weight, cm/m for each dimension). Revision identity remains
0023_catalog_item; 0024_currency_exchange_rates still depends on it. It does not
migrate old Product/Variant rows or existing CatalogItem data.

The five Catalog revisions 0012/0015/0017/0018/0019 are removed. Only chain links
in preserved migrations change: 0013 -> 0011, 0016 -> 0014, 0020 -> 0016. Files
0020/0021 and currency settings 0022 remain intact. There is one tenant head.
Downgrade from 0023 to 0022 removes only the new Catalog; upgrading recreates its empty
schema and Default seed. The historical baseline rebuild required fresh database
recreation; subsequent incremental migrations do not require it. No command here
automatically drops the application database.

Revision `0026_catalog_attribute_ids`, after `0025_user_display_currency`, removes
only the `code` columns and their uniqueness constraints from `catalog_attributes`
and `catalog_attribute_options`. IDs, translations, positions, assignments and
foreign keys remain intact, including future variation storage. Apply it together
with the new backend and Console: the previous backend requires those columns.
Downgrade recreates unique technical codes from UUIDs (`a_` / `o_` prefixes),
not the original code values; recovering those values requires a backup.

Revision `0016_remove_inventory`, after `0014_channel_publications`, retires
the Inventory schema; its own upgrade/downgrade behavior is preserved.
Catalog no longer references Inventory SKUs or warehouses.

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

- [Files](../modules/files.md): `0020_files` creates tenant registry tables;
  `dnk-manage files prepare --all` prepares private buckets after SQL migrations.
- [Tenancy](../modules/tenancy.md)
- [Persistence and UoW rules](../architecture/AGENTS.md#unit-of-work)
